# local-devlog

**在英特尔 AI PC 上完全离线地把代码变更整理成带证据锚点的工程决策记录（DEVLOG / ADR）。**

源代码、diff、测试数据、架构决策全程不出本机。

---

## 它解决什么问题

AI 让代码产出速度暴涨，但**决策上下文的流失速度同样暴涨**。半年后回看一段代码，
最想知道的从来不是「改了什么」（diff 里就有），而是：

- 为什么是这个方案？
- **当时否决了哪些方案，理由是什么？**
- 有哪些数字是真实测过的？

市面上的 AI 日志工具本质是「把 git log 改写得好看点」——它们只能翻译 diff。
而上面这些信息，diff 里根本不存在。

`local-devlog` 换了一个思路：**它不生成内容，它锚定证据。**

---

## 核心设计：字段来源严格分离

这是本 skill 与「让大模型写一篇日志」的根本区别。

| 章节 | 来源 | 经过模型？ |
| --- | --- | :---: |
| `Status` / `Scope` / `Generated-By` | 系统日期、git 状态、实际推理设备 | ❌ |
| `Context` / `Decision` / `Non-Goals` / `Pitfalls` | diff 证据 | ✅ 仅组织语言 |
| **`Alternatives Considered`** | **仅** `--rejected` 用户输入 | ❌ |
| **`Verified Facts`** | **仅** `--test-log` 的正则匹配结果 | ❌ |
| `Evidence` | git / 日志的真实锚点 | ❌ |

### 为什么 `Alternatives Considered` 不交给模型

被否决的方案**不会在代码里留下任何痕迹**——它在信息论上就不可能从 diff 反推。
让模型写这一节等于让它编造。所以没有 `--rejected` 输入时，此节诚实输出
「待补充」，并告诉作者怎么补。

### 为什么 `Verified Facts` 不交给模型

耗时、测试计数、版本号一旦被编造，整份记录就失去审计价值。模型负责组织语言，
**数字只能来自真实输出的正则匹配**，每个都带 `文件:行号` 锚点可回查。

### 反幻觉守卫

即使在模型负责的四个字段里，一旦它写出证据中不存在的性能数字或版本号
（`500ms`、`v3.2.1`、`24.5 tok/s`、`8 GiB` 这类形态），守卫会**就地替换为
「未验证」**并在条目末尾报告拦截数量。

> 输出末尾的「未验证字段」计数大于 0 是**正常且预期**的行为，
> 它代表工具没有编造。这是本 skill 的特性，不是缺陷。

---

## 架构

```
Host (Qoder / WorkBuddy / TRAE Work)
        │  调用唯一入口
        ▼
  scripts/run.ps1 ──► 硬件门禁 ──► install-env.ps1 (uv 建 venv)
        │
        ▼
  scripts/client.py            ← 采集 git 证据、渲染 ADR、写文件（在用户仓库 cwd）
        │  命名管道 \\.\pipe\local-devlog
        ▼
  scripts/server.py            ← 模型常驻，只做推理，不接触文件系统
        │
        ├─1─► Isvik  (127.0.0.1:7317)   自研 Nim + OpenVINO C API 运行时
        ├─2─► openvino-genai            纯 Python 路径，pip 装完即可复现
        └─3─► 规则模板                   无模型时只保留确定事实
```

**为什么证据采集在 client 侧**：server 是常驻进程，其工作目录不是用户的仓库；
只有 client 由 host 在仓库 cwd 下启动。这也让 server 完全不接触文件系统。

**三级后端的意义**：第 1 级是性能与深度优化路径；第 2 级保证任何人 `pip install`
后就能复现，不需要编译 Isvik；第 3 级不是凑数的兜底，而是「宁缺毋造」原则的
兜底体现——没有模型时诚实留空，而不是编一段读起来通顺的假日志。

**三级之外没有第四级。** 本 skill 不含任何云端推理路径。

---

## 快速开始

### 前置

- Windows x64 + 英特尔 Core / Core Ultra（有 iGPU 或 NPU 更佳）
- 首次运行自动创建 venv 并下载模型（约 0.9 GiB）

### 使用

```powershell
# 记录当前未提交变更所对应的决策
scripts\run.ps1 "改用 opaque handle 表示 Backend 资源"

# 带上实测数据与被否方案（推荐用法）
scripts\run.ps1 "接入编译缓存" `
    --test-log build\test.txt `
    --rejected "每次重新编译|冷启动 IR 编译占首次推理绝大部分耗时" `
    --rejected "只缓存到内存|进程退出即失效，解决不了冷启动"

# 整理最近 3 个提交
scripts\run.ps1 "错误模型统一重构" --commits 3

# 先预览不落盘
scripts\run.ps1 "接入 NPU" --dry-run

# 查看可用后端与设备
scripts\run.ps1 --doctor
```

完整参数见 [SKILL.md](./SKILL.md)。

### 输出

```
已追加: DEVLOG.md  条目: ADR-0042
后端: isvik  设备: GPU.0  模型: Qwen2.5-Coder-1.5B-Instruct-int4-ov
耗时: 6.4s   未验证字段: 1 (Pitfalls)
```

---

## 模型选择

默认 `OpenVINO/Qwen2.5-Coder-1.5B-Instruct-int4-ov`。

选 1.5B 而非 7B 是**硬件约束的结果，不是妥协**：

| 模型 | INT4 权重 | iGPU 单次分配上限 4 GiB | 实际落到的设备 |
| --- | --- | --- | --- |
| Coder-7B-int4 | 4.17 GiB | ❌ 超限 | CPU（慢数倍） |
| **Coder-1.5B-int4** | **0.85 GiB** | ✅ 通过 | **iGPU / NPU** |

Coder 系列专门训练过代码理解，配合「结构硬编码 + 每字段独立小请求」的
提问策略，1.5B 足以胜任受约束的证据抽取任务。

`--model 7b` 可切到质量优先档，但大概率回落 CPU。

### 关于 NPU

默认设备顺序是 `iGPU → CPU`，**NPU 有意不在默认顺序里**：NPU 上跑 LLM 需要
静态形状的专门导出，通用 `*-int4-ov` IR 直接指到 NPU 大概率编译失败。

要实测 NPU 请显式指定：

```powershell
$env:LOCAL_DEVLOG_DEVICE = 'NPU'
scripts\run.ps1 --doctor
```

---

## 与 Isvik 的关系

[Isvik](https://github.com/AbyssGG/Isvik) 是 100% Nim 编写、通过
[Resonance](https://github.com/AbyssGG/Resonance) 直连 OpenVINO C API 的本地
推理运行时，提供 OpenAI / Anthropic 双协议兼容的 HTTP 服务。

本 skill 检测到 `127.0.0.1:7317` 可用时优先走它，并**跳过模型下载**——Isvik
有自己的模型库（`isvik -import` 管理），重复下载 0.9 GiB 纯属浪费。

Isvik 不在时自动走 `openvino-genai`，功能完全一致。**评委复现不需要编译 Isvik。**

启用带鉴权的 Isvik：

```powershell
$env:ISVIK_API_KEY = 'isvk_...'   # 可选
$env:ISVIK_PORT = '7317'          # 可选，默认 7317
```

---

## 环境变量

| 变量 | 作用 |
| --- | --- |
| `LOCAL_DEVLOG_BACKEND` | 强制后端：`isvik` / `genai` / `rule` |
| `LOCAL_DEVLOG_DEVICE` | 强制设备：`CPU` / `GPU` / `GPU.0` / `NPU` |
| `ISVIK_BASE_URL` / `ISVIK_PORT` / `ISVIK_API_KEY` | Isvik 连接配置 |

---

## 测试

```powershell
# 完整测试（含真实推理）
.\tests\test.ps1

# 只跑静态检查与单元测试，不下载模型
.\tests\test.ps1 -Quick

# 单元测试（任何平台，不需要 OpenVINO / 模型 / Intel 硬件）
python tests\test_units.py
```

单元测试共 37 项，重点覆盖三条正确性底线：反幻觉守卫必须剔除伪造数字且不误伤
真实数字、无证据字段必须诚实留空、证据锚点必须来自真实解析结果。

此外有一组测试机械检查 `scripts/` 下不存在任何云端推理端点，**并且包含负例
验证**——先构造一个已知违规的假输入证明扫描器真的会报错，否则一个永远返回
「通过」的扫描器也能让测试全绿。

---

## 目录结构

```
local-devlog/
├── SKILL.md              # 路由规范 + 使用手册
├── info.json             # 运行时配置（venv / 内存 / 模型）
├── meta.json             # 商店元数据
├── requirements.txt      # Python 依赖
├── README.md
├── scripts/
│   ├── run.ps1           # 唯一入口，固定名不可改
│   ├── install-env.ps1   # uv 建 venv + 装依赖
│   ├── client.py         # 证据采集、渲染、落盘
│   ├── server.py         # 模型常驻服务
│   ├── backends.py       # 三级后端
│   ├── evidence.py       # git / 测试日志证据采集
│   ├── devlog_engine.py  # ADR 抽取与渲染、反幻觉守卫
│   └── common.py         # 路径、日志、管道协议
├── assets/
│   └── adr_template.md   # 输出格式说明与样例
└── tests/
    ├── test.ps1          # 真机端到端测试
    └── test_units.py     # 跨平台单元测试
```

---

## 隐私

devlog 的输入是一个团队最敏感的东西：未发布的代码、内部架构决策、失败的尝试、
性能数据。这类内容在很多组织里**绝对不允许**发往云端。

因此本 skill 的推理全程在 `localhost` 完成，无模型时降级为规则模板，
**绝不改走云端 API**。

---

## 许可

Apache-2.0
