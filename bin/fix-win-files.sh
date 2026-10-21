#!/bin/bash
# 把 Windows 端文件转成 CRLF（.ps1 另加 UTF-8 BOM），并做基础检查
set -e
cd /workspace/phone-control-pc/win

for f in *.bat; do
  [ -e "$f" ] || continue
  sed -i 's/\r\?$/\r/' "$f"
  echo "bat  $f  CRLF行=$(grep -c $'\r' "$f")"
done

for f in *.ps1; do
  [ -e "$f" ] || continue
  sed -i '1s/^\\xEF\\xBB\\xBF//' "$f"
  while [ "$(head -c3 "$f" | od -An -tx1 | tr -d ' \n')" = "efbbbf" ]; do
    tail -c +4 "$f" > "$f.nb" && mv "$f.nb" "$f"
  done
  sed -i 's/\r\?$/\r/' "$f"
  printf '\xef\xbb\xbf' > /tmp/bom.bin
  cat /tmp/bom.bin "$f" > /tmp/ps.out && mv /tmp/ps.out "$f"
  echo "ps1  $f  BOM+CRLF行=$(grep -c $'\r' "$f")  首字节=$(head -c3 "$f" | od -An -tx1 | tr -d ' \n')"
done

python3 -m py_compile agent_bridge.py && echo "py   agent_bridge.py 语法 OK"
echo "--- 文件清单 ---"
ls -l
