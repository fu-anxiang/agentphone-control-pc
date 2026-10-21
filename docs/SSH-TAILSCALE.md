# 备用通道：SSH + Tailscale

中继不可用、或者你更想要一条毫秒级稳定通道时的第二方案。
手机端已确认具备：`ssh 9.6 / sftp / scp / rsync / tar`，且 IPv6 可用。

## 1. 电脑端

### 1.1 装 Tailscale（两端都要）

```
winget install --id Tailscale.Tailscale -e
```

或到 https://tailscale.com/download/windows 下载。
装完打开 → 登录（Google / 微软邮箱均可）→ 记下本机 `100.x.y.z` 地址。

### 1.2 运行 `setup-pc.ps1`

管理员 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-pc.ps1
```

脚本做的事：

1. 安装并启动 OpenSSH Server（开机自启），默认 shell 设为 PowerShell
2. 写入手机公钥 → 免密码登录（含 `administrators_authorized_keys` 的 ACL 收紧）
3. 防火墙：TCP 22 **只** 对 `100.64.0.0/10`（Tailscale）和本地网段开放，不暴露公网
4. 专业版/企业版/教育版自动开启 RDP（来源同样收紧）
5. 打印 `用户名` / `Tailscale IP` / `局域网 IP`

### 1.3 家庭版想看桌面？

家庭版没有 RDP 服务端。装 **RustDesk**（开源、自带中转、跨网可用、带文件传输）：
https://rustdesk.com/download → 电脑装服务端，手机装 App，同一个 ID。
（国内也可选 ToDesk / 向日葵。）

## 2. 手机端

```sh
./bin/pl winctl info                      # 看公钥与当前配置
./bin/pl winctl setup 你的用户名@100.88.1.23   # 记录地址 + 首连测试（自动抓指纹）
```

看到 `免密登录成功，通道可用` 就通了。

> `bin/pl` 是在 ProotLinux 客户机里执行命令的启动器；它把 `winctl` 装到
> `/usr/local/bin/winctl`，客户机内直接敲 `winctl` 也行。

日常用法：

```sh
winctl test                              # 电脑名 / 系统 / 磁盘
winctl ssh 'dir C:\'                     # 在电脑上跑命令
winctl ssh 'Get-Process | Sort CPU -Desc | Select -First 5'
winctl files                             # 交互式 SFTP：ls / get / put / cd
winctl get 'C:/Users/kevin/Desktop/a.pdf' .    # 下载
winctl put ~/Download/photo.jpg 'C:/Users/kevin/Desktop/'
winctl sync /workspace/proj 'C:/work/proj'     # tar over SSH 覆盖同步
winctl rdp                                # 远程桌面地址
```

scp 里的 Windows 路径用**正斜杠**：`C:/Users/...`。

## 3. 手机看桌面

- **RDP**：手机装微软 **Windows App**（原 Remote Desktop）→ 添加 PC → 地址填 `100.88.1.23`
  → 账号填 Windows 登录名 + 密码。
- **RustDesk / ToDesk**：装 App 登录即可，不需要 Tailscale。

## 4. 安全要点

- sshd 只在 Tailscale/局域网可达，公网扫描扫不到 22 端口
- 免密登录用 ed25519 公钥；私钥只在手机 ProotLinux 的 `/root/.ssh/coomi_win_ed25519`（600）
- 建议保留 Windows 账户密码（SSH 不允许空密码账户登录）
- 彻底禁用密码登录：`C:\ProgramData\ssh\sshd_config` 设 `PasswordAuthentication no`，重启 sshd

## 5. 排查

| 现象 | 处理 |
|---|---|
| `winctl setup` 卡住 / 超时 | 电脑 `Get-Service sshd` 是否 Running；两端 Tailscale 是否同账号在线（`tailscale status`） |
| `Permission denied (publickey)` | 公钥没进 `C:\ProgramData\ssh\administrators_authorized_keys`，或该文件 ACL 不对；重跑 `setup-pc.ps1` |
| `Host key verification failed` | 电脑重装过系统：`ssh-keygen -R <地址>` 后重跑 setup |
| 连上了但提示符是 cmd | 默认 shell 注册表没生效，重跑脚本并 `Restart-Service sshd` |
| RDP 连不上 | 家庭版不支持；专业版确认 `Get-Service TermService` 与「系统属性 → 远程 → 允许远程连接」 |
| 手机连不上任何东西 | 检查手机网络；公司网络/部分运营商可能拦截 |

## 6. 为什么不用端口映射

- 家里宽带（尤其移动）通常没有公网 IPv4，端口映射做不了
- 手机与电脑不在同一网络，DDNS + 公网暴露 22/3389 风险高
- Tailscale 是 WireGuard 点对点打洞，失败才走中继，无需任何路由器配置
- 备选：电脑有 IPv6 且路由器放行入站时，`ssh 用户名@[电脑IPv6]` 直连
