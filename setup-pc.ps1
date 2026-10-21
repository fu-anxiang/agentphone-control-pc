#Requires -RunAsAdministrator
<#
  手机控制电脑 —— Windows 端一键配置
  ---------------------------------------------------------------
  用法（管理员 PowerShell）：
      powershell -ExecutionPolicy Bypass -File .\setup-pc.ps1
  可选参数：
      -PubKey "ssh-ed25519 AAAA..."   指定手机公钥（默认已内置本机生成的公钥）
      -NoRdp                          不开启远程桌面
  作用：
      1. 安装/启动 OpenSSH Server，并把默认 shell 设为 PowerShell
      2. 写入手机公钥（免密码登录）
      3. 防火墙只放行 Tailscale 网段 + 局域网（不暴露公网）
      4. 专业版/企业版自动开启远程桌面（RDP）
#>

param(
    [string]$PubKey = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJLiD3OKu+Gzddr78DkbG/YZoSL1Z+WIYbzpUxNAgrHz coomi-android@phone',
    [switch]$NoRdp
)

$ErrorActionPreference = 'Stop'
function Say  ($m) { Write-Host "[*] $m" -ForegroundColor Cyan }
function Ok   ($m) { Write-Host "[+] $m" -ForegroundColor Green }
function Warn ($m) { Write-Host "[!] $m" -ForegroundColor Yellow }
function Err  ($m) { Write-Host "[x] $m" -ForegroundColor Red }

$princ = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $princ.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Err '需要管理员权限：开始菜单搜索 PowerShell → 右键“以管理员身份运行”'
    exit 1
}

$cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
Say "系统: $($cv.ProductName) $($cv.DisplayVersion)   EditionID=$($cv.EditionID)"

# ---------------------------------------------------------------- 1. OpenSSH Server
Say '1/4 检查 OpenSSH Server ...'
$cap = Get-WindowsCapability -Online -Name 'OpenSSH.Server*'
if ($cap.State -ne 'Installed') {
    Say '    正在安装 OpenSSH Server（需要联网，约 1 分钟）...'
    Add-WindowsCapability -Online -Name $cap.Name | Out-Null
    Ok '    OpenSSH Server 安装完成'
} else {
    Ok '    已安装，跳过'
}

Set-Service -Name sshd -StartupType Automatic
if ((Get-Service sshd).Status -ne 'Running') { Start-Service sshd }
Ok "    sshd 已运行（状态: $((Get-Service sshd).Status)，开机自启）"

try { Set-Service -Name ssh-agent -StartupType Automatic; Start-Service ssh-agent } catch {}

# 默认 shell 换成 PowerShell，手机连上来直接是 PS 提示符
New-Item -Path 'HKLM:\SOFTWARE\OpenSSH' -Force | Out-Null
$psExe = (Get-Command powershell.exe).Source
New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell -Value $psExe -PropertyType String -Force | Out-Null
Ok "    默认 shell = $psExe"

# ---------------------------------------------------------------- 2. 公钥
Say '2/4 写入手机公钥（免密码登录）...'
$keyLine = $PubKey.Trim()
$targets = @()
$userSsh  = Join-Path $env:USERPROFILE '.ssh'
$userFile = Join-Path $userSsh 'authorized_keys'
New-Item -ItemType Directory -Force -Path $userSsh | Out-Null
$targets += $userFile
# 管理员账户登录时 sshd 读的是这个文件
$admFile = Join-Path $env:ProgramData 'ssh\administrators_authorized_keys'
New-Item -ItemType Directory -Force -Path (Split-Path $admFile) | Out-Null
$targets += $admFile

foreach ($f in $targets) {
    $existing = if (Test-Path $f) { Get-Content $f -ErrorAction SilentlyContinue } else { @() }
    if ($existing -notcontains $keyLine) {
        Add-Content -Path $f -Value $keyLine -Encoding ascii
        Ok "    已追加: $f"
    } else {
        Ok "    已存在: $f"
    }
}
# 管理员公钥文件必须收紧 ACL，否则 sshd 会拒绝使用
icacls $admFile /inheritance:r       | Out-Null
icacls $admFile /grant '*S-1-5-32-544:F' '*S-1-5-18:F' | Out-Null
Ok '    ACL 已收紧 (Administrators + SYSTEM)'

# 确认 sshd_config 允许公钥（默认开，这里兜底）
$cfg = Join-Path $env:ProgramData 'ssh\sshd_config'
if (Test-Path $cfg) {
    $raw = Get-Content $cfg -Raw
    if ($raw -notmatch '(?m)^\s*PubkeyAuthentication\s+yes') {
        Add-Content -Path $cfg -Value "`nPubkeyAuthentication yes"
        Restart-Service sshd
        Ok '    sshd_config 已补 PubkeyAuthentication yes'
    }
}

# ---------------------------------------------------------------- 3. 防火墙
Say '3/4 配置防火墙（只放行 Tailscale 网段 + 局域网）...'
$allowed = @('100.64.0.0/10', 'LocalSubnet')
Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
Get-NetFirewallRule -Name 'Coomi-SSHD' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -Name 'Coomi-SSHD' `
    -DisplayName 'Coomi SSHD (Tailscale + LAN)' `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 22 `
    -RemoteAddress $allowed -Profile Any | Out-Null
Ok '    TCP/22 仅对 100.64.0.0/10 与本地网段开放'

# ---------------------------------------------------------------- 4. 远程桌面
Say '4/4 远程桌面 ...'
if ($NoRdp) {
    Warn '    已按参数跳过'
} elseif ($cv.EditionID -match 'Professional|Enterprise|Education|Server') {
    Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections -Value 0 -Type DWord
    try { Set-Service TermService -StartupType Automatic; Start-Service TermService } catch {}
    foreach ($grp in @('@FirewallAPI.dll,-28752', 'Remote Desktop', '远程桌面')) {
        try {
            $rules = Get-NetFirewallRule -Group $grp -ErrorAction Stop
            $rules | Get-NetFirewallAddressFilter | Set-NetFirewallAddressFilter -RemoteAddress $allowed -ErrorAction SilentlyContinue
            Enable-NetFirewallRule -Group $grp -ErrorAction SilentlyContinue
            Ok "    RDP 已开启，来源同样限制在 Tailscale/局域网（$grp）"
            break
        } catch {}
    }
} else {
    Warn "    当前版本（$($cv.EditionID)）不提供 RDP 服务端。"
    Warn '    远程桌面请用 RustDesk / ToDesk / 向日葵，或升级到专业版。'
}

# ---------------------------------------------------------------- 汇总
Write-Host ''
Write-Host '=================== 连接信息 ===================' -ForegroundColor Magenta
Write-Host ("  用户名(SSH) : {0}" -f $env:USERNAME)
Write-Host ("  计算机名    : {0}" -f $env:COMPUTERNAME)

$lanIps = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
           Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and $_.IPAddress -ne '0.0.0.0' } |
           Select-Object -ExpandProperty IPAddress -Unique)
if ($lanIps) { Write-Host ("  局域网 IP   : {0}" -f ($lanIps -join ', ')) }

$tsCmd = Get-Command tailscale.exe -ErrorAction SilentlyContinue
if (-not $tsCmd -and (Test-Path 'C:\Program Files\Tailscale\tailscale.exe')) {
    $tsCmd = Get-Item 'C:\Program Files\Tailscale\tailscale.exe'
}
if ($tsCmd) {
    $tsIp = (& $tsCmd.Source ip -4 2>$null)
    if ($tsIp) {
        Write-Host ("  Tailscale IP: {0}" -f ($tsIp -join ', ')) -ForegroundColor Green
    } else {
        Write-Host '  Tailscale   : 已安装但未登录，请打开 Tailscale 登录同一账号'
    }
} else {
    Write-Host '  Tailscale   : 未安装' -ForegroundColor Yellow
    Write-Host '    安装: winget install --id Tailscale.Tailscale -e    然后登录手机同一个账号'
}
Write-Host '================================================' -ForegroundColor Magenta
Write-Host ''
Write-Host '下一步：手机上执行  winctl setup 用户名@Tailscale地址  （或 winctl setup 用户名@局域网IP）'
