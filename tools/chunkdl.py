#!/usr/bin/env python3
"""分段下载大文件（手机网络会在大约 650KB 处被切断，用 Range 续传拼起来）"""
import sys, os, time, urllib.request

url = sys.argv[1]
dst = sys.argv[2]
total = int(sys.argv[3]) if len(sys.argv) > 3 else 0
CHUNK = 200 * 1024
UA = {"user-agent": "Mozilla/5.0 (Linux; Android 14) fetch/1.0"}

have = os.path.getsize(dst) if os.path.exists(dst) else 0
if have and total and have >= total:
    print(f"already complete {have}")
    sys.exit(0)

for attempt in range(200):
    have = os.path.getsize(dst) if os.path.exists(dst) else 0
    end = have + CHUNK - 1
    req = urllib.request.Request(url, headers={**UA, "Range": f"bytes={have}-{end}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
            cr = r.headers.get("content-range")
            if cr and "/" in cr:
                total = int(cr.split("/")[1])
        with open(dst, "ab") as f:
            f.write(data)
        got = len(data)
        print(f"[{attempt}] +{got} -> {have + got}/{total or '?'}", flush=True)
        if total and have + got >= total:
            print("COMPLETE", dst, os.path.getsize(dst))
            break
        if got == 0:
            time.sleep(1)
    except Exception as e:
        print(f"[{attempt}] ERR {type(e).__name__}: {e}", flush=True)
        time.sleep(1)
else:
    print("GIVEUP", os.path.getsize(dst) if os.path.exists(dst) else 0)
