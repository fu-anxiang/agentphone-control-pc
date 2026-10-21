#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agent_bridge.py —— 电脑端中继桥（兼容 pcrelay 边缘中继协议）

电脑上运行后，手机通过
    Agent API : https://pcrelay.pages.dev/api?room=<32 位令牌 A>
    投屏接管  : https://pcrelay.pages.dev/?room=<32 位令牌 B>
即可控制这台电脑。

依赖：
    pip install websockets pillow
    pip install playwright        # 仅 pcc pw / pwscript 需要
    pip install qrcode            # 可选：生成 qrview.png 方便手机扫码

用法（Windows）：
    python agent_bridge.py                 # 用已保存的令牌，没有则生成并保存
    python agent_bridge.py --new-token     # 重新生成两个令牌
    python agent_bridge.py --room A --view-room B
    python agent_bridge.py --demo          # 演示模式：合成画面 + 输入只打印，不真正操作

令牌：secrets.token_urlsafe(24) → 32 位 URL-safe 字符；Agent 房间与投屏房间**互相独立**。
首次运行写入 ~/.pcremote/config.json，之后重启沿用同一对令牌。

协议（反转自 pcrelay 前端）：
    WS   wss://<host>/ws?role=pc&room=<room>
    PC→   {"t":"peer","event":"join","role":"pc"} / {"t":"info","w":..,"h":..} / 二进制 JPEG 帧
    中继→ {"id":"..","m":"shell","p":{...}}            请求
    PC→   {"id":"..","r":{...}}                        应答
    中继→ {"t":"peer","event":"join","role":"phone"}   手机投屏端上下线
    中继→ {"t":"abs"/"mv"/"click"/"key"/"wheel"/"text"} 输入事件
"""
import argparse
import asyncio
import base64
import io
import json
import os
import platform
import random
import secrets
import subprocess
import sys
import threading
import time
import traceback

try:
    import websockets
except ImportError:
    sys.exit("缺少依赖：pip install websockets")

try:
    from PIL import Image
except ImportError:
    Image = None

IS_WIN = sys.platform.startswith("win")
DEFAULT_HOST = "pcrelay.pages.dev"
FPS = 4.0                 # 投屏帧率
JPEG_QUALITY = 65
MAX_INFLIGHT = 2          # 未 ack 的帧上限，防止内存堆积
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".pcremote")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
TOKEN_LEN = 32            # token_urlsafe(24) 的结果长度


def new_token():
    """与新版 pc config 一致：URL-safe 随机令牌，32 位。"""
    return secrets.token_urlsafe(24)[:TOKEN_LEN]


def load_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except Exception:
        pass


# =====================================================================
#  画面采集
# =====================================================================
class Screen:
    """Windows 用 GDI BitBlt 抓屏；demo 模式生成合成画面。"""

    def __init__(self, demo=False, quality=JPEG_QUALITY):
        self.demo = demo or not IS_WIN
        self.quality = quality
        self._demo_t = 0
        self._lock = threading.Lock()
        if self.demo:
            self.size = (1280, 800)
        else:
            self._init_win()

    # ---------------- Windows ----------------
    def _init_win(self):
        import ctypes
        from ctypes import wintypes

        self.ct = ctypes
        self.wt = wintypes
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        self.user32, self.gdi32 = user32, gdi32

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Win8.1+ 每显示器 DPI 感知
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [("bmiHeader", BITMAPINFOHEADER),
                        ("bmiColors", wintypes.DWORD * 3)]

        self.BITMAPINFO = BITMAPINFO
        self.size = (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))

    def _grab_win(self):
        ct = self.ct
        hdc_screen = self.user32.GetDC(0)
        w, h = self.size
        mdc = self.gdi32.CreateCompatibleDC(hdc_screen)
        bmp = self.gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
        old = self.gdi32.SelectObject(mdc, bmp)
        SRCCOPY = 0x00CC0020
        self.gdi32.BitBlt(mdc, 0, 0, w, h, hdc_screen, 0, 0, SRCCOPY)

        bi = self.BITMAPINFO()
        bi.bmiHeader.biSize = ct.sizeof(self.BITMAPINFO)
        bi.bmiHeader.biWidth = w
        bi.bmiHeader.biHeight = -h          # 负数 = 自上而下
        bi.bmiHeader.biPlanes = 1
        bi.bmiHeader.biBitCount = 32
        bi.bmiHeader.biCompression = 0
        buf = ct.create_string_buffer(w * h * 4)
        self.gdi32.GetDIBits(mdc, bmp, 0, h, buf, ct.byref(bi), 0)

        self.gdi32.SelectObject(mdc, old)
        self.gdi32.DeleteObject(bmp)
        self.gdi32.DeleteDC(mdc)
        self.user32.ReleaseDC(0, hdc_screen)

        img = Image.frombuffer("RGB", (w, h), buf, "raw", "BGRX", 0, 1)
        if w > 1280:                      # 手机看画面不需要原始分辨率
            scale = 1280 / w
            img = img.resize((1280, int(h * scale)))
        return img

    # ---------------- demo ----------------
    def _grab_demo(self):
        from PIL import ImageDraw
        w, h = 1280, 800
        self._demo_t += 1
        img = Image.new("RGB", (w, h), (18, 24, 34))
        d = ImageDraw.Draw(img)
        d.rectangle([30, 30, w - 30, h - 30], outline=(58, 122, 200), width=3)
        d.text((60, 70), "DEMO SCREEN (no display capture)", fill=(220, 235, 250))
        d.text((60, 100), time.strftime("%Y-%m-%d %H:%M:%S"), fill=(140, 200, 255))
        d.text((60, 130), f"frame #{self._demo_t}", fill=(140, 200, 255))
        return img

    def grab_jpeg(self, quality=None, max_width=1600):
        with self._lock:
            img = self._grab_demo() if self.demo else self._grab_win()
            if max_width and img.width > max_width:
                scale = max_width / img.width
                img = img.resize((max_width, int(img.height * scale)))
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=int(quality or self.quality))
            return buf.getvalue(), img.size


# =====================================================================
#  输入注入
# =====================================================================
VK = {
    "enter": 0x0D, "return": 0x0D, "esc": 0x1B, "escape": 0x1B, "tab": 0x09,
    "space": 0x20, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "win": 0x5B, "lwin": 0x5B, "rwin": 0x5C, "apps": 0x5D,
    "ctrl": 0x11, "control": 0x11, "alt": 0x12, "shift": 0x10,
    "capslock": 0x14, "printscreen": 0x2C, "insert": 0x2D,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
}


class Input:
    def __init__(self, demo=False):
        self.demo = demo or not IS_WIN
        self._lock = threading.Lock()
        if not self.demo:
            self._init_win()

    def _init_win(self):
        import ctypes
        from ctypes import wintypes

        self.ct = ctypes
        ULONG_PTR = wintypes.WPARAM

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                        ("dwExtraInfo", ULONG_PTR)]

        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                        ("wParamH", wintypes.WORD)]

        class _U(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("u", _U)]

        self.INPUT = INPUT
        self.MI, self.KI = MOUSEINPUT, KEYBDINPUT
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.sw, self.sh = (self.user32.GetSystemMetrics(0),
                            self.user32.GetSystemMetrics(1))
        # 虚拟桌面（多显示器）
        self.vx = self.user32.GetSystemMetrics(76)
        self.vy = self.user32.GetSystemMetrics(77)
        self.vw = self.user32.GetSystemMetrics(78)
        self.vh = self.user32.GetSystemMetrics(79)

    # ---------------- 底层发送 ----------------
    def _send(self, *inputs):
        arr = (self.INPUT * len(inputs))(*inputs)
        self.user32.SendInput(len(inputs), arr, self.ct.sizeof(self.INPUT))

    def _mouse(self, flags, dx=0, dy=0, data=0):
        mi = self.MI(dx, dy, data, flags, 0, 0)
        inp = self.INPUT()
        inp.type = 0          # INPUT_MOUSE
        inp.u.mi = mi
        self._send(inp)

    def _key(self, vk, flags=0, scan=0):
        ki = self.KI(vk, scan, flags, 0, 0)
        inp = self.INPUT()
        inp.type = 1          # INPUT_KEYBOARD
        inp.u.ki = ki
        self._send(inp)

    # ---------------- 对外动作 ----------------
    def move_abs(self, x, y):
        """x,y 归一化 0~1（相对整个虚拟桌面）。"""
        if self.demo:
            return {"demo": "abs", "x": x, "y": y}
        with self._lock:
            ax = int(self.vx + max(0.0, min(1.0, x)) * self.vw)
            ay = int(self.vy + max(0.0, min(1.0, y)) * self.vh)
            nx = int(ax * 65535 / max(1, self.user32.GetSystemMetrics(78) - 1))
            ny = int(ay * 65535 / max(1, self.user32.GetSystemMetrics(79) - 1))
            self.user32.SetCursorPos(ax, ay)
        return {"ok": True, "x": ax, "y": ay}

    def move_px(self, x, y):
        """绝对定位到屏幕像素坐标。"""
        if self.demo:
            return {"demo": "move", "x": x, "y": y}
        with self._lock:
            self.user32.SetCursorPos(int(x), int(y))
        return {"ok": True, "cursor": [int(x), int(y)]}

    def button(self, down, button="left"):
        if self.demo:
            return {"demo": "down" if down else "up", "b": button}
        flags = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010),
                 "middle": (0x0020, 0x0040)}.get(button, (0x0002, 0x0004))
        with self._lock:
            self._mouse(flags[0] if down else flags[1])
        return {"ok": True}

    def move_rel(self, dx, dy):
        if self.demo:
            return {"demo": "mv", "dx": dx, "dy": dy}
        with self._lock:
            pt = self.ct.wintypes.POINT()
            self.user32.GetCursorPos(self.ct.byref(pt))
            self.user32.SetCursorPos(pt.x + int(dx * self.vw), pt.y + int(dy * self.vh))
        return {"ok": True}

    def click(self, button="left", n=1):
        if self.demo:
            return {"demo": "click", "b": button, "n": n}
        down, up = {"left": (0x0002, 0x0004), "right": (0x0008, 0x0010),
                    "middle": (0x0020, 0x0040)}.get(button, (0x0002, 0x0004))
        with self._lock:
            for _ in range(max(1, int(n))):
                self._mouse(down)
                self._mouse(up)
                time.sleep(0.02)
        return {"ok": True}

    def wheel(self, dy):
        if self.demo:
            return {"demo": "wheel", "dy": dy}
        with self._lock:
            self._mouse(0x0800, data=int(dy))
        return {"ok": True}

    def type_text(self, text):
        if self.demo:
            return {"demo": "text", "text": text}
        with self._lock:
            for ch in text:
                if ch == "\n":
                    self._key(VK["enter"], 0)
                    self._key(VK["enter"], 0x0002)
                    continue
                units = ch.encode("utf-16-le")           # 代理对拆成两个 UTF-16 单元
                for i in range(0, len(units), 2):
                    unit = int.from_bytes(units[i:i + 2], "little")
                    self._key(0, 0x0004, unit)           # KEYEVENTF_UNICODE
                    self._key(0, 0x0004 | 0x0002, unit)  # + KEYEVENTF_KEYUP
                time.sleep(0.004)
        return {"ok": True, "sent": len(text)}

    def key(self, k, mods=None):
        if self.demo:
            return {"demo": "key", "k": k, "mods": mods}
        mods = mods or []
        vk = VK.get(str(k).lower())
        if vk is None and len(str(k)) == 1:
            ch = str(k)
            vk = ord(ch.upper()) if ch.isalnum() else None
        if vk is None:
            return {"err": f"未知按键 {k}"}
        mod_vk = [VK[m] for m in mods if m.lower() in VK]
        with self._lock:
            for m in mod_vk:
                self._key(m, 0)
            self._key(vk, 0)
            self._key(vk, 0x0002)
            for m in reversed(mod_vk):
                self._key(m, 0x0002)
        return {"ok": True}


# =====================================================================
#  工具方法（shell / fs / 窗口 / 剪贴板 / 应用）
# =====================================================================
def run_shell(cmd, timeout=60):
    if IS_WIN:
        args = ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd]
    else:
        args = ["/bin/bash", "-lc", cmd]
    t0 = time.time()
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout)
        enc = "utf-8"
        out = r.stdout.decode(enc, "replace")
        err = r.stderr.decode(enc, "replace")
        return {"code": r.returncode, "out": out, "err": err,
                "_ms": int((time.time() - t0) * 1000)}
    except subprocess.TimeoutExpired:
        return {"code": -1, "out": "", "err": f"超时（{timeout}s）"}
    except Exception as e:
        return {"code": -1, "out": "", "err": f"{type(e).__name__}: {e}"}


def list_windows():
    if not IS_WIN:
        return {"items": [], "err": "仅 Windows 支持窗口枚举"}
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    items = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        items.append({"hwnd": int(hwnd), "title": buf.value, "pid": pid.value,
                      "rect": [rect.left, rect.top, rect.right, rect.bottom]})
        return True

    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return {"ok": True, "windows": items, "items": items, "count": len(items)}


def focus_window(title):
    if not IS_WIN:
        return {"err": "仅 Windows 支持窗口切换"}
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    found = []

    def cb(hwnd, _):
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if title.lower() in buf.value.lower():
                found.append((hwnd, buf.value))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    if not found:
        return {"ok": False, "e": f"没找到包含“{title}”的窗口"}
    hwnd, name = found[0]
    user32.ShowWindow(hwnd, 9)          # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    return {"ok": True, "window": {"hwnd": int(hwnd), "title": name,
                                   "foreground": True}}


def clipboard(action, text=None):
    if IS_WIN:
        if action == "get":
            return run_shell("Get-Clipboard -Raw")
        r = run_shell("Set-Clipboard -Value " + json.dumps(text or ""))
        return {"ok": True, "chars": len(text or "")}
    return {"err": "剪贴板仅 Windows 实现"}


def fs_op(p):
    action = (p.get("action") or "list").lower()
    path = p.get("path", ".")
    try:
        if action in ("ls", "list"):
            rows = []
            with os.scandir(path) as it:
                for e in it:
                    try:
                        st = e.stat()
                        rows.append({"name": e.name, "dir": e.is_dir(), "size": st.st_size,
                                     "mtime": int(st.st_mtime)})
                    except OSError:
                        rows.append({"name": e.name, "dir": e.is_dir(), "size": 0})
            rows.sort(key=lambda x: (not x["dir"], x["name"].lower()))
            return {"ok": True, "path": os.path.abspath(path), "items": rows[:500],
                    "count": len(rows)}
        if action == "read":
            data = open(path, "rb").read()
            if p.get("b64"):
                return {"ok": True, "b64": base64.b64encode(data).decode(),
                        "size": len(data)}
            limit = int(p.get("max_bytes", 400000))
            return {"ok": True, "path": path,
                    "text": data.decode("utf-8", "replace")[:limit],
                    "truncated": len(data) >= limit}
        if action == "write":
            if p.get("b64"):
                data = base64.b64decode(p["b64"])
            else:
                data = str(p.get("content", p.get("text", ""))).encode(
                    p.get("encoding", "utf-8"))
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "ab" if p.get("append") else "wb") as f:
                f.write(data)
            return {"ok": True, "path": path, "bytes": os.path.getsize(path)}
        if action == "mkdir":
            os.makedirs(path, exist_ok=True)
            return {"ok": True, "path": path}
        if action in ("del", "delete", "rm"):
            import shutil
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            elif os.path.exists(path):
                os.remove(path)
            return {"ok": True, "path": path}
        return {"ok": False, "e": f"未知 fs 动作 {action}"}
    except Exception as e:
        return {"ok": False, "e": f"{type(e).__name__}: {e}"}


def app_op(action, name):
    if action == "start":
        if IS_WIN:
            if name.lower().startswith(("http://", "https://")) or os.path.exists(name):
                os.startfile(name)          # noqa: 用系统默认程序打开文档/网址
                return {"ok": True, "started": name}
            proc = subprocess.Popen([name], stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            return {"ok": True, "pid": proc.pid, "started": name}
        else:
            subprocess.Popen(name, shell=True)
        return {"ok": True, "started": name}
    if action == "kill":
        if IS_WIN:
            if str(name).isdigit():
                subprocess.run(["taskkill", "/PID", str(name), "/F"], capture_output=True)
            else:
                subprocess.run(["taskkill", "/IM", str(name), "/F"], capture_output=True)
            return {"ok": True}
        return run_shell(f"pkill -f {name}")
    return {"err": f"未知动作 {action}"}


# =====================================================================
#  Playwright（可选）
# =====================================================================
class PW:
    def __init__(self):
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.err = None

    async def _ensure(self):
        if self.page:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("未安装 playwright：pip install playwright")
        if self.pw is None:
            self.pw = await async_playwright().start()
        if self.browser is None:
            try:
                self.browser = await self.pw.chromium.launch(channel="chrome", headless=False)
            except Exception:
                self.browser = await self.pw.chromium.launch(headless=False)
        if self.context is None:
            self.context = await self.browser.new_context()
        if self.page is None:
            pages = self.context.pages
            self.page = pages[0] if pages else await self.context.new_page()

    async def run(self, p):
        await self._ensure()
        a = p.get("action")
        page = self.page
        if a == "goto":
            await page.goto(p.get("url", "about:blank"), timeout=45000)
            return {"ok": True, "url": page.url, "title": await page.title()}
        if a == "click":
            await page.click(p.get("selector"), timeout=20000)
            return {"ok": True}
        if a == "fill":
            await page.fill(p.get("selector"), str(p.get("value", "")), timeout=20000)
            return {"ok": True}
        if a == "press":
            await page.keyboard.press(p.get("key", "Enter"))
            return {"ok": True}
        if a == "text":
            return {"text": (await page.inner_text(p.get("selector", "body")))[:100000]}
        if a == "html":
            return {"html": (await page.content())[:200000]}
        if a == "eval":
            return {"value": await page.evaluate(p.get("code", "1"))}
        if a == "count":
            return {"count": await page.locator(p.get("selector", "a")).count()}
        if a == "screenshot":
            buf = await page.screenshot(type="jpeg", quality=JPEG_QUALITY)
            return {"b64": base64.b64encode(buf).decode()}
        if a == "newpage":
            self.page = await self.context.new_page()
            if p.get("url"):
                await self.page.goto(p["url"])
            return {"ok": True}
        if a == "pages":
            return {"items": [pg.url for pg in self.context.pages]}
        if a == "back":
            await page.go_back()
            return {"ok": True, "url": page.url}
        if a == "wait":
            await asyncio.sleep(float(p.get("sec", 1)))
            return {"ok": True}
        return {"err": f"未知 pw 动作 {a}"}

    async def script(self, code):
        await self._ensure()
        env = {"page": self.page, "context": self.context,
               "browser": self.browser, "asyncio": asyncio}
        fn = f"async def __s__():\n" + "\n".join("    " + l for l in code.splitlines())
        exec(fn, env)
        return {"result": repr(await env["__s__"]())}


# =====================================================================
#  桥主体
# =====================================================================
class Bridge:
    def __init__(self, host, agent_room, view_room=None, demo=False):
        self.host = host
        self.agent_room = agent_room
        self.view_room = view_room or None
        # 新版协议：Agent 房间管 API，投屏房间管画面，两者独立
        self.rooms = [agent_room] + ([view_room] if view_room else [])
        self.demo = demo
        self.screen = Screen(demo)
        self.input = Input(demo)
        self.pw = PW()
        self.viewer = {}          # room -> 是否有手机在看
        self.inflight = {}
        self.ack_count = {}
        self.keep_awake = False

    # ---------- 请求分发 ----------
    async def handle(self, m, p):
        p = p or {}
        # 与官方桥保持同一套参数名（value/match/count/set/content...）
        if m == "info":
            import socket
            vx, vy, vw, vh = (0, 0, self.screen.size[0], self.screen.size[1])
            return {"host": socket.gethostname(), "user": os.environ.get("USERNAME")
                    or os.environ.get("USER"), "os": platform.platform(),
                    "screen": {"w": vw, "h": vh},
                    "w": vw, "h": vh,
                    "demo": self.demo, "pid": os.getpid(),
                    "locked": False, "idle": 0}
        if m == "ping":
            return {"pong": time.time()}
        if m == "session":
            return {"locked": False, "idle": 0,
                    "screen": {"w": self.screen.size[0], "h": self.screen.size[1]},
                    "keep_awake": self.keep_awake, "hint": "本桥无锁屏检测"}
        if m == "keep_awake":
            self.keep_awake = bool(p.get("on", True))
            return {"ok": True, "on": self.keep_awake}
        if m == "shell":
            return await asyncio.get_event_loop().run_in_executor(
                None, run_shell, p.get("cmd", ""), int(p.get("timeout", 60)))
        if m == "screenshot":
            b64 = await asyncio.get_event_loop().run_in_executor(
                None, self._shot_b64, int(p.get("quality", JPEG_QUALITY)),
                int(p.get("max_width", 1600)))
            return b64
        if m == "input":
            return self._do_input(p)
        if m == "windows":
            return await asyncio.get_event_loop().run_in_executor(None, list_windows)
        if m == "focus":
            return await asyncio.get_event_loop().run_in_executor(
                None, focus_window, str(p.get("match") or p.get("title") or ""))
        if m == "app":
            if p.get("action") == "kill" and (p.get("pid") or p.get("name")):
                target = p.get("name") or str(p.get("pid"))
                return await asyncio.get_event_loop().run_in_executor(
                    None, app_op, "kill", target)
            return await asyncio.get_event_loop().run_in_executor(
                None, app_op, p.get("action", "start"),
                p.get("target") or p.get("name", ""))
        if m == "fs":
            return await asyncio.get_event_loop().run_in_executor(None, fs_op, p)
        if m == "clip":
            return await asyncio.get_event_loop().run_in_executor(
                None, clipboard,
                "set" if ("set" in p or p.get("action") == "set") else "get",
                p.get("set", p.get("text")))
        if m == "pw":
            return await self.pw.run(p)
        if m == "pwscript":
            return await self.pw.script(p.get("code", "return 1"))
        return {"err": f"未知方法 {m}", "code": -1}

    def _shot_b64(self, quality=JPEG_QUALITY, max_width=1600):
        data, (w, h) = self.screen.grab_jpeg(quality=quality, max_width=max_width)
        return {"ok": True, "b64": base64.b64encode(data).decode(), "w": w, "h": h}

    def _do_input(self, p):
        a = p.get("action")
        if a == "move":
            if "xpx" in p:
                return self.input.move_abs(p["xpx"] / max(1, self.screen.size[0]),
                                           p["ypx"] / max(1, self.screen.size[1]))
            if "x" in p and "y" in p:          # 与官方桥一致：x/y 是像素
                return self.input.move_px(float(p["x"]), float(p["y"]))
            return self.input.move_rel(float(p.get("dx", 0)), float(p.get("dy", 0)))
        if a == "abs":                          # 归一化 0~1
            return self.input.move_abs(float(p.get("x", 0.5)), float(p.get("y", 0.5)))
        if a == "moveby":
            return self.input.move_rel(float(p.get("dx", 0)), float(p.get("dy", 0)))
        if a == "click":
            return self.input.click(p.get("button", "left"),
                                    int(p.get("count", p.get("n", 1))))
        if a in ("dblclick", "double"):
            return self.input.click("left", 2)
        if a == "rightclick":
            return self.input.click("right", 1)
        if a == "down":
            return self.input.button(True, p.get("button", "left"))
        if a == "up":
            return self.input.button(False, p.get("button", "left"))
        if a in ("scroll", "wheel"):
            return self.input.wheel(int(p.get("dy", -120)))
        if a in ("type", "text"):
            # 官方桥读 value；这里两种都认
            return self.input.type_text(str(p.get("value", p.get("text", ""))))
        if a == "key":
            return self.input.key(p.get("key", "enter"), p.get("mods") or [])
        return {"err": f"未知 input 动作 {a}"}

    # ---------- 手机投屏端事件 ----------
    def on_event(self, room, ev):
        t = ev.get("t")
        if t == "peer":
            if ev.get("role") == "phone":
                self.viewer[room] = ev.get("event") == "join"
            return
        if t == "abs":
            self.input.move_abs(float(ev.get("x", 0)), float(ev.get("y", 0))); return
        if t == "mv":
            self.input.move_rel(float(ev.get("dx", 0)), float(ev.get("dy", 0))); return
        if t == "click":
            self.input.click(ev.get("b", "left"), int(ev.get("n", 1))); return
        if t == "wheel":
            self.input.wheel(int(ev.get("dy", 0))); return
        if t == "text":
            self.input.type_text(str(ev.get("s", ""))); return
        if t == "key":
            self.input.key(ev.get("k", "enter"), ev.get("mods") or []); return
        if t == "ack":
            self.inflight[room] = max(0, self.inflight.get(room, 1) - 1)
            self.ack_count[room] = self.ack_count.get(room, 0) + 1
            return

    # ---------- 单个房间的连接循环 ----------
    async def run_room(self, room):
        url = f"wss://{self.host}/ws?role=pc&room={room}"
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(url, ping_interval=20, max_size=None,
                                              open_timeout=20) as ws:
                    role = "agent" if room == self.agent_room else "view"
                    print(f"[{time.strftime('%H:%M:%S')}] connected room={room} ({role})",
                          flush=True)
                    backoff = 1.0
                    await ws.send(json.dumps({"t": "peer", "event": "join", "role": "pc"}))
                    await ws.send(json.dumps({"t": "info", "w": self.screen.size[0],
                                              "h": self.screen.size[1]}))
                    tasks = [asyncio.create_task(self._reader(ws, room)),
                             asyncio.create_task(self._streamer(ws, room))]
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for t in pending:
                        t.cancel()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] room={room} 断开: {type(e).__name__}: {e}"
                      f"（{backoff:.1f}s 后重连）", flush=True)
            await asyncio.sleep(backoff)
            backoff = min(30.0, backoff * 1.6)

    async def _reader(self, ws, room):
        async for msg in ws:
            if isinstance(msg, bytes):
                continue
            try:
                ev = json.loads(msg)
            except Exception:
                continue
            if "id" in ev and "m" in ev:
                asyncio.create_task(self._serve_req(ws, ev))
            else:
                self.on_event(room, ev)

    async def _serve_req(self, ws, ev):
        t0 = time.time()
        try:
            r = await self.handle(ev["m"], ev.get("p") or {})
        except Exception as e:
            r = {"err": f"{type(e).__name__}: {e}", "code": -1,
                 "trace": traceback.format_exc()[-800:]}
        if not isinstance(r, dict):
            r = {"result": r}
        r.setdefault("_ms", int((time.time() - t0) * 1000))
        try:
            await ws.send(json.dumps({"id": ev["id"], "r": r}))
        except Exception:
            pass

    async def _streamer(self, ws, room):
        """按 FPS 推帧；用 inflight 限流，但 acks 不来时 1.2s 后自动放宽，避免画面卡死。"""
        sent = acked = 0
        last_stat = last_ack = time.time()
        while True:
            await asyncio.sleep(1.0 / FPS)
            if not self.viewer.get(room):
                continue
            # ack 丢失保护：超过 1.2s 没有 ack 就把计数清零
            if self.inflight.get(room, 0) >= MAX_INFLIGHT:
                if time.time() - last_ack > 1.2:
                    self.inflight[room] = 0
                else:
                    continue
            try:
                data, _ = await asyncio.get_event_loop().run_in_executor(
                    None, self.screen.grab_jpeg)
                await ws.send(data)
                self.inflight[room] = self.inflight.get(room, 0) + 1
                sent += 1
            except Exception:
                await asyncio.sleep(0.5)
                continue
            now = time.time()
            if now - last_stat >= 5:
                total_ack = self.ack_count.get(room, 0)
                print(f"[{time.strftime('%H:%M:%S')}] room={room} 投屏 "
                      f"{sent / (now - last_stat):.1f} fps, ack+{total_ack - acked}",
                      flush=True)
                sent = 0
                acked = total_ack
                last_stat = now

    async def main(self):
        # 中继对同一 IP 的并发 WS 握手会排队，错开 1.5 秒依次连，避免第二个房间迟迟不上线
        tasks = []
        for i, room in enumerate(self.rooms):
            if i:
                await asyncio.sleep(1.5)
            tasks.append(asyncio.create_task(self.run_room(room)))
        await asyncio.gather(*tasks)


def main():
    # pythonw.exe 下 sys.stdout/stderr 为 None，重定向到 bridge.log，否则 print 会炸
    if sys.stdout is None or sys.stderr is None:
        logpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge.log")
        f = open(logpath, "a", encoding="utf-8", buffering=1)
        if sys.stdout is None:
            sys.stdout = f
        if sys.stderr is None:
            sys.stderr = f

    ap = argparse.ArgumentParser(description="电脑端 pcrelay 桥（新版 32 位双令牌）")
    ap.add_argument("--room", help="Agent API 房间令牌（32 位）；不填则沿用/生成")
    ap.add_argument("--view-room", dest="view_room", help="投屏画面房间令牌（32 位）")
    ap.add_argument("--new-token", action="store_true", help="重新生成一对令牌并保存")
    ap.add_argument("--host", default=DEFAULT_HOST, help=f"中继主机，默认 {DEFAULT_HOST}")
    ap.add_argument("--demo", action="store_true", help="演示模式：不真正抓屏/注入")
    args = ap.parse_args()

    cfg = load_config()
    if args.new_token:
        cfg = {}

    agent_room = args.room or cfg.get("agent_room")
    view_room = args.view_room or cfg.get("view_room")
    if not agent_room:
        agent_room = new_token()
    if not view_room:
        view_room = new_token()
        while view_room == agent_room:
            view_room = new_token()
    if agent_room == view_room:
        sys.exit("× Agent 房间与投屏房间不能相同")
    host = args.host or cfg.get("host") or DEFAULT_HOST

    if (cfg.get("agent_room") != agent_room or cfg.get("view_room") != view_room
            or cfg.get("host") != host):
        save_config({"agent_room": agent_room, "view_room": view_room, "host": host,
                     "updated": time.strftime("%Y-%m-%d %H:%M:%S")})

    api_url = f"https://{host}/api?room={agent_room}"
    view_url = f"https://{host}/?room={view_room}"

    print("=" * 74)
    print("  电脑端桥已就绪（新版：两个 32 位独立令牌）")
    print(f"  Agent API : {api_url}")
    print(f"  触屏画面  : {view_url}")
    print(f"  令牌长度  : agent={len(agent_room)}  view={len(view_room)}")
    print(f"  配置文件  : {CONFIG_FILE}")
    print(f"  模式      : {'DEMO（不操作真实桌面）' if args.demo or not IS_WIN else 'LIVE'}")
    print("=" * 74, flush=True)

    # 手机扫码用：把投屏地址存成 QR 图片
    try:
        import qrcode
        qrpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qrview.png")
        qrcode.make(view_url).save(qrpath)
        print(f"  二维码    : {qrpath}", flush=True)
    except Exception:
        pass

    bridge = Bridge(host, agent_room, view_room, demo=args.demo)
    try:
        asyncio.run(bridge.main())
    except KeyboardInterrupt:
        print("\n已退出")


if __name__ == "__main__":
    main()
