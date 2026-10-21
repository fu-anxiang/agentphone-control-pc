#Requires -RunAsAdministrator
<#
  手机控制电脑 —— 中继桥一键安装（Windows，新版 32 位双令牌）
  ---------------------------------------------------------------
  用法（管理员 PowerShell，在本文件所在目录）：
      powershell -ExecutionPolicy Bypass -File .\install-bridge.ps1
      powershell -ExecutionPolicy Bypass -File .\install-bridge.ps1 -NewToken
  参数：
      -Room       指定 Agent API 令牌（32 位）；不填则沿用上次或自动生成
      -ViewRoom   指定投屏房间令牌（32 位）；不填则沿用上次或自动生成
      -NewToken   强制重新生成两个令牌
      -NoAuto     不设置登录自启
  作用：
      1. 检查/安装 Python 依赖（websockets、pillow，可选 playwright、qrcode）
      2. 生成/沿用两个 32 位令牌，写入 %USERPROFILE%\.pcremote\config.json
      3. 用 pythonw 后台启动 agent_bridge.py（无窗口，日志 bridge.log）
      4. 注册登录自启计划任务 pcrelay-bridge
      5. 打印手机端要用的两行地址
#>

param(
    [string]$Room = '',
    [string]$ViewRoom = '',
    [switch]$NewToken,
    [switch]$NoAuto
)

$ErrorActionPreference = 'Stop'
function Say($m) { Write-Host "[*] $m" -ForegroundColor Cyan }
function Ok($m)  { Write-Host "[+] $m" -ForegroundColor Green }
function Warn($m){ Write-Host "[!] $m" -ForegroundColor Yellow }
function Err($m) { Write-Host "[x] $m" -ForegroundColor Red }

$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bridge = Join-Path $dir 'agent_bridge.py'
if (-not (Test-Path $bridge)) { Err "找不到 agent_bridge.py（应与本脚本同目录）: $bridge"; exit 1 }

# ---------------------------------------------------------------- 1. Python 与依赖
Say '1/4 检查 Python ...'
$py = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $py) {
    Warn '    未找到 python.exe，尝试用 winget 安装 Python 3.12 ...'
    try {
        winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements | Out-Null
        $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
        $py = Get-Command python.exe -ErrorAction SilentlyContinue
    } catch {}
}
if (-not $py) {
    Err '    请先安装 Python 3.9+（python.org 安装时勾选 Add python.exe to PATH）'
    exit 1
}
Ok "    python = $($py.Source)"
& $py.Source --version

Say '    安装依赖 websockets / pillow ...'
& $py.Source -m pip install --quiet --upgrade websockets pillow
if ($LASTEXITCODE -ne 0) {
    Warn '    默认源失败，改用清华镜像重试 ...'
    & $py.Source -m pip install --quiet --upgrade -i https://pypi.tuna.tsinghua.edu.cn/simple websockets pillow
}
if ($LASTEXITCODE -ne 0) { Err '    依赖安装失败，检查网络'; exit 1 }
Ok '    依赖就绪'

$hasPw = & $py.Source -c "import importlib.util as u;print(1 if u.find_spec('playwright') else 0)"
if ($hasPw -ne '1') {
    Warn '    未安装 playwright（pcc pw 浏览器自动化不可用；不影响其它功能）'
    Warn '    需要时： python -m pip install playwright ; python -m playwright install chromium'
}
$hasQr = & $py.Source -c "import importlib.util as u;print(1 if u.find_spec('qrcode') else 0)"
if ($hasQr -ne '1') {
    & $py.Source -m pip install --quiet qrcode pillow 2>$null
    if ($LASTEXITCODE -eq 0) { Ok '    已装 qrcode（生成 qrview.png 供手机扫码）' }
}

# ---------------------------------------------------------------- 2. 令牌
Say '2/4 准备令牌（新版是两个独立的 32 位令牌）...'
$cfgFile = Join-Path $env:USERPROFILE '.pcremote\config.json'
$cfg = $null
if ((Test-Path $cfgFile) -and (-not $NewToken)) {
    try { $cfg = Get-Content $cfgFile -Raw | ConvertFrom-Json } catch {}
}
function New-Token {
    $chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
    $bytes = New-Object 'byte[]' 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
}
if (-not $Room)     { if ($cfg -and $cfg.agent_room) { $Room = $cfg.agent_room } }
if (-not $ViewRoom) { if ($cfg -and $cfg.view_room)  { $ViewRoom = $cfg.view_room } }
if (-not $Room)     { $Room = New-Token }
if (-not $ViewRoom) { $ViewRoom = New-Token; while ($ViewRoom -eq $Room) { $ViewRoom = New-Token } }
if ($Room -eq $ViewRoom) { Err '    Agent 令牌与投屏令牌不能相同'; exit 1 }
New-Item -ItemType Directory -Force -Path (Split-Path $cfgFile) | Out-Null
@{ agent_room = $Room; view_room = $ViewRoom; host = 'pcrelay.pages.dev';
   updated = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') } |
    ConvertTo-Json | Set-Content -Path $cfgFile -Encoding UTF8
Ok "    agent 令牌 = $Room  ($($Room.Length) 位)"
Ok "    view  令牌 = $ViewRoom  ($($ViewRoom.Length) 位)"
Ok "    已保存 $cfgFile（重启沿用同一对令牌）"

$argList = @("`"$bridge`"", '--room', $Room, '--view-room', $ViewRoom)

# ---------------------------------------------------------------- 3. 后台启动
Say '3/4 启动后台桥 ...'
$pyw = Join-Path (Split-Path $py.Source) 'pythonw.exe'
if (-not (Test-Path $pyw)) { $pyw = $py.Source }
$log = Join-Path $dir 'bridge.log'

$running = Get-CimInstance Win32_Process -Filter "Name like 'python%'" -ErrorAction SilentlyContinue |
           Where-Object { $_.CommandLine -like '*agent_bridge.py*' }
if ($running) {
    Warn "    已有桥在运行 (PID $($running.ProcessId -join ','))，先结束旧的"
    $running | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}
Start-Process -FilePath $pyw -ArgumentList $argList -WorkingDirectory $dir -WindowStyle Hidden
Start-Sleep -Seconds 3
$now = Get-CimInstance Win32_Process -Filter "Name like 'python%'" -ErrorAction SilentlyContinue |
       Where-Object { $_.CommandLine -like '*agent_bridge.py*' }
if ($now) { Ok "    已启动 (PID $($now.ProcessId -join ','))" }
else { Warn "    启动似乎失败，手动执行：`n      `"$pyw`" `"$bridge`" --room $Room --view-room $ViewRoom" }

# ---------------------------------------------------------------- 4. 登录自启
if ($NoAuto) {
    Warn '4/4 已跳过自启设置（-NoAuto）'
} else {
    Say '4/4 注册登录自启 ...'
    $task = 'pcrelay-bridge'
    schtasks /Query /TN $task *> $null
    if ($LASTEXITCODE -eq 0) { schtasks /Delete /TN $task /F | Out-Null }
    $tr = '"' + $pyw + '" "' + $bridge + '" --room ' + $Room + ' --view-room ' + $ViewRoom
    schtasks /Create /TN $task /TR $tr /SC ONLOGON /RL HIGHEST /F | Out-Null
    if ($LASTEXITCODE -eq 0) { Ok "    已注册计划任务 $task（登录自动启动）" }
    else { Warn '    计划任务注册失败，可把 start-bridge.bat 放进「启动」文件夹' }
}

# ---------------------------------------------------------------- 汇总
$apiUrl  = "https://pcrelay.pages.dev/api?room=$Room"
$viewUrl = "https://pcrelay.pages.dev/?room=$ViewRoom"
Write-Host ''
Write-Host '================ 手机端用这两行 ================' -ForegroundColor Magenta
Write-Host ("  Agent API : {0}" -f $apiUrl)
Write-Host ("  触屏画面  : {0}" -f $viewUrl)
Write-Host '================================================' -ForegroundColor Magenta
Write-Host ''
Write-Host '手机端一条命令接上（把两行地址整段粘过去，pcc 会自动解析）：'
Write-Host ("  pcc init ""{0} {1}""" -f $apiUrl, $viewUrl)
Write-Host '然后： pcc info'
Write-Host ''
Write-Host '二维码：同目录 qrview.png（手机扫码直接进投屏页）'
Write-Host '换新令牌： .\install-bridge.ps1 -NewToken'
Write-Host '停止桥： Get-CimInstance Win32_Process | ? CommandLine -like "*agent_bridge.py*" | % { Stop-Process -Id $_.ProcessId -Force }'
