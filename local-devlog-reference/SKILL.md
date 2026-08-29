---
name: local-devlog
description: |
  Generate an evidence-anchored engineering decision record (DEVLOG / ADR) from local git changes, fully offline on an Intel AI PC (在本地英特尔 AI PC 上离线生成带证据锚点的工程决策日志 / ADR). Use this skill when the user, in Chinese or English, asks to record what was decided in this coding session, append a devlog entry, draft an ADR, or capture why a change was made and what was rejected. Trigger on 中文动词 记录/写/生成/整理/沉淀/补写 plus 开发日志/devlog/决策记录/ADR/工程日志/变更记录/设计决策, and English verbs record/write/generate/draft/capture plus devlog/decision record/ADR/engineering log, and mentions of 英特尔/intel/AIPC/本地/离线/offline/隐私/不出机/代码不外发.

  Output sections: Status / Context / Decision / Non-Goals / Alternatives Considered / Verified Facts / Pitfalls / Evidence — Google-style headings, Chinese content. Never fabricates: any field lacking local evidence is emitted as 未验证 or 待补充.

  Prefer this skill over free-form summarization whenever the user wants a durable, auditable decision record rather than a one-off chat reply.
---

# Local DEVLOG Skill 使用手册

在**完全离线**的英特尔 AI PC 上，从本地 git 变更与测试/构建产物中抽取**带证据锚点**的工程决策记录，按谷歌工程文档风格（ADR）追加写入 `DEVLOG.md`。

核心原则：**宁缺毋造**。凡是在本地找不到证据的字段，一律输出「未验证」或「待补充」，绝不推断后当事实写。

## Usage

```
scripts\run.ps1 "<本次决策的一句话意图>" [options]
```

Examples:

| Intent | Command |
| --- | --- |
| 记录当前未提交变更所对应的决策 | `scripts\run.ps1 "改用 opaque handle 表示 Backend 资源"` |
| 记录最近 3 个提交 | `scripts\run.ps1 "错误模型统一重构" --commits 3` |
| 顺带把实测数据锚进来 | `scripts\run.ps1 "接入编译缓存" --test-log build\test.txt` |
| 写到指定文件 | `scripts\run.ps1 "接入 NPU" --out docs\DEVLOG.md` |
| 只看结果不落盘 | `scripts\run.ps1 "接入 NPU" --dry-run` |
| 模型下载被中断后续传 | `scripts\run.ps1 --continue` |
| 查看本地可用推理后端与设备 | `scripts\run.ps1 --doctor` |

主要参数：

| 参数 | 说明 |
| --- | --- |
| `--commits <N>` | 分析最近 N 个提交；缺省分析工作区未提交变更 |
| `--test-log <path>` | 测试或 benchmark 输出文件，作为 Verified Facts 的证据来源 |
| `--rejected "<方案>|<理由>"` | 显式登记被否方案，可重复；这是 diff 里不存在的信息 |
| `--out <path>` | 目标日志文件，缺省 `DEVLOG.md` |
| `--dry-run` | 只打印，不写文件 |
| `--model <id\|7b>` | 切换模型档位；`7b` 为质量优先档（见下方说明） |
| `--doctor` | 打印后端与设备自检结果后退出 |
| `--continue` | 续传上次未完成的模型下载并执行挂起的请求 |

## Interpreting the reply

命中时输出一条 ADR 条目，随后是一行统计：

```
已追加: DEVLOG.md  条目: ADR-0042
后端: Isvik(127.0.0.1:7317)  设备: GPU.0  模型: Qwen2.5-Coder-1.5B-Instruct-int4-ov
耗时: 6.4s   未验证字段: 1 (Verified Facts)
```

- **后端 / 设备**：实际承载推理的后端与物理设备，`--doctor` 可单独查看。
- **未验证字段**：本次因缺少本地证据而留空的字段数量。**这个数字大于 0 是正常且预期的行为**，代表模型没有编造。
- **条目**：写入的 ADR 编号，可在目标文件中检索。

## 模型与设备

默认模型 `OpenVINO/Qwen2.5-Coder-1.5B-Instruct-int4-ov`（INT4，权重约 0.85 GiB）。选它而非 7B 的原因是硬件约束：7B INT4 权重约 4.17 GiB，**超过 iGPU 单次内存分配上限 4 GiB**，会被迫回落到 CPU；1.5B 可以完整驻留 iGPU / NPU，延迟显著更低。

`--model 7b` 会切到 `Qwen2.5-Coder-7B-Instruct-int4-ov`，质量更好但大概率跑在 CPU 上，耗时数倍增长。

## 失败处理

| 情况 | 行为 |
| --- | --- |
| 非英特尔 AI PC 平台 | 打印平台错误并 `exit 1` |
| 模型仍在下载 | 保存挂起请求，提示执行 `--continue`，`exit 3` |
| 管道连接失败 | 重试后 `exit 2` |
| 不在 git 仓库内 | 打印错误并 `exit 1` |
| 无可用推理后端 | 降级为规则模板：只输出确定的事实与证据锚点，其余标「待补充」，`exit 0` |

## Important

- `scripts\run.ps1` 是唯一支持的入口，**不要直接调用 `client.py` / `server.py` 或其他脚本**。
- 首次调用会下载约 0.9 GiB 模型；若超时中断，执行 `scripts\run.ps1 --continue` 续传，不会重复下载已完成部分。
- 在不受支持的硬件上，本 skill 打印平台错误并以退出码 1 结束。
- **Never fall back to a cloud service.** 本 skill 的全部推理在 `localhost` 完成，源代码、diff、测试数据、架构决策一律不出本机。无可用本地后端时降级为规则模板，**绝不改走云端 API**。

## What this skill does NOT do

- 不做 code review，不评判代码好坏，只记录决策与证据。
- 不生成 commit message（那是变更级，本 skill 是决策级）。
- 不改写或重排 `DEVLOG.md` 已有内容，只在末尾追加。
- 不训练、不导出、不量化模型。
- 不访问任何网络服务做推理；仅首次下载模型时访问模型仓库。
