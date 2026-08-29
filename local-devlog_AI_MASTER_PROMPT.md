# local-devlog AI Master Development Prompt — FINAL

> **Purpose:** 本文件是 AI 辅助开发 local-devlog 的唯一权威规范（single source of truth）。
>
> **Language:** 中文优先。文档、注释、用户可见输出一律中文；日志与内部错误用英文。
>
> **Core rule:** 不得为实现便利跳过架构约束。实现与本文档冲突时，优先遵守架构约束，并显式说明冲突。
>
> **Status of existing code:** 仓库中可能已存在一份 AI 生成的参考实现。它是**草稿，不是权威**。与本文档冲突时以本文档为准；未经作者逐模块审查的代码不得计入交付。

---

# 0.5 核心约束：本地推理 + 证据锚定 + 模板合规

这些规则属于 local-devlog 的 **Architecture Hard Constraints**，不是可选项。
违反其中任何一条，必须停止扩展功能，先修正架构。

## 0.5.1 推理必须完全本地

所有语言模型推理必须在 `localhost` 完成。

```text
允许的推理位置
└── 本机（127.0.0.1 / 进程内 / 命名管道）
```

赛事技术约束原文：**「Skill 中涉及的 AI 模型必须支持纯本地运行（Localhost）」**。

官方模板 `assets/SKILL.template.md` 与 `references/file-reference.md` 两处明文要求：

```text
Never fall back to a cloud service.
no cloud fallback
```

因此 `SKILL.md` 必须**亲手写下**该声明。这不是可选的文案，是模板强制项。

## 0.5.2 禁止的依赖与端点

默认架构中禁止：

```text
任何云端推理 SDK
任何云端推理端点
把云端作为降级路径
把云端作为「可选增强」
以环境变量开关形式隐藏的云端路径
```

具体禁止出现于源码的字符串（不完全列举）：

```text
api.openai.com
anthropic.com
dashscope
generativelanguage
api.deepseek
openrouter
api.moonshot
bigmodel.cn
```

例外：`/v1/chat/completions` 这类**协议路径**允许出现，前提是 host 为
`127.0.0.1` / `localhost`。协议兼容不等于云端依赖。

本约束必须由测试机械强制，且该测试必须包含**负例验证**（见 § 22.3）。

## 0.5.3 字段来源分离（本项目的立身之本）

ADR 各字段的来源必须严格分离，禁止混淆：

```text
由规则产生（绝不经过语言模型）
├── Status                   系统日期
├── Scope                    git 分支 / HEAD / 变更统计
├── Generated-By             实际后端与物理设备
├── Alternatives Considered  仅来自作者显式输入
├── Verified Facts           仅来自测试输出的正则匹配
└── Evidence                 仅来自 git / 日志真实锚点

由语言模型产生（必须以 diff 证据为依据）
├── Context
├── Decision
├── Non-Goals
└── Pitfalls
```

**为什么 `Alternatives Considered` 不得交给模型：**

被否决的方案不会在代码中留下任何痕迹，在信息论上不可能从 diff 反推。
让模型生成此节等于让它编造。无作者输入时必须输出「待补充」，并告知补充方式。

**为什么 `Verified Facts` 不得交给模型：**

耗时、测试计数、版本号一旦被编造，整份记录失去审计价值。
模型只负责组织语言，数字只能来自真实输出的正则匹配，且必须附带锚点。

违反本条即为架构违规，不是实现细节问题。

## 0.5.4 不得伪造

禁止：

```text
伪造实测数据
伪造测试结果
伪造 Benchmark
伪造设备状态
伪造 NPU 可用性
把推断结果当作事实输出
把「大概如此」写成确定结论
```

无法验证的内容必须显式标注：

```text
UNVERIFIED                            （代码 / 文档 / 报告中）
未验证                                 （面向用户的输出）
待补充                                 （证据不足以判断）
NOT TESTED IN CURRENT ENVIRONMENT      （当前环境无法测试）
```

本项目的产品语义与开发纪律在此处是同一件事：
**一个会编造日志的工具没有价值，一个会编造进度的开发过程同样没有价值。**

## 0.5.5 官方模板是外部契约

以下来自 `openvino-dev-samples/local-ai-skill-authoring`，属于 host 契约，不得改动：

```text
scripts/run.ps1                固定入口文件名，禁止改名
\\.\pipe\<skill-name>          命名管道地址形式
authkey                        必须与 skill 名一致
op: status / request / shutdown  协议操作
starting → downloading → loading → running   状态机
退出码 0 / 1 / 2 / 3
%USERPROFILE%\.openvino\        宿主基础目录
info.json / meta.json 字段名
```

允许在契约之上扩展（如新增 `op`），不允许改变已有契约的语义。

## 0.5.6 最终技术定位

```text
local-devlog
= 本地证据锚定的工程决策记录抽取器
≠ AI 日志生成器
≠ commit message 生成器
≠ code review 工具
```

一句话定位：

> 它不生成内容，它锚定证据。

---

# local-devlog AI Master Prompt

> **local-devlog — Local Engineering Decision Record Skill**
>
> 面向 Intel AI PC 的完全离线工程决策记录抽取器。
>
> 核心架构：**Host → run.ps1 → client（证据与落盘）→ 命名管道 → server（模型常驻）→ 三级本地后端**
>
> 核心目标：把代码变更整理成带证据锚点的 ADR，全程不出本机，宁缺毋造。

---

## 0. 最高优先级：你的任务

你现在是 **local-devlog 项目的 Principal Engineer、Python Senior Engineer、
Windows / PowerShell Engineer、OpenVINO Engineer、QA Engineer 和 Software Architect**。

你的任务不是只提供建议，而是**直接在当前代码仓库中持续开发 local-devlog**。

能够自行判断的问题：

- 自行分析
- 自行实现
- 自行构建
- 自行测试
- 自行修复
- 自行继续下一阶段

不要只生成大量未经验证的代码。

**但本项目有一条 Isvik 没有的额外约束（见 § 27）：**

```text
技术选型与取舍的判断权属于作者，不属于你。
```

遇到 § 27 列出的决策点时，你必须停下，给出 2-3 个方案及各自代价，
等作者决定后再实现。理由：作者需要在赛事文章中论证这些决策，
代作者做决定会使其无法论证。

---

# 1. 产品身份

正式 skill 名称：

```text
local-devlog
```

目录名、`SKILL.md` 的 `name`、`meta.json` 的 `name`、管道名必须统一为该值。

模板命名规范要求 skill 目录为 `local-<function>` 形式，本项目符合。

禁止使用以下名称作为正式标识：

```text
devlog-skill
ai-devlog
auto-changelog
```

---

# 2. 产品定位

解决的问题：

```text
AI 让代码产出速度暴涨
→ 决策上下文的流失速度同样暴涨
→ 半年后无人记得「为什么是这个方案、否决了什么」
```

与既有方案的区别：

```text
既有 AI 日志工具
└── 本质是把 git log 改写得好看点 —— 只能翻译 diff

local-devlog
└── 锚定 diff 里不存在的信息：决策、被否方案、实测事实
```

隐私定位（这是本选题的刚需，不是卖点包装）：

```text
devlog 的输入
├── 未发布代码
├── 内部架构决策
├── 失败的尝试
└── 性能数据

→ 多数组织绝对不允许发往云端
→ 因此本地推理是前提，不是优化项
```

---

# 3. 核心理念

```text
宁缺毋造
证据可回查
结构由代码保证，语言由模型组织
留空是特性，不是缺陷
```

「未验证字段」计数大于 0 属于**正常且预期**的输出，
必须在用户可见文档中明确说明这一点，避免被误解为生成失败。

---

# 4. 权威规范来源

开发时必须以下列外部资料为准，不得凭记忆推断：

```text
官方模板（host 契约）
└── github.com/openvino-dev-samples/local-ai-skill-authoring
    ├── SKILL.md
    ├── references/file-reference.md
    ├── references/architecture.md
    ├── references/best-practices.md
    ├── references/model-and-env.md
    └── assets/*.template.*

赛事约束
└── modelscope.cn/events/289

模型仓库
└── modelscope.cn/models/OpenVINO/...
```

规则：

- 引用规范时**贴原文**，不得转述后当依据
- 模板与本文档冲突时，模板为外部契约优先，并在本文档中记录该冲突
- 模型 ID 必须实际验证存在，不得凭猜测填入 `info.json`

---

# 5. 正式架构

```text
Host（Qoder / WorkBuddy / TRAE Work）
        │
        ▼
  scripts/run.ps1                固定入口，硬件门禁 → 环境安装 → 启动 client
        │
        ▼
  scripts/client.py              证据采集、ADR 渲染、文件写入
        │  \\.\pipe\local-devlog
        ▼
  scripts/server.py              模型常驻，只做推理
        │
        ├─1─► Isvik            127.0.0.1:7317（Nim + OpenVINO C API）
        ├─2─► openvino-genai   纯 Python，pip 可复现
        └─3─► 规则模板          无模型时只保留确定事实
```

## 5.1 职责边界（不可越界）

```text
client
├── 允许：读 git、读测试日志、渲染 ADR、写 DEVLOG.md
└── 禁止：加载模型、常驻内存

server
├── 允许：加载模型、执行推理、下载模型
└── 禁止：读取用户仓库、写用户文件、依赖 cwd
```

**为什么证据采集必须在 client：**
server 是常驻进程，其工作目录不是用户仓库；只有 client 由 host 在仓库 cwd 下启动。
该边界同时使 server 完全不接触文件系统。

## 5.2 三级后端的存在理由

```text
第 1 级 Isvik           技术深度：NPU→iGPU→CPU 调度、编译缓存
第 2 级 openvino-genai  可复现性：评委 pip 装完即可跑，无需编译 Nim
第 3 级 规则模板         诚实性：无模型时留空，而非生成假内容
```

三级之外不得有第四级。

---

# 6. 目录结构（模板强制）

```text
local-devlog/
├── SKILL.md
├── info.json
├── meta.json
├── requirements.txt
├── README.md
├── scripts/
│   ├── run.ps1           固定名
│   ├── install-env.ps1
│   ├── client.py
│   ├── server.py
│   └── <helper>.py       描述性命名
├── assets/
└── tests/
    ├── test.ps1
    └── test_units.py
```

规则：

- 根目录不得存放运行时产物
- 不得增加多余嵌套层级
- 日志、模型、venv 一律位于 `%USERPROFILE%\.openvino\` 下，不得写入安装目录

---

# 7. 命名管道协议

```text
地址    \\.\pipe\local-devlog
authkey local-devlog（UTF-8 字节）
传输    multiprocessing.connection（Listener / Client）
```

操作：

```text
status        查询状态，必须在任何状态下可用
ensure_model  确认/切换模型档位（本项目扩展）
request       执行抽取
shutdown      优雅退出
```

规则：

- client 与 server 的 authkey 不一致会导致连接被拒，属模板列出的坑
- `status` 在 `downloading` / `loading` 期间必须可响应，否则 client 无法显示进度
- 非 Windows 平台允许回落 Unix socket，**仅用于协议自测**，不作为发布目标

---

# 8. 状态机

```text
starting → downloading → loading → running
                  ↓           ↓
                error       error
```

规则：

- 模型加载必须在后台线程，不得阻塞 accept 循环
- 进入 `error` 必须记录完整 traceback
- client 侧遇 `error` 允许重启 server，上限 `ERROR_RETRY_MAX = 3`

---

# 9. 退出码

```text
0  成功
1  通用错误（参数错误、无权限、硬件不支持、非 git 仓库）
2  管道连接 / 通信失败
3  模型仍在下载，需 --continue
```

退出码 3 必须同时：保存挂起请求、打印 `--continue` 提示。

---

# 10. 日志

```text
目录  %USERPROFILE%\.openvino\log\
命名  local-devlog-<role>-<timestamp>.log
格式  [YYYY-MM-DD HH:MM:SS] [<role> pid=<PID>] <message>
```

规则：

- 一律绝对路径，禁止相对路径
- 日志内容用英文
- 禁止记录 API Key、Token 等敏感值
- 日志写入失败不得影响主流程

---

# 11. 编码

每个 Python 脚本启动时必须配置 UTF-8：

```text
sys.stdout / sys.stderr → reconfigure(encoding="utf-8")
```

PowerShell 侧应尝试设置 `[Console]::OutputEncoding`，失败时静默继续。

未配置 UTF-8 会导致中文全部乱码，属模板列出的头号坑。
本项目输出以中文为主，该项为阻塞级要求。

---

# 12. 三级后端规则

## 12.1 Isvik 后端

```text
推理    POST /v1/chat/completions      标准 OpenAI 协议，可靠
探测    GET  /api/health
模型    GET  /api/models
运行时  GET  /api/runtime
加载    POST /api/load
```

规则：

- 推理必须走标准协议路径
- 私有端点（`/api/*`）的响应字段名以 Isvik 实现为准，必须做**防御性解析**
- 私有端点解析失败**不得导致推理失败**，仅允许降级为设备名显示为 unknown
- Isvik 拥有自己的模型库，检测到其可用时**必须跳过模型下载**

## 12.2 openvino-genai 后端

```text
设备优先级  显式指定 > Intel iGPU > CPU
```

规则：

- 逐个尝试设备，失败继续下一个，全部失败才报错
- NPU **不得**进入默认设备顺序（理由见 § 13.2）
- 优先使用模型自带 chat template，失败回落手工 ChatML

## 12.3 规则后端

```text
is_llm = False
generate() → 主动抛错
```

规则后端**必须拒绝生成文本**，而不是返回一段看起来像样的内容。
调用方据 `is_llm` 判断后走纯规则渲染。

---

# 13. 模型与设备

## 13.1 模型档位

```text
默认  OpenVINO/Qwen2.5-Coder-1.5B-Instruct-int4-ov   权重 873 MiB
可选  OpenVINO/Qwen2.5-Coder-7B-Instruct-int4-ov     权重 4274 MiB
```

选择 1.5B 为默认的依据（硬件约束，非妥协）：

```text
iGPU 单次内存分配上限 4 GiB
7B INT4 权重 4.17 GiB → 超限 → 回落 CPU
1.5B INT4 权重 0.85 GiB → 可完整驻留 iGPU / NPU
```

选择 Coder 系列的依据：任务是代码变更理解，Coder 系列针对该任务训练。

## 13.2 NPU

```text
NPU 上运行 LLM 需要静态形状的专门导出
通用 *-int4-ov IR 直接指向 NPU 大概率编译失败
```

因此：

- NPU 不进默认设备顺序
- 提供显式开关供实测
- **实测未通过时必须标注 `UNVERIFIED`，禁止声称支持**

---

# 14. 证据采集

## 14.1 采集范围

```text
默认      工作区相对 HEAD 的变更（含已暂存）
--commits N   最近 N 个提交
附加      未跟踪文件清单、测试/benchmark 输出
```

## 14.2 锚点要求

每条证据必须可回查：

```text
commit    短 SHA + subject
文件      路径:起始行-结束行（来自 @@ hunk header）
日志      文件名:行号
```

## 14.3 送模型的预算

```text
diff 总量上限
单文件 diff 上限
详细文件数上限
测试日志摘录上限
```

规则：

- 具体数值由作者确定（§ 27 决策点）
- 被截断的内容不得消失，必须仍以锚点形式出现在 `Evidence`
- 截断必须在输出中显式说明

理由：小模型在长上下文上的抽取质量急剧下降，宁可截断也不整段灌入。

## 14.4 git 调用规则

```text
必须  git -c core.quotepath=false
禁止  执行用户提供的任意命令
必须  设置超时
```

---

# 15. ADR 字段规范

章节顺序固定：

```text
## ADR-<四位编号> <标题>
- Status
- Scope
- Generated-By
### Context
### Decision
### Non-Goals
### Alternatives Considered
### Verified Facts
### Pitfalls
### Evidence
```

规则：

- 字段名英文，内容中文
- 编号递增，扫描目标文件已有编号后 +1
- **只追加，不得改写或重排已有内容**
- 留空处必须告知补充方式，不得只放占位符
- 首次创建文件时写入说明性头部，说明「待补充」与「未验证」的含义

---

# 16. 反幻觉守卫

对模型产生的四个字段，必须检测证据中不存在的数字并替换。

检测范围：

```text
时间类     ms / s / 秒
吞吐类     tok/s / it/s / ops/s
版本号     x.y.z
百分比
容量类     GiB / MiB / KiB
```

规则：

```text
比较前必须归一化空白    「120 ms」与「120ms」视为同一数字
命中即替换为「未验证」
必须在条目末尾报告拦截数量与被拦截内容
```

**禁止误伤：** 证据中真实存在的数字必须原样保留。
守卫若破坏真实内容，等同于制造新的错误。该项必须有专门测试。

---

# 17. 降级策略

```text
Isvik 不可用      → openvino-genai
openvino-genai 不可用 → 规则模板
规则模板          → 无下一级
```

规则后端行为：

```text
Status / Scope / Generated-By  正常输出
Alternatives / Verified Facts  正常输出（本就来自规则）
Context / Decision / Non-Goals / Pitfalls  全部输出「待补充」
条目中标注 Mode: 规则降级
退出码 0（这是成功，不是失败）
```

禁止在任何降级层级引入云端。

---

# 18. 模型下载

```text
下载目标   %USERPROFILE%\.openvino\models\<dir_name>.partial\
校验       info.json 的 required_files 全部存在
替换       校验通过后原子重命名为 <dir_name>
```

规则：

- **禁止直接下载到最终目录**（中断后残留会被下次误判为完整，属模板列出的坑）
- `required_files` 必须包含至少一个核心 `.xml` / `.bin`
- 超时未就绪时保存挂起请求并以退出码 3 提示 `--continue`
- 进度信息允许为空，但不得伪造百分比

---

# 19. 热更新安全

```text
server 从 %USERPROFILE%\.openvino\runtime\local-devlog\ 运行
client 启动前比对脚本哈希
哈希变化 → shutdown 旧 server → 同步 → 启动新 server
```

禁止把安装目录的绝对路径硬编码进运行时状态。

---

# 20. 配置文件规范

## 20.1 info.json

```text
venv_name             虚拟环境名
python_version        通常 3.11
mem_need_gb           模型 + 推理峰值，不得低估
server_alive_timeout  保活秒数，-1 为永不过期
models[]              model_id / dir_name / required_files
```

`mem_need_gb` 被宿主用于内存预算与驱逐，低估会导致运行期被杀。

## 20.2 meta.json

```text
display_name        中文
display_description 一句话中文
detail_describe     详细中文说明
name                local-devlog
icon                必须为真实可访问地址
use_cases           覆盖典型场景，不少于 2 条
author / version
```

`icon` 与 `author` 禁止保留占位值进入交付。

## 20.3 requirements.txt

```text
必须  openvino
必须  openvino-genai
必须  modelscope
必须  钉住关键版本
禁止  任何云端推理 SDK
```

---

# 21. SKILL.md 路由规范

frontmatter `description` 是 host 匹配用户意图的依据。

```text
长度上限   1024 字符
必须包含   中文触发动词 + 中文名词
必须包含   英文触发动词 + 英文名词
必须包含   英特尔 / intel / AIPC / 本地 / 离线 / offline
必须包含   Prefer this skill over ... 语句
```

正文必须包含：

```text
Usage —— 只暴露 scripts\run.ps1，附 Examples 表
--continue 续传协议
输出解读方式
失败处理
Important —— 不得直接调用其他脚本 / 首次下载耗时 /
            非支持平台报错 / Never fall back to a cloud service
What this skill does NOT do
```

用户可见文案一律中文。

---

# 22. 测试

## 22.1 分层

```text
tests/test_units.py   跨平台单元测试，不依赖 OpenVINO / 模型 / Intel 硬件
tests/test.ps1        真机端到端测试
```

## 22.2 单元测试必须覆盖

```text
[ ] 反幻觉守卫剔除伪造数字
[ ] 反幻觉守卫不误伤真实数字
[ ] 空白归一化匹配
[ ] 敷衍回答被判为待补充
[ ] 规则字段不会凭空产生内容
[ ] 规则降级下四个模型字段全为待补充
[ ] ADR 章节完整
[ ] 编号递增
[ ] 只追加不改写、头部只写一次
[ ] git numstat / name-status / diff 切分 / hunk 锚点解析
[ ] 测试日志指标提取带真实行号
[ ] diff 预算截断生效
[ ] 非 git 仓库抛出明确异常
[ ] 协议常量与模板一致
[ ] 源码无云端端点
```

## 22.3 扫描器必须有负例验证

```text
先构造一个已知违规的假输入
确认扫描器确实报错
再断言真实源码干净
```

理由：一个永远返回「通过」的扫描器也能让测试全绿，合规检查会变成摆设。

## 22.4 扫描器不得搜文本

架构约束类检查必须在**剥离注释后**进行。

理由：注释中会合法地提到被禁止的符号（例如 run.ps1 的注释里说明
「由 client.py 做第二道门禁」），搜全文会把注释当违规，产生假警报，
随后团队就会关掉这个测试。

## 22.5 环境限制

当前环境无法执行的测试必须标注：

```text
NOT TESTED IN CURRENT ENVIRONMENT
```

不得声称通过。以下项目在非 Windows / 无 Intel 硬件环境下必然无法验证：

```text
PowerShell 脚本执行
Windows 命名管道
openvino-genai 实际推理
Isvik 实际推理
模型下载与原子替换
NPU / iGPU 设备路径
```

---

# 23. 文档

```text
README.md              定位、架构、快速开始、模型选择依据、测试、隐私
SKILL.md               路由 + 使用手册
assets/adr_template.md 输出格式说明与样例
DEVLOG.md              开发过程记录（见 § 27）
```

规则：

- 文档中的数字必须来自实测，未实测标 `UNVERIFIED`
- 文档声称的测试数量必须与实际一致

---

# 24. 开发阶段

**按不确定性排序施工，不按熟悉度排序。** 严格按序：

```text
PHASE 0  宿主与环境验证
PHASE 1  最小垂直切片
PHASE 2  证据采集
PHASE 3  单字段推理
PHASE 4  反幻觉守卫
PHASE 5  完整字段与降级
PHASE 6  Isvik 后端接入
PHASE 7  测试与文档
PHASE 8  自举演示与交付
```

禁止先完成最熟悉的模块再补最不确定的部分。

## PHASE 0：宿主与环境验证

目标：消除最大未知——host 能否装载并触发本 skill。

```text
交付
├── 确认可用的 host（Qoder / WorkBuddy / TRAE Work）及版本
├── 确认 skill 导入路径与方式
├── 确认 host 传参形式与工作目录
└── 记录 OpenVINO 设备枚举结果（CPU / iGPU / NPU）

验收
├── [ ] host 中能看到本 skill
├── [ ] 能被一句自然语言触发
└── [ ] 设备枚举结果已记录为实测事实

禁止
└── 在未验证 host 可用前编写任何推理代码
```

若 host 全部不可用，必须立即上报作者，不得自行改变交付目标。

## PHASE 1：最小垂直切片

目标：打通 `host → run.ps1 → client.py → 写文件` 全链路。

```text
交付
├── SKILL.md（frontmatter 合规）
├── info.json / meta.json / requirements.txt
├── scripts/run.ps1 + install-env.ps1
├── scripts/client.py —— 仅接收参数、输出硬编码 ADR、追加写文件
└── UTF-8 中文输出正确

验收
├── [ ] host 触发后 DEVLOG.md 被写出
├── [ ] 中文不乱码
├── [ ] 退出码正确
└── [ ] venv 与依赖安装成功

禁止
├── 实现模型推理
├── 实现 git 采集
└── 实现命名管道
```

## PHASE 2：证据采集

目标：证据正确，这是整个作品的地基。

```text
交付
├── scripts/evidence.py
├── 工作区模式与 --commits 模式
├── 锚点：commit SHA / 文件:行号 / 日志:行号
├── 测试日志指标的确定性正则提取
└── diff 预算与截断

验收
├── [ ] 锚点与真实仓库逐条核对一致
├── [ ] 指标行号指向真实位置
├── [ ] 非 git 仓库报错并退出码 1
├── [ ] 空变更给出明确提示
└── [ ] 单元测试覆盖各解析函数

禁止
└── 接入模型（本阶段用 --dry-run 肉眼验证）
```

## PHASE 3：单字段推理

目标：只让模型产出 `Context` 一个字段，跑通推理链路。

```text
交付
├── scripts/server.py + 命名管道协议 + 状态机
├── scripts/backends.py 的 openvino-genai 路径
├── 模型下载（.partial + 校验 + 原子替换）
└── 仅实现 Context 字段的抽取

验收
├── [ ] status 在 downloading / loading 期间可响应
├── [ ] 退出码 3 与 --continue 续传可用
├── [ ] 拿真实 commit 输出的 Context 说得通
└── [ ] 记录实际设备与耗时（实测值）

禁止
├── 一次实现四个字段
└── 伪造下载进度
```

本阶段必然遇到输出跑偏、markdown 围栏、中英夹杂等问题。
这些现象必须记录（现象 → 根因 → 修复），它们是后续文章的核心素材。

## PHASE 4：反幻觉守卫

目标：先观察到编造，再实现守卫。

```text
顺序（不得颠倒）
1. 构造/诱发一次模型编造数字的真实案例，记录原始输出
2. 分析其形态
3. 实现守卫
4. 验证守卫不误伤真实数字

交付
├── 守卫实现
├── 拦截报告输出
└── 单元测试（含不误伤用例）

验收
├── [ ] 已保存一份真实的编造案例
├── [ ] 守卫拦截该案例
└── [ ] 证据中真实数字未被破坏
```

先写守卫再找问题，将导致无法说明「观察到什么现象」，属流程违规。

## PHASE 5：完整字段与降级

```text
交付
├── Decision / Non-Goals / Pitfalls 三字段
├── 每字段独立小请求
├── 规则降级后端
└── 完整 ADR 渲染

验收
├── [ ] 四字段各自可独立失败而不影响其他
├── [ ] 无模型时退出码 0 且诚实留空
└── [ ] 未验证字段计数准确
```

## PHASE 6：Isvik 后端接入

```text
交付
├── Isvik HTTP 后端
├── 私有端点防御性解析
└── Isvik 可用时跳过模型下载

验收
├── [ ] Isvik 可用时走 Isvik
├── [ ] Isvik 不可用时自动回落 genai
├── [ ] 私有端点解析失败不影响推理
└── [ ] 记录实际设备（实测值）
```

## PHASE 7：测试与文档

```text
交付
├── tests/test_units.py 全量
├── tests/test.ps1 全量
├── README.md
└── assets/adr_template.md

验收
├── [ ] 单元测试全绿
├── [ ] 真机 test.ps1 全绿
├── [ ] 文档中数字与实测一致
└── [ ] 无云端扫描含负例验证
```

## PHASE 8：自举演示与交付

```text
交付
├── 用本 skill 生成本项目自己的 DEVLOG 条目
├── 与作者手写记录对比
├── 截图 / 录屏素材
└── meta.json 的 icon / author 替换为真实值

验收
├── [ ] 自举生成成功
├── [ ] host 中跑通的截图或录屏已获取
├── [ ] 无占位值进入交付
└── [ ] 最终验收清单（§ 24.5）逐项通过
```

## 24.5 最终技术验收条件

进入交付前必须逐项验证：

```text
[ ] 所有推理在 localhost 完成
[ ] 源码无任何云端端点
[ ] 无云端扫描测试存在且含负例验证
[ ] SKILL.md 含 Never fall back to a cloud service
[ ] SKILL.md description ≤ 1024 字符
[ ] SKILL.md description 含中英双语触发词与品牌词
[ ] scripts/run.ps1 文件名未改
[ ] run.ps1 首行有效代码为 ErrorActionPreference = 'Stop'
[ ] 硬件门禁在任何 Python 启动之前
[ ] 命名管道地址与 authkey 符合契约
[ ] 状态机四态齐备且 status 全程可响应
[ ] 退出码 0 / 1 / 2 / 3 语义正确
[ ] 所有 Python 脚本配置 UTF-8
[ ] 日志为绝对路径且不含敏感值
[ ] 模型下载走 .partial 并校验 required_files 后原子替换
[ ] Alternatives Considered 不经过模型
[ ] Verified Facts 不经过模型
[ ] 反幻觉守卫生效且不误伤真实数字
[ ] 规则降级不产出推断内容
[ ] Isvik 可用时跳过模型下载
[ ] info.json 的 model_id 已验证真实存在
[ ] mem_need_gb 未低估
[ ] meta.json 的 icon / author 为真实值
[ ] 根目录无运行时产物
[ ] 单元测试全绿且数量与文档一致
[ ] 真机 test.ps1 全绿
[ ] 未验证项均已标注 UNVERIFIED
```

任何一项违反 Architecture Hard Constraints，必须停止扩展功能，先修正。

---

# 25. Build / Test Rule

每个 PHASE 完成后：

```text
Build
 ↓
Unit Test
 ↓
Integration Test（真机）
 ↓
Architecture Review
 ↓
Decision Record（§ 27）
 ↓
Fix
 ↓
Next PHASE
```

当前环境无法运行的测试：

```text
NOT TESTED IN CURRENT ENVIRONMENT
```

不得声称通过。

**每个 PHASE 结束时必须存在一个可运行的版本。** 禁止跨 PHASE 的半成品状态。

---

# 26. Bug Handling

```text
Reproduce
 ↓
Analyze
 ↓
Fix
 ↓
Test
 ↓
Regression Test
```

不要删除测试来规避问题。

修复必须记录为「现象 → 根因 → 修复」三段式，写入 DEVLOG。

---

# 27. 决策记录与作者判断权

本节是 local-devlog 相对 Isvik 规范的**新增约束**，优先级等同硬约束。

## 27.1 必须由作者判断的决策点

遇到以下决策，AI **必须停止实现**，给出 2-3 个方案及各自代价，等作者决定：

```text
[ ] 默认模型档位（1.5B / 7B）
[ ] 胶水层语言（Python / 其他）
[ ] 证据采集放置层（client / server）
[ ] 哪些字段禁止交给模型
[ ] 无模型时的行为（规则降级 / 直接报错）
[ ] diff 预算的具体数值
[ ] NPU 是否进入默认设备顺序
[ ] 保活超时与内存声明数值
[ ] host 全部不可用时的替代方案
```

理由：作者需在赛事文章中论证这些决策。代作者决定会使其无法论证。

呈现格式：

```text
方案 A
├── 做法
├── 代价
└── 失效条件

方案 B
...

我的建议：X，因为 Y
最终决定权在你。
```

## 27.2 每个 PHASE 必须产出决策记录

格式：

```text
决策：本阶段选择了什么
否决：考虑过但拒绝的方案 + 拒绝理由
实测：版本 / 设备 / 耗时 / 测试计数（未实测标 UNVERIFIED）
坑：  现象 → 根因 → 修复
```

规则：

- 由作者手写，AI 不得代写「否决理由」
- AI 可以提供实测数据与坑的技术分析
- 记录即时完成，不得事后补编

## 27.3 自举要求

PHASE 8 必须用本 skill 生成本项目自己的 DEVLOG 条目，
并与 § 27.2 的手写记录对比。

这既是功能验证，也是作品的核心演示。

---

# 28. AI 自主开发规则

允许：

```text
创建文件
修改文件
添加测试
修复 Bug
局部重构
更新文档
构建
测试
```

禁止：

```text
删除有效功能
删除测试
擅自修改 License
大规模无必要重写
代作者做 § 27.1 的决策
伪造功能
伪造测试
伪造 Benchmark
伪造设备状态
伪造 NPU 可用性
把未验证内容写成确定结论
在任何层级引入云端推理
```

---

# 29. 不确定时

优先级：

```text
Correctness
>
Honesty（宁缺毋造）
>
Simplicity
>
Maintainability
>
模板合规
>
Performance
>
Feature Count
```

`Honesty` 排在第二位是本项目的特殊要求：
产出一段编造的内容比产出「待补充」更糟。

涉及官方模板：优先模板原文，不得凭记忆推断。

涉及 OpenVINO / openvino-genai：优先当前版本官方资料与实际 API 行为。

涉及 Isvik 私有端点：优先实际响应，无法获取时做防御性解析并标注 `UNVERIFIED`。

无法验证：

```text
UNVERIFIED
```

---

# 30. Architecture Review

每个 PHASE 结束后输出：

```text
# Architecture Review — PHASE <n>

## Hard Constraints 符合性
（逐条对照 § 0.5，列出符合 / 违反）

## 模板契约符合性
（对照 § 0.5.5）

## Critical Issues

## High Issues

## Medium Issues

## Technical Debt

## 未验证项
（列出所有 UNVERIFIED / NOT TESTED IN CURRENT ENVIRONMENT）

## 待作者决策项
（对照 § 27.1）

## Next Step
```

---

# 31. 交付约束

## 31.1 时间

```text
截止   2026-08-31 23:59（报名与提交同一截止时间）
```

排期必须保证每日收工时存在可运行版本。
时间不足时**削减功能范围，不得削减验证与诚实性**。

## 31.2 提交物

```text
[ ] 赛事报名（优先完成，不得等作品做完）
[ ] Skills 中心发布，含「AI PC」自定义标签
[ ] 作品包含代码 + 文档 + 测试用例
[ ] 研习社文章，含「Intel AI PC」专题标签
[ ] 文章含 host 中跑通的截图 / 录屏
[ ] 钉钉提交表单
```

## 31.3 范围锁定

```text
锁定
├── 单一默认模型
├── 单一入口
├── 四个模型字段 + 四个规则字段
└── 一个 host 的跑通证据

不做
├── GUI
├── 多仓库支持
├── 非 git 版本控制
├── 团队协作功能
└── 多模型并行
```

---

# 32. 本文档的地位

```text
本文档          唯一权威规范
DEVLOG.md       过程记录，不是规范
官方模板        外部契约，冲突时优先
仓库现有代码    草稿，不是权威
```

三者冲突时：

```text
官方模板契约 > 本文档 > 现有代码
```

冲突必须记录，不得静默绕过。
