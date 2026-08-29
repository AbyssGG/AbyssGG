# local-devlog 开发规格书（AI 可自主执行版）

> **本文件是自包含的。** AI 拿到它即可从零构建整个 skill，全程无需向用户提问。
> 所有技术决策已在 § 2 给出最终结论，不得再回头询问。
>
> **语言：** 中文优先。文档、代码注释、用户可见输出一律中文；日志与内部错误用英文。
>
> **冲突处理顺序：** 官方模板契约 > 本文档 > 仓库现有代码。
> 仓库若已存在实现，视为**草稿**，可参照但必须按本文档逐项校验。

---

## 使用方法（给人看，AI 跳过本节）

1. 把本文件整份交给 AI（Qoder / Claude / 任意有文件读写与命令执行能力的 Agent）。
2. 复制下面这段作为第一条指令：

```text
读完 local-devlog_BUILD_SPEC.md 全文，然后按 § 6 从 STAGE 1 开始施工。
规则：
- 一次只做一个 STAGE，做完立刻执行该 STAGE 的自测命令并把真实输出贴给我
- 自测不通过就修到通过，不要进入下一个 STAGE
- § 2 的决策已经定了，不要问我选哪个
- 无法在当前环境验证的项，标注 NOT TESTED IN CURRENT ENVIRONMENT，不要声称通过
先输出你对本文档硬约束的理解清单（§ 1 逐条），然后开始 STAGE 1。
```

3. 每个 STAGE 结束时 AI 会给你一条自测命令，你在自己机器上跑一遍，把输出贴回去。
4. 环境准备见 § 8，跑不通时的排查见 § 9。

---

# 1. 硬约束（违反即返工）

## 1.1 推理必须完全本地

```text
允许的推理位置
└── 本机（127.0.0.1 / localhost / 进程内）
```

赛事技术约束：**「Skill 中涉及的 AI 模型必须支持纯本地运行（Localhost）」**

官方模板两处明文要求，且必须写进本项目的 `SKILL.md`：

```text
Never fall back to a cloud service.
```

## 1.2 禁止云端

禁止出现在源码中的字符串（不完全列举）：

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

例外：`/v1/chat/completions` 等**协议路径**允许出现，前提是 host 为
`127.0.0.1` 或 `localhost`。协议兼容 ≠ 云端依赖。

禁止以「可选增强」「环境变量开关」等形式保留云端路径。

## 1.3 字段来源必须分离

```text
由规则产生（绝不经过语言模型）
├── Status                   系统日期
├── Scope                    git 分支 / HEAD / 变更统计
├── Generated-By             实际后端与物理设备
├── Alternatives Considered  仅来自 --rejected 参数
├── Verified Facts           仅来自 --test-log 的正则匹配
└── Evidence                 仅来自 git / 日志真实锚点

由语言模型产生（必须以 diff 为依据）
├── Context
├── Decision
├── Non-Goals
└── Pitfalls
```

**`Alternatives Considered` 不得交给模型：** 被否决的方案不在代码里留痕迹，
无法从 diff 反推，让模型写等于让它编造。

**`Verified Facts` 不得交给模型：** 数字被编造则整份记录失去审计价值。

## 1.4 不得伪造

禁止伪造实测数据、测试结果、设备状态、NPU 可用性。

无法验证的必须显式标注：

```text
UNVERIFIED                          代码 / 报告
未验证                               用户可见输出（本应有数字但未提供来源）
待补充                               用户可见输出（证据不足以判断）
NOT TESTED IN CURRENT ENVIRONMENT   当前环境无法测试
```

## 1.5 官方模板契约（不可改动）

```text
scripts/run.ps1               固定入口文件名，禁止改名
\\.\pipe\local-devlog         命名管道地址
authkey = "local-devlog"      UTF-8 字节
退出码 0 / 1 / 2 / 3
%USERPROFILE%\.openvino\      宿主基础目录
info.json / meta.json 字段名
```

允许在契约之上新增（如新增 `op`），不得改变已有契约语义。

---

# 2. 已定决策（不得再询问用户）

下表所有决策**已经确定**。AI 直接按此实现，不要给选项、不要问偏好。

| 编号 | 决策项 | 结论 | 依据 |
| :-: | --- | --- | --- |
| D1 | 默认模型 | `OpenVINO/Qwen2.5-Coder-1.5B-Instruct-int4-ov` | 7B INT4 权重 4.17 GiB 超过 iGPU 单次分配上限 4 GiB，会回落 CPU；1.5B 为 0.85 GiB，可驻留 iGPU |
| D2 | 可选模型 | `OpenVINO/Qwen2.5-Coder-7B-Instruct-int4-ov`，`--model 7b` 触发 | 质量优先档，文档需注明大概率回落 CPU |
| D3 | 实现语言 | Python（胶水层）+ PowerShell（入口） | 模板契约要求 venv + requirements.txt；保证评委 pip 装完即可复现 |
| D4 | 证据采集位置 | client 侧 | server 是常驻进程，cwd 不是用户仓库；只有 client 由 host 在仓库 cwd 下启动 |
| D5 | 文件写入位置 | client 侧 | 同 D4 |
| D6 | 禁止交给模型的字段 | `Alternatives Considered`、`Verified Facts` | 见 § 1.3 |
| D7 | 无模型时行为 | 降级为规则模板，**退出码 0** | 这是成功路径而非失败：只输出确定事实，其余标「待补充」 |
| D8 | diff 总量预算 | 6000 字符 | 1.5B 模型长上下文抽取质量急剧下降；被截断内容仍以锚点形式保留 |
| D9 | 单文件 diff 预算 | 1500 字符 | 同上 |
| D10 | 详细文件数上限 | 12 个 | 同上 |
| D11 | 测试日志摘录上限 | 4000 字符，超出保留头尾 | 头部含环境信息，尾部含结论 |
| D12 | NPU | **不进默认设备顺序**，仅通过 `LOCAL_DEVLOG_DEVICE=NPU` 显式启用 | NPU 跑 LLM 需静态形状专门导出，通用 int4-ov IR 直接指过去大概率编译失败 |
| D13 | 默认设备顺序 | `Intel iGPU → CPU` | 模板 best-practices 要求 GPU-first、CPU fallback |
| D14 | `mem_need_gb` | `3.0` | 权重 0.85 GiB + KV cache + 运行时开销，不得低估 |
| D15 | `server_alive_timeout` | `600` | 一次会话可能连续写多条 ADR，保活久一点减少重载 |
| D16 | 模型生成温度 | `0.15` | 记录类任务要求稳定可复现 |
| D17 | 每字段最大 token | Context/Non-Goals 220，Decision/Pitfalls 320 | 每字段独立小请求，不做长输出 |
| D18 | 提问策略 | **每个字段一次独立小请求**，不整篇生成 | 小模型长输出结构保持能力差；失败可隔离到单字段 |
| D19 | 后端优先级 | Isvik → openvino-genai → 规则模板 | 三级之外不得有第四级 |
| D20 | Isvik 可用时 | **跳过模型下载** | Isvik 有自己的模型库，重复下载 0.9 GiB 是浪费 |
| D21 | ADR 编号 | 扫描目标文件已有最大编号 +1，四位补零 | |
| D22 | 写入方式 | **只追加，不改写不重排** | |
| D23 | 字段名 / 内容语言 | 字段名英文，内容中文 | 谷歌工程文档骨架 + 中文交付 |
| D24 | host 不可用时 | 依次尝试 Qoder → WorkBuddy → TRAE Work；全不可用则以 `scripts\run.ps1` 直接调用完成验证，并在文档标注 host 集成为 `NOT TESTED` | 不得因此改变交付目标 |
| D25 | 非 Windows 平台 | 管道回落 Unix socket，**仅用于协议自测**，不作为发布目标 | 便于在 CI / 非 Windows 机器验证协议逻辑 |

---

# 3. 目标形态

```text
local-devlog
= 本地证据锚定的工程决策记录抽取器
≠ AI 日志生成器
≠ commit message 生成器
≠ code review 工具
```

一句话：**它不生成内容，它锚定证据。**

用户视角的完整流程：

```text
用户在 Qoder 里说「把这次的决策记进开发日志」
        ↓
host 匹配 SKILL.md 的 description，调用 scripts\run.ps1
        ↓
硬件门禁 → 环境安装 → client 启动
        ↓
client 采集本仓库的 git 变更 + 测试日志 → 证据包
        ↓
命名管道送给常驻 server
        ↓
server 用本地模型逐字段抽取（只抽 4 个字段）
        ↓
client 渲染 ADR，追加写入 DEVLOG.md
        ↓
输出：条目编号、后端、设备、耗时、未验证字段数
```

---

# 4. 架构与目录

## 4.1 架构

```text
Host（Qoder / WorkBuddy / TRAE Work）
        │
        ▼
  scripts/run.ps1        硬件门禁 → install-env.ps1 → client.py
        │
        ▼
  scripts/client.py      证据采集、ADR 渲染、文件写入
        │  \\.\pipe\local-devlog
        ▼
  scripts/server.py      模型常驻，只做推理，不接触文件系统
        │
        ├─1─► Isvik            127.0.0.1:7317
        ├─2─► openvino-genai   本地 IR 模型
        └─3─► 规则模板          无模型时只保留确定事实
```

## 4.2 职责边界（不可越界）

```text
client
├── 允许：读 git、读测试日志、渲染 ADR、写 DEVLOG.md
└── 禁止：加载模型、常驻内存

server
├── 允许：加载模型、执行推理、下载模型
└── 禁止：读用户仓库、写用户文件、依赖 cwd
```

## 4.3 目录结构（模板强制）

```text
local-devlog/
├── SKILL.md
├── info.json
├── meta.json
├── requirements.txt
├── README.md
├── .gitignore
├── scripts/
│   ├── run.ps1            固定名，禁止改
│   ├── install-env.ps1
│   ├── client.py
│   ├── server.py
│   ├── backends.py
│   ├── evidence.py
│   ├── devlog_engine.py
│   └── common.py
├── assets/
│   └── adr_template.md
└── tests/
    ├── test.ps1
    └── test_units.py
```

规则：根目录不得存放运行时产物；日志 / 模型 / venv 一律位于
`%USERPROFILE%\.openvino\` 下，不得写入安装目录。

---

# 5. 精确技术规格

本节是契约，AI 必须严格按此实现，不得自行改字段名。

## 5.1 路径

```text
基础目录   %USERPROFILE%\.openvino\
日志       <基础>\log\local-devlog-<role>-<yyyyMMdd-HHmmss>.log
状态       <基础>\local-devlog\
挂起请求   <基础>\local-devlog\pending.json
运行时副本 <基础>\runtime\local-devlog\
模型       <基础>\models\<dir_name>\
venv       <基础>\venv\devlog\Scripts\python.exe
```

`role` 取值：`ps` / `env` / `client-py` / `server-py`

日志行格式：

```text
[YYYY-MM-DD HH:MM:SS] [<role> pid=<PID>] <message>
```

一律绝对路径。日志内容英文。禁止记录 API Key。日志写入失败不得影响主流程。

## 5.2 命名管道协议

```text
地址     Windows: \\.\pipe\local-devlog
         其他:    <临时目录>/local-devlog.sock
authkey  b"local-devlog"
传输     multiprocessing.connection 的 Listener / Client
```

### status

```text
请求  {"op": "status"}

响应  {"ok": true,
       "state": "starting|downloading|loading|running|error",
       "pid": <int>,
       "uptime_s": <float>,
       "progress": <float 0-100>,
       "tier": "1.5b|7b",
       "backend": "<后端名或空>",
       "device": "<设备名或空>",
       "model": "<模型名或空>",
       "error": "<traceback 或空>"}
```

`status` 必须在**任何状态下**可响应，否则 client 无法显示下载进度。

### ensure_model

```text
请求  {"op": "ensure_model", "tier": "1.5b"}
响应  {"ok": true, "switching": <bool>, "tier": "1.5b"}
错误  {"ok": false, "error": "unknown model tier: xxx"}
```

用于在等待就绪**之前**确认档位，使切档产生的下载/加载也能被统一等待。

### request

```text
请求  {"op": "request",
       "args": [<原始命令行参数>],
       "intent": "<用户输入的一句话意图>",
       "evidence": {<见 5.3>},
       "rejected": [{"option": "方案", "reason": "理由"}],
       "model_tier": "1.5b",
       "out": "DEVLOG.md",
       "dry_run": false}

响应  {"ok": true,
       "fields": {<见 5.4>},
       "backend": "<后端名>",
       "device": "<设备名>",
       "model": "<模型名>"}
错误  {"ok": false, "error": "<原因>"}
```

`state != running` 时必须返回 `{"ok": false, "error": "not ready: <state>"}`。

### shutdown

```text
请求  {"op": "shutdown"}
响应  {"ok": true, "state": "shutting_down"}
```

响应发出后关闭后端并退出进程。

## 5.3 证据包结构

client 采集后放入 `request.evidence`：

```text
{
  "repo": {"root": str, "branch": str, "head": str,
           "head_short": str, "commit_count": int},
  "mode": "working-tree" | "commits",
  "commits": [{"sha": str, "short": str, "author": str,
               "date": str, "subject": str, "body": str}],
  "files": [{"path": str, "status": str, "status_cn": str,
             "added": int, "deleted": int}],
  "untracked": [str],
  "diff_text": str,
  "diff_truncated": bool,
  "diff_total_bytes": int,
  "stats": {"files": int, "added": int, "deleted": int},
  "test_log": null | {"path": str, "name": str, "lines": int,
                      "excerpt": str, "excerpt_truncated": bool,
                      "metrics": {<指标名>: [{"value": str,
                                             "groups": [str],
                                             "line": int,
                                             "label": str,
                                             "anchor": str}]},
                      "has_metrics": bool},
  "anchors": [{"kind": "commit|file|test", "ref": str, "detail": str}],
  "empty": bool
}
```

`status` 字段取值 `A/M/D/R/C/T/U`，`status_cn` 对应
`新增/修改/删除/重命名/复制/类型变更/未合并`。

## 5.4 fields 结构

server 抽取后返回：

```text
{
  "title": str,                    # 即用户的 intent，不经模型
  "status": "已接受（YYYY-MM-DD）",
  "context": str,                  # 模型产出，或「待补充」
  "decision": str,
  "non_goals": str,
  "pitfalls": str,
  "alternatives": [{"option": str, "reason": str}],
  "verified_facts": [{"metric": str, "value": str, "anchor": str}],
  "anchors": [str],                # 已格式化的锚点行
  "guard_removed": [str],          # 被守卫拦截的数字
  "degraded": bool                 # 是否走了规则降级
}
```

## 5.5 采集规则

```text
默认模式        git diff HEAD（覆盖已暂存与未暂存）
--commits N     git diff HEAD~N..HEAD；提交数不足时退化为 git show HEAD
未跟踪文件      git ls-files --others --exclude-standard，最多列 20 个
git 调用        必须加 -c core.quotepath=false（否则中文路径被转义）
超时            30 秒
```

锚点要求：

```text
commit  短 SHA + subject
文件    路径:起始行-结束行（来自 @@ hunk header 的 +起始,长度）
日志    文件名:行号
```

预算按 D8–D11。被截断的内容**不得消失**，必须仍以锚点形式出现在 `Evidence`，
且截断事实必须在输出中显式说明。

## 5.6 测试日志指标抽取

必须用**确定性正则**抽取，不得经过模型。至少覆盖：

| 指标名 | 抽取目标 | 中文标签 |
| --- | --- | --- |
| `duration` | `took/elapsed/耗时/用时/in` + 数字 + `ms/s/sec/秒` | 耗时 |
| `tests_passed` | 数字 + `passed/ok/通过` | 测试通过 |
| `tests_failed` | 数字 + `failed/failures/失败` | 测试失败 |
| `tests_total` | `ran/total/共` + 数字 + `tests` | 测试总数 |
| `throughput` | 数字 + `tok/s、tokens/s、it/s、ops/s` | 吞吐 |
| `percentile` | `p50/p90/p95/p99` + 数字 | 分位延迟 |
| `version` | `x.y.z`（可带 `-`/`+` 后缀） | 版本 |
| `device` | `NPU / GPU.N / GPU / CPU` | 设备 |

每个命中必须记录**真实行号**并生成 `文件名:行号` 锚点。每个指标最多取 3 条进入输出。

## 5.7 ADR 输出格式

```text
## ADR-<四位编号> <标题>

- **Status**: 已接受（YYYY-MM-DD）
- **Scope**: <分支> @ <短SHA> · <N> 文件 +<A>/-<D>
- **Generated-By**: <后端> / <设备> / <模型>（本地推理）
- **Mode**: 规则降级（无可用本地模型，仅保留确定事实）   ← 仅降级时出现

### Context
### Decision
### Non-Goals
### Alternatives Considered
### Verified Facts
### Pitfalls
### Evidence

---
```

`Alternatives Considered` 为空时输出：

```text
待补充：本次未登记被否方案。

> 被否决的方案不会在代码里留下痕迹，无法从 diff 反推，因此本工具不会替你推测。
> 补充方式：`--rejected "方案|拒绝理由"`（可重复多次）。
```

`Verified Facts` 有数据时用三列表格（指标 / 值 / 证据锚点）；为空时输出：

```text
未验证：本次未提供测试或 benchmark 输出。

> 补充方式：`--test-log <路径>`，工具只登记该文件中真实出现的数字。
```

文件首次创建时写入头部，说明「待补充」与「未验证」的含义，
并声明「未验证字段计数大于 0 属正常行为」。

## 5.8 反幻觉守卫

对模型产出的四个字段执行。检测形态：

```text
时间   数字 + ms/毫秒 | s/秒/sec/seconds
吞吐   数字 + tok/s | tokens/s | it/s | ops/s | fps
版本   v?x.y.z（可带 -/+ 后缀）
百分比 数字 + % | percent
容量   数字 + GiB/MiB/KiB/GB/MB/KB
```

判定流程：

```text
1. 在字段文本中匹配上述形态，得到 token
2. 把 token 与「证据全文」都去掉所有空白并转小写
3. 归一化后的 token 不出现在归一化后的证据全文中 → 判定为编造
4. 就地替换为「（未验证）」，并记入 guard_removed
5. 条目末尾报告拦截数量与被拦截内容
```

「证据全文」= `diff_text` + 各 commit 的 subject/body + 文件路径与增删行数
+ 变更统计 + 测试日志 excerpt。

**禁止误伤：** 证据中真实存在的数字必须原样保留。
`120 ms` 与 `120ms` 必须视为同一数字（这是步骤 2 的目的）。
该项必须有专门的单元测试。

## 5.9 模型输出清洗

模型返回后依次处理：

```text
1. 去掉 markdown 代码块围栏（```开头/结尾）
2. 去掉 ChatML 残留（<|im_end|> / <|im_start|> / <|endoftext|>）
3. 去掉「回答：」「答案：」「内容：」「输出：」等前缀
4. 去掉被当成标题输出的行（^#{1,6} ）
5. 首尾去空白
```

判定为「待补充」的条件（任一成立）：

```text
清洗后为空
清洗后等于「待补充」或「未验证」
清洗后长度 < 4
清洗后为「无」「。」等敷衍内容
```

## 5.10 提问规格

系统提示必须包含以下五条硬规则（措辞可优化，语义不得削弱）：

```text
1. 只依据提供的证据作答，不得推断、不得补充证据里没有的信息
2. 不得编造任何数字（耗时、版本号、测试数量、性能指标）
3. 证据不足以回答时，只输出四个字：待补充
4. 直接输出内容本身，不要加标题、不要加解释、不要用 markdown 代码块
5. 用简体中文，语气克制，不使用营销辞令
```

四个字段的提问要点：

| 字段 | 问什么 |
| --- | --- |
| `context` | 改动前存在什么问题或需求，使这次决策成为必要。不要描述改动本身。2-3 句 |
| `decision` | 实际采用的技术决策是什么，如何解决背景中的问题。具体到模块或做法。2-4 句 |
| `non_goals` | 明确不打算解决什么，1-3 条边界。证据看不出边界就输出「待补充」 |
| `pitfalls` | 证据中是否有修复具体问题的痕迹；有则按「现象→根因→修复」各一句；无则「待补充」 |

## 5.11 三级后端

### Isvik

```text
探测   GET  /api/health
模型   GET  /api/models
运行时 GET  /api/runtime
加载   POST /api/load
推理   POST /v1/chat/completions      ← 标准 OpenAI 协议
```

规则：

- 推理**必须**走标准协议路径（可靠、有文档）
- 私有端点（`/api/*`）的响应字段名以 Isvik 实现为准，**必须做防御性解析**：
  对每个需要的值尝试多个候选字段名（如 `device` / `Device` / `physical_device`
  / `execution_device`），并递归查找嵌套 dict
- 私有端点解析失败**不得导致推理失败**，仅允许降级为设备名显示 `unknown`
- `POST /api/load` 的 body 字段名未知，依次尝试 `{"model":…}`、
  `{"model_id":…}`、`{"id":…}`
- 环境变量：`ISVIK_BASE_URL`、`ISVIK_PORT`（默认 7317）、`ISVIK_API_KEY`（可选，
  同时设置 `Authorization: Bearer` 与 `x-api-key`）
- 通信用标准库 `urllib`，不引入 `requests`

### openvino-genai

```text
接口   openvino_genai.LLMPipeline(model_dir, device)
配置   GenerationConfig: max_new_tokens / temperature / do_sample
设备   按 D13：显式指定 > Intel iGPU > CPU
```

规则：

- 逐个尝试设备，失败继续下一个，全部失败才报错并记录每个设备的失败原因
- 优先用 `pipeline.get_tokenizer().apply_chat_template(...)`，失败回落手工 ChatML：
  `<|im_start|>system\n…<|im_end|>\n<|im_start|>user\n…<|im_end|>\n<|im_start|>assistant\n`
- 输出中若含 `<|im_end|>` 等标记，截断至该标记前

### 规则模板

```text
is_llm = False
generate() → 主动抛出异常
```

**必须拒绝生成文本**，而不是返回一段看起来像样的内容。
调用方据 `is_llm` 判断后走纯规则渲染，四个模型字段全部输出「待补充」，
条目标注 `Mode: 规则降级`，退出码 0。

### 选择逻辑

```text
环境变量 LOCAL_DEVLOG_BACKEND 可强制指定：isvik | genai | rule
未指定时按 D19 依次尝试，全部失败落到规则模板（不抛异常）
```

**server 加载流程必须按此顺序，以避免无谓下载：**

```text
1. 强制 rule            → 直接用规则后端，不下载模型
2. Isvik 探测成功       → 用 Isvik，跳过模型下载（D20）
3. openvino-genai 可用  → 此时才下载模型，然后加载
4. 都不可用             → 规则后端
```

## 5.12 模型下载

```text
目标   %USERPROFILE%\.openvino\models\<dir_name>.partial\
校验   info.json 的 required_files 全部存在
替换   校验通过后原子重命名为 <dir_name>
```

规则：

- **禁止直接下载到最终目录**（中断残留会被下次误判为完整，模板点名的坑）
- 已存在且 `required_files` 齐全 → 跳过下载
- 用 `modelscope.snapshot_download(model_id, local_dir=<partial>)`
- 进度：独立监控线程周期统计 `.partial` 目录字节数 / 总字节数；
  总字节数可向 `https://www.modelscope.cn/api/v1/models/<model_id>/repo/files?Revision=master&Root=`
  查询求和，失败则用内置估值（1.5b ≈ 898 MiB，7b ≈ 4300 MiB）
- 进度信息允许为空，**不得伪造百分比**
- 超时未就绪（8 分钟）→ 保存挂起请求 → 打印 `--continue` 提示 → 退出码 3

## 5.13 热更新安全

```text
server 从 %USERPROFILE%\.openvino\runtime\local-devlog\ 运行
client 启动前对运行时脚本集合算 sha256，与副本目录中的记录比对
哈希变化 → shutdown 旧 server → 复制新脚本 → 启动新 server
```

server 从副本运行后拿不到安装目录的 `info.json`，
因此 client 启动 server 时必须通过环境变量 `LOCAL_DEVLOG_ROOT` 传入安装根目录。

Windows 下启动 server 使用
`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`。

## 5.14 状态机与错误重试

```text
starting → downloading → loading → running
                ↓            ↓
              error        error
```

规则：

- 模型加载必须在后台线程，不得阻塞 accept 循环
- 进入 `error` 必须记录完整 traceback
- client 遇 `error` 可 shutdown 并重启 server，上限 3 次，超限则报错退出码 1

## 5.15 退出码

```text
0  成功（含规则降级成功、空变更、无待续传请求）
1  通用错误（参数错误、硬件不支持、非 git 仓库、未知档位、重试超限）
2  管道连接 / 通信失败
3  模型仍在下载，需 --continue
```

## 5.16 硬件门禁

两道：

```text
第一道（run.ps1，在任何 Python 启动之前）
└── bin\platform.exe --is-aipc  返回 1 才继续
    宿主未提供该文件时跳过，交给第二道

第二道（client.py 最早期）
└── 用 openvino 枚举设备：
    openvino 不可用            → 退出码 1
    有 NPU 或 GPU              → 放行（真 AIPC）
    仅 CPU 且 CPU 名含 Intel   → 放行，但打印「将在 CPU 上推理，耗时增加」
    其他                        → 退出码 1
```

`--doctor` 必须跳过门禁（否则用户无法在不支持的机器上自查）。
`--allow-non-intel` 用于在非目标硬件上做协议自测。

## 5.17 命令行接口

```text
scripts\run.ps1 "<一句话意图>" [选项]
```

| 参数 | 说明 |
| --- | --- |
| 位置参数 | 本次决策的一句话意图（`--continue` / `--doctor` 时不需要） |
| `--commits <N>` | 分析最近 N 个提交；缺省分析工作区未提交变更 |
| `--test-log <path>` | 测试或 benchmark 输出文件 |
| `--rejected "方案|理由"` | 登记被否方案，可重复 |
| `--out <path>` | 目标文件，缺省 `DEVLOG.md` |
| `--dry-run` | 只打印不写文件 |
| `--model <1.5b\|7b>` | 模型档位 |
| `--doctor` | 打印设备与后端自检后退出 |
| `--continue` | 续传上次未完成的下载并执行挂起请求 |
| `--allow-non-intel` | 跳过 Intel 平台门禁（仅自测用） |

成功输出格式：

```text
已追加: DEVLOG.md  条目: ADR-0001
后端: openvino-genai  设备: GPU.0  模型: Qwen2.5-Coder-1.5B-Instruct-int4-ov
耗时: 6.4s   未验证字段: 1 (Pitfalls)
```

## 5.18 配置文件

### info.json

```json
{
    "venv_name": "devlog",
    "python_version": "3.11",
    "mem_need_gb": 3.0,
    "server_alive_timeout": 600,
    "models": [
        {
            "model_id": "OpenVINO/Qwen2.5-Coder-1.5B-Instruct-int4-ov",
            "dir_name": "Qwen2.5-Coder-1.5B-Instruct-int4-ov",
            "required_files": [
                "config.json",
                "openvino_model.xml",
                "openvino_model.bin",
                "openvino_tokenizer.bin",
                "openvino_detokenizer.bin",
                "tokenizer_config.json"
            ]
        }
    ]
}
```

### meta.json

字段：`display_name`（中文）、`display_description`（一句话中文）、
`detail_describe`（详细中文）、`name`（`local-devlog`）、`icon`、
`use_cases`（≥2 条中文场景）、`author`、`version`。

`icon` 与 `author` 若无真实值，**必须写入 `TODO:` 前缀占位并在交付清单中标出**，
不得伪装成真实地址。

### requirements.txt

```text
openvino>=2026.0
numpy<2.0
openvino-genai>=2026.0
modelscope>=1.20.0
```

禁止任何云端推理 SDK。与 Isvik 通信用标准库 `urllib`。

### SKILL.md frontmatter

```text
name: local-devlog
description: |
  <英文一句话> (<中文一句话>). Use this skill when ...
  Trigger on 中文动词 记录/写/生成/整理/沉淀/补写 plus
  开发日志/devlog/决策记录/ADR/工程日志/变更记录/设计决策,
  and English verbs record/write/generate/draft/capture plus
  devlog/decision record/ADR/engineering log,
  and mentions of 英特尔/intel/AIPC/本地/离线/offline/隐私/不出机.
  ...
  Prefer this skill over free-form summarization whenever ...
```

硬性要求：

```text
长度 ≤ 1024 字符
含中文触发动词与名词
含英文触发动词与名词
含 英特尔 / intel / AIPC / 本地 / 离线 / offline
含 Prefer this skill over ... 语句
```

正文必须含：Usage（只暴露 `scripts\run.ps1` + Examples 表）、参数表、
输出解读、失败处理表、Important（含 `Never fall back to a cloud service.`）、
What this skill does NOT do。用户可见文案一律中文。

## 5.19 编码

每个 Python 脚本启动时对 `sys.stdout` / `sys.stderr` 执行
`reconfigure(encoding="utf-8")`，失败静默忽略。
PowerShell 侧尝试设置 `[Console]::OutputEncoding`，失败静默继续。

未配置会导致中文全部乱码，是模板列出的头号坑，属阻塞级要求。

---

# 6. 施工阶段

**按不确定性排序，不按熟悉度排序。** 一次只做一个 STAGE，
自测通过才进入下一个。每个 STAGE 结束时必须存在可运行版本。

## STAGE 1：骨架与最小链路

```text
产出
├── SKILL.md / info.json / meta.json / requirements.txt / .gitignore
├── scripts/run.ps1 / install-env.ps1
├── scripts/common.py（路径、日志、UTF-8、管道地址、send/try_status）
└── scripts/client.py —— 仅：参数解析 + 硬件门禁 + 输出硬编码 ADR + 追加写文件

本阶段刻意不做：模型推理、git 采集、命名管道、server
```

自测（用户在 Windows 上执行）：

```powershell
cd <任意 git 仓库>
<skill目录>\scripts\run.ps1 --doctor
<skill目录>\scripts\run.ps1 "测试骨架"
type DEVLOG.md
```

```text
验收
[ ] venv 自动创建，依赖安装成功
[ ] --doctor 打印 OpenVINO 设备列表
[ ] DEVLOG.md 被写出且中文不乱码
[ ] 退出码 0
```

## STAGE 2：证据采集

```text
产出
└── scripts/evidence.py —— 按 § 5.3 / 5.5 / 5.6 实现
    client 改为打印真实证据包（仍不接模型）
```

自测：

```powershell
cd <一个有真实改动的 git 仓库>
<skill目录>\scripts\run.ps1 "测试证据" --dry-run
<skill目录>\scripts\run.ps1 "测试证据" --test-log <某个测试输出文件> --dry-run
```

```text
验收
[ ] 锚点中的 commit SHA 与 git log 一致
[ ] 文件行号区间与 git diff 的 @@ 头一致
[ ] 测试日志指标的行号指向真实位置（逐条人工核对）
[ ] 非 git 目录下报错且退出码 1
[ ] 无改动时给出明确提示且退出码 0
```

## STAGE 3：管道 + server + 单字段推理

```text
产出
├── scripts/server.py —— 按 § 5.2 / 5.12 / 5.14 实现
├── scripts/backends.py —— 先只实现 openvino-genai + 规则模板
└── scripts/devlog_engine.py —— 先只实现 context 一个字段 + 渲染 + 落盘

本阶段刻意不做：其余三个字段、反幻觉守卫、Isvik 后端
```

自测：

```powershell
# 先验证降级路径（不下载模型，快）
$env:LOCAL_DEVLOG_BACKEND = 'rule'
<skill目录>\scripts\run.ps1 "测试降级"

# 再验证真实推理（首次会下载约 0.9 GiB）
Remove-Item Env:\LOCAL_DEVLOG_BACKEND
<skill目录>\scripts\run.ps1 "测试真实推理"
```

```text
验收
[ ] rule 模式下四字段为「待补充」，退出码 0
[ ] 下载中 status 可响应，进度递增
[ ] 下载中断后 --continue 可续传，中途退出码为 3
[ ] 模型下载到 .partial 后原子改名（人工查看 models 目录）
[ ] 真实推理产出的 Context 语义说得通
[ ] 记录实际后端 / 设备 / 耗时（实测值，不得估算）
```

## STAGE 4：反幻觉守卫

**顺序不得颠倒。**

```text
1. 先诱发一次模型编造数字：
   构造一个不含任何性能数字的 diff，让模型写 Context/Decision，
   观察它是否自行编出耗时或版本号；保存原始输出
2. 分析编造内容的形态
3. 按 § 5.8 实现守卫
4. 验证守卫不误伤证据中真实存在的数字

产出
├── 守卫实现 + 拦截报告输出
└── 单元测试：拦截用例 + 不误伤用例 + 空白归一化用例
```

自测：

```powershell
python <skill目录>\tests\test_units.py
```

```text
验收
[ ] 已保存一份真实的编造案例（原始输出）
[ ] 守卫拦截该案例
[ ] 证据中真实存在的数字未被破坏
[ ] 「120 ms」与「120ms」判为同一数字
```

## STAGE 5：完整字段与降级

```text
产出
├── decision / non_goals / pitfalls 三字段（每字段独立小请求，D18）
├── 完整 ADR 渲染（§ 5.7）
├── 规则降级完整路径
└── 未验证字段计数
```

自测：

```powershell
<skill目录>\scripts\run.ps1 "完整测试" `
    --test-log <测试输出> `
    --rejected "方案A|理由A" --rejected "方案B|理由B"
type DEVLOG.md
```

```text
验收
[ ] 七个章节齐备
[ ] Alternatives 原样登记两条输入
[ ] Verified Facts 表格中的数字全部能在测试日志中找到
[ ] 单字段抽取失败不影响其他字段
[ ] ADR 编号递增，已有内容未被改写
```

## STAGE 6：Isvik 后端

```text
产出
└── Isvik HTTP 后端（§ 5.11），含防御性解析与跳过下载（D20）
```

自测：

```powershell
# Isvik 未启动时应自动回落
<skill目录>\scripts\run.ps1 --doctor

# 启动 Isvik 后应优先使用它
isvik api serve --port 7317
<skill目录>\scripts\run.ps1 "测试 Isvik 后端"
```

```text
验收
[ ] Isvik 未启动时自动走 genai，不报错
[ ] Isvik 启动后 Generated-By 显示 isvik
[ ] Isvik 路径下不重复下载模型
[ ] 私有端点解析失败不影响推理（可临时改端口模拟）
```

## STAGE 7：测试与文档

```text
产出
├── tests/test_units.py 全量（§ 7.1）
├── tests/test.ps1 全量
├── README.md
└── assets/adr_template.md
```

自测：

```powershell
python <skill目录>\tests\test_units.py
<skill目录>\tests\test.ps1 -Quick
<skill目录>\tests\test.ps1
```

```text
验收
[ ] 单元测试全绿
[ ] test.ps1 全绿
[ ] 文档中声明的测试数量与实际一致
[ ] 无云端扫描含负例验证
```

## STAGE 8：交付整理

```text
产出
├── 自举：用本 skill 生成本项目自己的 DEVLOG 条目
├── 清理根目录运行时产物
├── 列出所有 TODO 占位值（icon / author）
└── 列出所有 UNVERIFIED 项
```

```text
验收
[ ] § 7.2 最终清单逐项通过
[ ] 自举生成成功
[ ] 所有占位值与未验证项已明确列出交给用户
```

---

# 7. 测试与验收

## 7.1 单元测试必须覆盖

`tests/test_units.py` 不得依赖 OpenVINO / 模型 / Intel 硬件，任何平台可跑。

```text
[ ] 守卫剔除伪造数字
[ ] 守卫不误伤真实数字
[ ] 空白归一化匹配（120 ms == 120ms）
[ ] 输出清洗：代码块围栏 / ChatML 残留 / 前缀 / 标题行
[ ] 敷衍回答判为待补充
[ ] Alternatives 只来自输入，空输入得空结果
[ ] 缺理由时标为待补充
[ ] 无 test_log 时 Verified Facts 为空
[ ] 规则降级下四字段全为待补充且不抛异常
[ ] ADR 七章节齐备
[ ] 留空处包含补充方式提示
[ ] 守卫拦截报告被渲染
[ ] 未验证字段计数正确
[ ] 首次写入只产生一个文件头
[ ] 编号递增（1 → 2 → 43）
[ ] numstat 解析（含二进制文件的 - -）
[ ] name-status 解析
[ ] diff 按文件切分
[ ] hunk 锚点行号计算
[ ] 测试日志指标行号正确
[ ] diff 预算截断生效
[ ] 非 git 仓库抛出专用异常
[ ] 规则后端 is_llm 为假且 generate 抛错
[ ] 强制 rule 后端生效
[ ] 退出码常量与模板一致
[ ] 管道地址形态正确
[ ] authkey 与 skill 名一致
[ ] 端到端：真实临时 git 仓库 → 采集 → 规则渲染 → 落盘
```

### 无云端扫描必须含负例验证

```text
1. 构造一个含 api.openai.com 的假输入，断言扫描器报错
2. 构造一个含 127.0.0.1:7317/v1/chat/completions 的假输入，断言不误报
3. 断言真实源码干净
```

理由：一个永远返回「通过」的扫描器也能让测试全绿，合规检查会变成摆设。

### 架构类检查不得搜文本

比较代码位置顺序（如「硬件门禁必须在启动 Python 之前」）时，
**必须先剥离注释行**。

理由：注释中会合法地提到被检查的符号（例如 `run.ps1` 的注释里说明
「由 client.py 做第二道门禁」），搜全文会把注释当代码，产生假警报。

## 7.2 最终验收清单

```text
[ ] 所有推理在 localhost 完成
[ ] 源码无任何云端端点
[ ] 无云端扫描测试存在且含负例验证
[ ] SKILL.md 含 Never fall back to a cloud service
[ ] SKILL.md description ≤ 1024 字符
[ ] SKILL.md description 含中英双语触发词与品牌词
[ ] scripts/run.ps1 文件名未改
[ ] run.ps1 首行有效代码为 $ErrorActionPreference = 'Stop'
[ ] 硬件门禁在任何 Python 启动之前
[ ] 管道地址与 authkey 符合契约
[ ] 状态机四态齐备且 status 全程可响应
[ ] 退出码 0/1/2/3 语义正确
[ ] 所有 Python 脚本配置 UTF-8
[ ] 中文输出不乱码
[ ] 日志为绝对路径且不含敏感值
[ ] 模型下载走 .partial 并校验后原子替换
[ ] Alternatives Considered 不经过模型
[ ] Verified Facts 不经过模型
[ ] 守卫生效且不误伤真实数字
[ ] 规则降级不产出推断内容且退出码 0
[ ] Isvik 可用时跳过模型下载
[ ] info.json 的 model_id 真实存在
[ ] mem_need_gb 为 3.0
[ ] 根目录无运行时产物
[ ] 单元测试全绿且数量与文档一致
[ ] test.ps1 全绿
[ ] 所有未验证项已标注
[ ] 所有 TODO 占位值已列出
```

## 7.3 每阶段结束的报告格式

```text
# STAGE <n> 报告

## 产出文件
## 自测命令与真实输出
（必须贴真实输出，不得描述）
## 验收清单勾选情况
## 未通过项与原因
## 未验证项（UNVERIFIED / NOT TESTED IN CURRENT ENVIRONMENT）
## 下一步
```

---

# 8. 环境准备（用户侧，一次性）

```text
必需
├── Windows x64
├── Python 3.11（或让 uv 自动安装）
├── git（在 PATH 中）
└── 网络（仅首次下载模型与依赖）

推荐
└── Intel Core Ultra（有 iGPU / NPU）

自动处理（无需手动装）
├── uv        install-env.ps1 会自动下载到 bin/
├── venv      自动创建于 %USERPROFILE%\.openvino\venv\devlog\
└── 模型      首次运行自动下载约 0.9 GiB
```

PowerShell 执行策略若阻止脚本运行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

只想验证协议逻辑、不想下载模型时：

```powershell
$env:LOCAL_DEVLOG_BACKEND = 'rule'
```

---

# 9. 跑不通时的排查顺序

按此顺序排查，不要跳步。

```text
1. 脚本无法执行
   → 执行策略：Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

2. 中文显示成乱码或问号
   → 检查 Python 是否执行了 stdout/stderr 的 UTF-8 reconfigure
   → 检查 PowerShell 是否设置了 Console.OutputEncoding

3. venv 创建失败
   → 看 %USERPROFILE%\.openvino\log\local-devlog-env-*.log
   → 手动执行 bin\uv.exe venv --python 3.11 <venv路径> 看真实报错

4. 依赖安装失败
   → 镜像问题：install-env.ps1 应已依次尝试阿里云 / 清华 / 官方源
   → 手动激活 venv 后 pip install -r requirements.txt 看真实报错

5. 退出码 1 且提示需要 Intel 平台
   → 先跑 --doctor 看设备枚举结果
   → 仅做协议验证时加 --allow-non-intel

6. 卡在「正在下载模型」
   → 看 models 目录下的 .partial 是否在增长
   → 超过 8 分钟会自动退出码 3，之后用 --continue 续传

7. 退出码 2（管道通信失败）
   → 看 local-devlog-server-py-*.log 是否存在、有无 traceback
   → 确认 client 与 server 的 authkey 一致
   → 杀掉残留 python 进程后重试

8. server 反复进入 error
   → 日志里的 traceback 是唯一线索
   → 强制走 rule 后端确认是模型问题还是协议问题

9. 生成内容为空或全是「待补充」
   → 若 Generated-By 显示 rule-template，说明模型未加载成功，回到 7/8
   → 若显示真实后端，则是模型输出被清洗规则判为敷衍，检查 § 5.9 判定阈值

10. host 里搜不到 / 触发不了这个 skill
    → 检查 SKILL.md 的 frontmatter 是否合法 YAML
    → 检查 description 是否含用户实际说的词
    → 先用 scripts\run.ps1 直接调用，确认 skill 本身可用，再排查 host 侧
```

**任何一步的真实报错信息都必须原样保留并贴出，不得转述。**

---

# 10. AI 行为规则

允许：

```text
创建文件 / 修改文件 / 添加测试 / 修复 Bug / 局部重构 / 更新文档 / 构建 / 测试
```

禁止：

```text
删除有效功能
删除测试
大规模无必要重写
询问 § 2 已定的决策
伪造功能 / 测试 / Benchmark / 设备状态 / NPU 可用性
把未验证内容写成确定结论
在任何层级引入云端推理
用「应该可以」代替实际执行
```

不确定时的优先级：

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

`Honesty` 位列第二是本项目的特殊要求：
**产出一段编造的内容比产出「待补充」更糟。**

涉及官方模板：优先模板原文，不得凭记忆推断。
涉及 openvino-genai / Isvik：优先实际 API 行为与实际响应。
无法验证：标 `UNVERIFIED`。

---

# 11. 参考资料

```text
官方模板（host 契约，必须实际读取）
└── github.com/openvino-dev-samples/local-ai-skill-authoring
    ├── SKILL.md
    ├── references/file-reference.md
    ├── references/architecture.md
    ├── references/best-practices.md
    ├── references/model-and-env.md
    └── assets/*.template.*

赛事要求
└── modelscope.cn/events/289

模型
├── modelscope.cn/models/OpenVINO/Qwen2.5-Coder-1.5B-Instruct-int4-ov
└── modelscope.cn/models/OpenVINO/Qwen2.5-Coder-7B-Instruct-int4-ov

Isvik（可选后端）
└── github.com/AbyssGG/Isvik
```
