# run.ps1 — 固定入口脚本，host 硬编码此文件名，禁止改名
# 流程：硬件门禁 → 环境安装 → 定位 venv python → 启动 client.py 并转发全部参数
$ErrorActionPreference = 'Stop'

# 控制台强制 UTF-8，否则 client.py 的中文输出在 host 侧会乱码
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # 某些非交互宿主环境不允许改 Console 编码，忽略即可，Python 侧还有一层兜底
}

$SkillName = 'local-devlog'
$Root = Split-Path -Parent $PSScriptRoot          # skill 根目录
$Bin  = Join-Path $Root 'bin'

# --- 日志：必须用绝对路径，禁止相对路径 -------------------------------------
$LogDir = Join-Path $env:USERPROFILE '.openvino\log'
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$LogFile = Join-Path $LogDir ("{0}-client-{1}.log" -f $SkillName, (Get-Date -Format 'yyyyMMdd-HHmmss'))

function Write-Log([string]$Message) {
    $line = "[{0}] [ps pid={1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $PID, $Message
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

Write-Log "run.ps1 start, args=[$($args -join ' ')]"

# --doctor 是硬件诊断入口，必须允许在不受支持的平台上运行，否则用户无法自查
$SkipHardwareGate = $false
foreach ($a in $args) {
    if ($a -eq '--doctor') { $SkipHardwareGate = $true }
}

# --- 1. 硬件门禁：在任何 Python 启动之前 ------------------------------------
# 首选 host 提供的 platform.exe（Marvis 等宿主自带）。
# 若宿主未提供，此处无法在 pre-Python 阶段判定硬件，改由 client.py 用
# openvino 的设备枚举做第二道门禁 —— 这是顺序上的妥协，如实记录于此。
$platform = Join-Path $Bin 'platform.exe'
if ((Test-Path $platform) -and (-not $SkipHardwareGate)) {
    $isAipc = (& $platform --is-aipc).Trim()
    Write-Log "platform.exe --is-aipc => $isAipc"
    if ($isAipc -ne '1') {
        Write-Output '本 skill 需要英特尔 AI PC 平台（Intel Core / Core Ultra + OpenVINO 可用设备）。'
        Write-Log 'hardware gate failed, exit 1'
        exit 1
    }
} else {
    Write-Log 'platform.exe not found or doctor mode; hardware gate deferred to client.py'
}

# --- 2. 安装/校验 Python 环境 -----------------------------------------------
& (Join-Path $PSScriptRoot 'install-env.ps1')
if ($LASTEXITCODE -ne 0) {
    Write-Output '环境安装失败，请检查日志：' 
    Write-Output "  $LogFile"
    Write-Log "install-env.ps1 failed with $LASTEXITCODE, exit 1"
    exit 1
}

# --- 3. 定位 venv 中的 python ------------------------------------------------
$infoPath = Join-Path $Root 'info.json'
$info     = Get-Content $infoPath -Raw -Encoding UTF8 | ConvertFrom-Json
$venv     = Join-Path $env:USERPROFILE ".openvino\venv\$($info.venv_name)"
$python   = Join-Path $venv 'Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Output "未找到虚拟环境解释器：$python"
    Write-Log "python not found at $python, exit 1"
    exit 1
}

# --- 4. 启动 client.py，转发全部参数 ----------------------------------------
$clientPy = Join-Path $PSScriptRoot 'client.py'
Write-Log "launching client.py via $python"

& $python $clientPy @args
$code = $LASTEXITCODE

Write-Log "client.py exited with $code"
exit $code
