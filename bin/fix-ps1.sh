#!/bin/bash
# 规范化 PowerShell 脚本（幂等）：
#   去掉误写的字面量前缀 \xEF\xBB\xBF / 已有 BOM → 统一 CRLF → 只保留一个 UTF-8 BOM
set -e
f=/workspace/phone-control-pc/setup-pc.ps1
sed -i '1s/^\\xEF\\xBB\\xBF//' "$f"
# 反复剥掉行首 BOM（可能被多次追加）
while [ "$(head -c3 "$f" | od -An -tx1 | tr -d ' \n')" = "efbbbf" ]; do
  tail -c +4 "$f" > "$f.nb" && mv "$f.nb" "$f"
done
sed -i 's/\r\?$/\r/' "$f"
printf '\xef\xbb\xbf' > /tmp/bom.bin
cat /tmp/bom.bin "$f" > /tmp/out.ps1
mv /tmp/out.ps1 "$f"
chmod 644 "$f"
echo "first bytes: $(head -c 6 "$f" | od -An -tx1 | tr -d '\n')"
echo "CRLF lines: $(grep -c $'\r' "$f") / total: $(wc -l < "$f")"
