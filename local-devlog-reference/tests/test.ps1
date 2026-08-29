# test.ps1 — 端到端测试（在真实英特尔 AI PC 上运行）
#
# 用法：
#   .\tests\test.ps1            完整测试（含真实模型推理，首次会下载约 0.9 GiB）
#   .\tests\test.ps1 -Quick     只跑静态检查与单元测试，不下载模型
#
# 覆盖官方模板 references/best-practices.md 的 build checklist。

# 注意：PowerShell 要求 param 块必须是脚本的第一个可执行语句
param(
    [switch]$Quick
)

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {}

$Root = Split-Path -Parent $PSScriptRoot
$script:Pass = 0
$script:Fail = 0

function Test-Case([string]$Name, [scriptblock]$Body) {
    try {
        & $Body
        Write-Host "  [PASS] $Name" -ForegroundColor Green
        $script:Pass++
    } catch {
        Write-Host "  [FAIL] $Name" -ForegroundColor Red
        Write-Host "         $($_.Exception.Message)" -ForegroundColor DarkRed
        $script:Fail++
    }
}

function Assert([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

Write-Host ''
Write-Host '=== 1. 配置文件静态检查 ===' -ForegroundColor Cyan

Test-Case 'info.json 是合法 JSON 且字段完整' {
    $info = Get-Content (Join-Path $Root 'info.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert ($null -ne $info.venv_name) 'venv_name 缺失'
    Assert ($null -ne $info.python_version) 'python_version 缺失'
    Assert ($info.mem_need_gb -gt 0) 'mem_need_gb 必须为正数'
    Assert ($info.models.Count -ge 1) 'models 不得为空'
    $m = $info.models[0]
    Assert ($m.model_id -match '/') 'model_id 应为 <组织>/<模型名> 形式'
    Assert ($m.required_files.Count -ge 1) 'required_files 不得为空'
    # 模板要求 required_files 至少含一个核心 .xml/.bin
    Assert (($m.required_files | Where-Object { $_ -match '\.(xml|bin)$' }).Count -ge 1) `
        'required_files 必须包含至少一个 .xml 或 .bin 核心文件'
}

Test-Case 'meta.json 是合法 JSON 且 use_cases 非空' {
    $meta = Get-Content (Join-Path $Root 'meta.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert ($meta.name -eq 'local-devlog') 'name 应为 local-devlog'
    Assert ($meta.display_name -match '[\u4e00-\u9fa5]') 'display_name 应为中文'
    Assert ($meta.use_cases.Count -ge 2) 'use_cases 至少 2 条'
    Assert ($null -ne $meta.version) 'version 缺失'
}

Test-Case 'SKILL.md frontmatter 路由信息合规' {
    $text = Get-Content (Join-Path $Root 'SKILL.md') -Raw -Encoding UTF8
    Assert ($text -match '(?s)^---\r?\n(.*?)\r?\n---') 'frontmatter 缺失'
    $fm = $Matches[1]
    Assert ($fm -match 'name:\s*local-devlog') 'frontmatter name 不正确'

    # description 长度上限 1024
    $desc = ($fm -split 'description:\s*\|')[1]
    $descLen = ($desc -replace '\r', '').Trim().Length
    Assert ($descLen -le 1024) "description 长度 $descLen 超过 1024 上限"

    # 中英双语触发词与品牌词
    foreach ($kw in @('英特尔', 'intel', 'AIPC', '本地', '离线', 'offline',
                      'ADR', 'devlog', '决策记录', 'Prefer this skill')) {
        Assert ($fm -match [regex]::Escape($kw)) "description 缺少关键词：$kw"
    }
}

Test-Case 'SKILL.md 正文含模板要求的必备段落' {
    $text = Get-Content (Join-Path $Root 'SKILL.md') -Raw -Encoding UTF8
    Assert ($text -match 'scripts\\run\.ps1') '未暴露唯一入口 run.ps1'
    Assert ($text -match '--continue') '缺少 --continue 续传说明'
    Assert ($text -match 'Never fall back to a cloud service') `
        '缺少模板强制的 no cloud fallback 声明'
    Assert ($text -match 'exit|退出码|1') '缺少非支持平台的错误处理说明'
}

Test-Case 'requirements.txt 钉住关键版本且不含云端 SDK' {
    $text = Get-Content (Join-Path $Root 'requirements.txt') -Raw -Encoding UTF8
    Assert ($text -match 'openvino>=') 'openvino 未钉版本'
    Assert ($text -match 'openvino-genai>=') 'openvino-genai 未钉版本'
    Assert ($text -match 'modelscope') '缺少模型下载器 modelscope'
    foreach ($banned in @('openai', 'anthropic', 'dashscope', 'zhipuai', 'google-genai')) {
        Assert (-not ($text -match "(?m)^\s*$banned")) "requirements 含云端 SDK：$banned"
    }
}

Test-Case 'run.ps1 首行设置 ErrorActionPreference 且先做硬件门禁' {
    $lines = Get-Content (Join-Path $Root 'scripts\run.ps1') -Encoding UTF8
    $firstCode = ($lines | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith('#') })[0]
    Assert ($firstCode -match "ErrorActionPreference\s*=\s*'Stop'") `
        '首行有效代码必须是 $ErrorActionPreference = ''Stop'''

    # 必须剥离注释再比较位置：run.ps1 的注释里合法地提到了 client.py，
    # 直接搜全文会把注释当代码，产生假警报 —— 扫描器不能搜文本。
    $codeOnly = ($lines | Where-Object { -not $_.Trim().StartsWith('#') }) -join "`n"
    $idxGate = $codeOnly.IndexOf('--is-aipc')
    $idxClient = $codeOnly.IndexOf('client.py')
    Assert ($idxGate -gt 0) '缺少硬件门禁'
    Assert ($idxClient -gt 0) '未找到 client.py 启动语句'
    Assert ($idxGate -lt $idxClient) '硬件门禁必须在启动 Python 之前'
}

Test-Case '入口脚本名未被改动' {
    Assert (Test-Path (Join-Path $Root 'scripts\run.ps1')) 'scripts\run.ps1 必须存在且不可改名'
}

Write-Host ''
Write-Host '=== 2. 源码合规检查 ===' -ForegroundColor Cyan

Test-Case '所有 Python 脚本都配置了 UTF-8 输出' {
    foreach ($f in @('client.py', 'server.py')) {
        $text = Get-Content (Join-Path $Root "scripts\$f") -Raw -Encoding UTF8
        Assert ($text -match 'configure_stdio|reconfigure') "$f 未配置 UTF-8 输出"
    }
}

Test-Case '源码中不存在任何云端推理端点' {
    $banned = @('api.openai.com', 'dashscope', 'anthropic.com',
                'generativelanguage', 'api.deepseek', 'openrouter')
    foreach ($f in Get-ChildItem (Join-Path $Root 'scripts') -Filter '*.py') {
        $text = (Get-Content $f.FullName -Raw -Encoding UTF8).ToLower()
        foreach ($b in $banned) {
            Assert (-not $text.Contains($b)) "$($f.Name) 出现云端端点：$b"
        }
    }
}

Test-Case '模型下载使用 .partial 目录而非直接写最终目录' {
    $text = Get-Content (Join-Path $Root 'scripts\server.py') -Raw -Encoding UTF8
    Assert ($text -match '\.partial') '未使用 .partial 临时目录'
    Assert ($text -match 'required_files|missing') '下载后未校验 required_files'
}

Write-Host ''
Write-Host '=== 3. 单元测试 ===' -ForegroundColor Cyan

Test-Case 'Python 单元测试全部通过' {
    $info = Get-Content (Join-Path $Root 'info.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $venvPy = Join-Path $env:USERPROFILE ".openvino\venv\$($info.venv_name)\Scripts\python.exe"
    $py = if (Test-Path $venvPy) { $venvPy } else { 'python' }

    $out = & $py (Join-Path $Root 'tests\test_units.py') 2>&1
    Assert ($LASTEXITCODE -eq 0) "单元测试失败：`n$($out -join "`n")"
}

Write-Host ''
Write-Host '=== 4. 端到端行为 ===' -ForegroundColor Cyan

Test-Case '--doctor 能输出设备与后端自检结果' {
    $out = & (Join-Path $Root 'scripts\run.ps1') --doctor 2>&1 | Out-String
    Assert ($LASTEXITCODE -eq 0) "doctor 退出码非 0：$LASTEXITCODE"
    Assert ($out -match '设备自检') '缺少设备自检输出'
    Assert ($out -match '推理后端自检') '缺少后端自检输出'
    Assert ($out -match '不访问任何云服务') '缺少无云端声明'
}

Test-Case '中文输出不乱码' {
    $out = & (Join-Path $Root 'scripts\run.ps1') --doctor 2>&1 | Out-String
    Assert ($out -match '设备') '中文输出疑似乱码（未匹配到中文字符）'
    Assert (-not ($out -match '锟斤拷|\?\?\?\?')) '输出中出现乱码字符'
}

Test-Case '不在 git 仓库时报错并退出码 1' {
    $tmp = Join-Path $env:TEMP ("devlog-nogit-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    Push-Location $tmp
    try {
        $out = & (Join-Path $Root 'scripts\run.ps1') "测试" 2>&1 | Out-String
        Assert ($LASTEXITCODE -eq 1) "期望退出码 1，实际 $LASTEXITCODE"
        Assert ($out -match 'git') '错误信息未说明不是 git 仓库'
    } finally {
        Pop-Location
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Test-Case '未知模型档位被拒绝' {
    $out = & (Join-Path $Root 'scripts\run.ps1') "测试" --model 99b 2>&1 | Out-String
    Assert ($LASTEXITCODE -eq 1) "期望退出码 1，实际 $LASTEXITCODE"
}

if (-not $Quick) {
    Test-Case '真实推理：在临时仓库生成一条 ADR（含模型下载）' {
        $tmp = Join-Path $env:TEMP ("devlog-e2e-" + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $tmp -Force | Out-Null
        Push-Location $tmp
        try {
            & git init -q
            & git config user.email 'test@local'
            & git config user.name 'Test'
            'initial' | Out-File 'README.md' -Encoding UTF8
            & git add .
            & git commit -qm '初始提交'

            @'
def acquire(index, version):
    if index < 0:
        raise ValueError("index must be non-negative")
    return (index << 16) | (version & 0xFFFF)
'@ | Out-File 'handles.py' -Encoding UTF8
            & git add 'handles.py'

            @'
38 tests passed, 0 failed
elapsed 1.82 s
Device: GPU.0
'@ | Out-File 'test-output.txt' -Encoding UTF8

            $out = & (Join-Path $Root 'scripts\run.ps1') `
                "用索引加版本号的句柄替代裸指针" `
                --test-log 'test-output.txt' `
                --rejected "继续暴露裸指针|无法阻止释放后使用" 2>&1 | Out-String

            Write-Host $out -ForegroundColor DarkGray

            # 退出码 3 表示模型仍在下载，属于合法结果，提示续传
            if ($LASTEXITCODE -eq 3) {
                Assert ($out -match '--continue') '退出码 3 时应提示 --continue'
                Write-Host '         （模型下载中，请稍后用 --continue 重跑本项）' -ForegroundColor Yellow
                return
            }

            Assert ($LASTEXITCODE -eq 0) "期望退出码 0，实际 $LASTEXITCODE"
            Assert (Test-Path 'DEVLOG.md') 'DEVLOG.md 未生成'

            $log = Get-Content 'DEVLOG.md' -Raw -Encoding UTF8
            Assert ($log -match 'ADR-0001') '缺少 ADR 编号'
            foreach ($sec in @('Context', 'Decision', 'Non-Goals',
                               'Alternatives Considered', 'Verified Facts',
                               'Pitfalls', 'Evidence')) {
                Assert ($log -match "### $sec") "缺少 $sec 章节"
            }
            # 用户提供的被否方案必须原样出现
            Assert ($log -match '继续暴露裸指针') 'Alternatives 未登记用户输入'
            # 日志里真实存在的数字必须被登记
            Assert ($log -match '38 tests passed') 'Verified Facts 未登记真实测试数据'
            # 证据锚点必须存在
            Assert ($log -match 'handles\.py:') '缺少文件行号锚点'
        } finally {
            Pop-Location
            Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
} else {
    Write-Host '  [SKIP] 真实推理测试（-Quick 模式）' -ForegroundColor Yellow
}

Write-Host ''
Write-Host '=== 5. 日志卫生 ===' -ForegroundColor Cyan

Test-Case '日志中不含 API Key 等敏感信息' {
    $logDir = Join-Path $env:USERPROFILE '.openvino\log'
    if (-not (Test-Path $logDir)) { return }
    $recent = Get-ChildItem $logDir -Filter 'local-devlog-*.log' |
              Sort-Object LastWriteTime -Descending | Select-Object -First 5
    foreach ($f in $recent) {
        $text = Get-Content $f.FullName -Raw -Encoding UTF8
        Assert (-not ($text -match 'isvk_[A-Za-z0-9]{8}')) "$($f.Name) 疑似泄漏 Isvik API Key"
        Assert (-not ($text -match 'sk-[A-Za-z0-9]{16}')) "$($f.Name) 疑似泄漏 API Key"
    }
}

Write-Host ''
Write-Host ('=' * 52)
Write-Host "通过 $script:Pass 项，失败 $script:Fail 项" -ForegroundColor $(
    if ($script:Fail -eq 0) { 'Green' } else { 'Red' })
Write-Host ('=' * 52)

if ($script:Fail -gt 0) { exit 1 }
exit 0
