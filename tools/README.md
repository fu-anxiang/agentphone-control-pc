# tools：辅助工具

| 工具 | 用途 |
|---|---|
| `shrink.py <图> <输出目录>` | 把手机截图缩小/切半，便于视觉读取（依赖 Pillow） |
| `bands.py <图> <输出目录> [条带数] [语言]` | 长截图切成带重叠的横条逐条 OCR（依赖 tesseract） |
| `lines.py <图> [输出目录] [语言]` | 按行切图逐行 OCR（读随机令牌这类精确内容用） |
| `rowocr.py <图>` | 行投影找文本行 + 逐行放大 OCR |
| `crop_ocr.py <图> <y0> <y1> [psm]` | 指定纵向区间放大 OCR，只打印含 URL/令牌特征的行 |
| `tokocr.py <图> <y0> <y1> <x0> <x1>` | 令牌区域精读：Otsu 二值化 + 多方案投票 |
| `chunkdl.py <url> <目标> [总字节]` | 分段 Range 下载（手机网络会在 ~650KB 处被切，用续传拼起来） |
| `probe_proto.py <room>` | 以 role=pc 连中继，打印它发来的每条消息（反推请求信封） |
| `probe_reply.py <room> [信封] [秒]` | 收到请求后按指定信封回复，反推应答格式 |
| `probe-relay.sh` / `probe-relay2.sh` | 抓中继前端页面，提取 WebSocket/房间协议 |

## 为什么这些留在这里

`pcc` 的实现是「先探明真实接口，再照着写」。这些工具就是探明过程本身：

1. 截图 → OCR 读能力表（`bands` / `lines` / `rowocr` / `crop_ocr`）
2. 令牌被 OCR 认不准（`1/l/I`、`0/O/_`）→ 用 `tokocr` 多方案投票 + 长度核对
3. 协议未知 → `probe_proto` / `probe_reply` 直接跟中继对话
4. 大文件下不下来 → `chunkdl` 分段落盘

接口再变时，照这个顺序再跑一遍就能重新摸清（见 `dev/probe_api*.py`）。
