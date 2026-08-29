# install-env.ps1 — 创建/校验 Python 虚拟环境（读 info.json 驱动）
# 用 uv 而非 pip/venv：建环境与装依赖显著更快，且自带解析缓存
$ErrorActionPreference = 'Stop'

$SkillName = 'local-devlog'
$Root = Split-Path -Parent $PSScriptRoot
$Bin  = Join-Path $Root 'bin'

$LogDir = Join-Path $env:USERPROFILE '.openvino\log'
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$LogFile = Join-Path $LogDir ("{0}-env-{1}.log" -f $SkillName, (Get-Date -Format 'yyyyMMdd-HHmmss'))

function Write-Log([string]$Message) {
    $line = "[{0}] [env pid={1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $PID, $Message
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

$infoPath = Join-Path $Root 'info.json'
$info     = Get-Content $infoPath -Raw -Encoding UTF8 | ConvertFrom-Json
$venvName = $info.venv_name
$pyVer    = $info.python_version

$VenvRoot = Join-Path $env:USERPROFILE '.openvino\venv'
$VenvDir  = Join-Path $VenvRoot $venvName
$PythonExe = Join-Path $VenvDir 'Scripts\python.exe'
$ReqFile  = Join-Path $Root 'requirements.txt'
$StampFile = Join-Path $VenvDir '.requirements.sha256'

Write-Log "venv=$VenvDir python=$pyVer"

# --- 1. 确保 uv.exe 可用 -----------------------------------------------------
if (-not (Test-Path $Bin)) { New-Item -ItemType Directory -Path $Bin -Force | Out-Null }
$UvExe = Join-Path $Bin 'uv.exe'

if (-not (Test-Path $UvExe)) {
    # 优先复用系统已安装的 uv，避免重复下载
    $sysUv = Get-Command uv -ErrorAction SilentlyContinue
    if ($sysUv) {
        $UvExe = $sysUv.Source
        Write-Log "reuse system uv at $UvExe"
    } else {
        Write-Output '首次运行：正在下载 uv（约 15 MB）...'
        $uvZip = Join-Path $env:TEMP "uv-$([guid]::NewGuid().ToString('N')).zip"
        $uvUrl = 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip'
        try {
            Invoke-WebRequest -Uri $uvUrl -OutFile $uvZip -UseBasicParsing
            Expand-Archive -Path $uvZip -DestinationPath $Bin -Force
            Remove-Item $uvZip -Force -ErrorAction SilentlyContinue
            Write-Log 'uv downloaded and extracted'
        } catch {
            Write-Output "uv 下载失败：$($_.Exception.Message)"
            Write-Log "uv download failed: $($_.Exception.Message)"
            exit 1
        }
        $UvExe = Join-Path $Bin 'uv.exe'
    }
}

if (-not (Test-Path $UvExe)) {
    Write-Output "未找到 uv.exe：$UvExe"
    Write-Log 'uv.exe missing after install attempt'
    exit 1
}

# --- 2. 创建虚拟环境 ---------------------------------------------------------
if (-not (Test-Path $PythonExe)) {
    Write-Output "正在创建虚拟环境（Python $pyVer）..."
    Write-Log "creating venv at $VenvDir"
    & $UvExe venv --python $pyVer $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Output '虚拟环境创建失败。'
        Write-Log "uv venv failed with $LASTEXITCODE"
        exit 1
    }
}

# --- 3. 装依赖：SHA256 一致则跳过 -------------------------------------------
# 用 requirements.txt 的哈希做指纹，内容没变就不重复解析安装
$reqHash = (Get-FileHash -Path $ReqFile -Algorithm SHA256).Hash
$needInstall = $true
if (Test-Path $StampFile) {
    $oldHash = (Get-Content $StampFile -Raw -Encoding UTF8).Trim()
    if ($oldHash -eq $reqHash) {
        $needInstall = $false
        Write-Log 'requirements unchanged, skip install'
    }
}

if ($needInstall) {
    Write-Output '正在安装依赖（首次约需 1-3 分钟）...'
    Write-Log "installing requirements, hash=$reqHash"

    # 国内镜像优先，失败回落公共 PyPI
    $mirrors = @(
        'https://mirrors.aliyun.com/pypi/simple/',
        'https://pypi.tuna.tsinghua.edu.cn/simple/',
        'https://pypi.org/simple/'
    )

    $installed = $false
    foreach ($m in $mirrors) {
        Write-Log "try index $m"
        & $UvExe pip install --python $PythonExe -r $ReqFile --index-url $m
        if ($LASTEXITCODE -eq 0) {
            $installed = $true
            Write-Log "install ok via $m"
            break
        }
        Write-Log "index $m failed with $LASTEXITCODE, fallback"
    }

    if (-not $installed) {
        Write-Output '依赖安装失败，请检查网络或日志：'
        Write-Output "  $LogFile"
        Write-Log 'all indexes failed'
        exit 1
    }

    Set-Content -Path $StampFile -Value $reqHash -Encoding UTF8
}

# --- 4. 本地 wheels：仅当文件比标记更新时安装 -------------------------------
$WheelDir = Join-Path $Root 'wheels'
if (Test-Path $WheelDir) {
    $wheels = Get-ChildItem -Path $WheelDir -Filter '*.whl' -ErrorAction SilentlyContinue
    foreach ($w in $wheels) {
        $stamp = Join-Path $VenvDir (".whl-" + $w.BaseName + ".stamp")
        $needWhl = $true
        if (Test-Path $stamp) {
            $stampTime = (Get-Item $stamp).LastWriteTimeUtc
            if ($w.LastWriteTimeUtc -le $stampTime) { $needWhl = $false }
        }
        if ($needWhl) {
            Write-Log "installing wheel $($w.Name)"
            & $UvExe pip install --python $PythonExe $w.FullName
            if ($LASTEXITCODE -eq 0) {
                Set-Content -Path $stamp -Value $w.LastWriteTimeUtc.ToString('o') -Encoding UTF8
            } else {
                Write-Log "wheel $($w.Name) failed with $LASTEXITCODE"
            }
        }
    }
}

Write-Log 'install-env.ps1 done'
exit 0
