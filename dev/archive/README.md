# 归档：一次性脚本（保留作参考，不再维护）

这些脚本是当初调试/验证某个具体问题时写的，**依赖当时的临时环境**：

- 多数从 `/tmp/pccmod.py` 导入 `pcc`（先 `cp bin/pcc /tmp/pccmod.py`）
- 部分写死了当时那台电脑的路径（`C:/Users/24335/...`）
- `verify_*` 系列用来验证「打字到底进没进窗口」，现在这些结论已经写进
  [docs/PROTOCOL.md](../../docs/PROTOCOL.md) 的「四个坑」里

留在这里是因为它们记录了解题过程，遇到类似问题可以直接翻出来改。

| 文件 | 当时用来查什么 |
|---|---|
| `verify_typing*.py` | SendInput 打的字有没有真的进窗口（含 UIA/OCR 校验） |
| `verify_type2.py` / `verify_sendinput.py` | `input.type` 参数名是 `text` 还是 `value` |
| `verify_combo.py` | Ctrl+A 组合键是否生效 |
| `verify_inject_compare.py` | 对比 bridge SendInput 与 PowerShell SendKeys |
| `read_bridge.py` / `read_server.py` | 把电脑端源码拉下来读参数名 |
| `find_bridge.py` | 从进程命令行定位桥脚本路径 |
| `look_now.py` / `look_bridge.py` | 看当前桌面/窗口状态 |
| `pc_state.py` | 摸清守护进程、日志、自启、电源设置 |
| `test_wmi.py` | 验证 WMI 脱管执行（`pcc svc restart` 的基础） |
| `test_real.py` | 第一版真实联调脚本 |
| `cleanup_pc.py` / `debug_qr.py` / `fetch_pcremote.py` | 清理痕迹 / 调试二维码 / 拉取 17 项文件 |

> 想复现某次验证：把对应脚本里的写死路径改成你机器的，再
> `cp bin/pcc /tmp/pccmod.py` 后运行。
