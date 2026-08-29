# local-devlog — 开发规格与参考实现

本分支为 **ModelScope Production AI Skills 大赛**（截止 2026-08-31 23:59）的开发资料。
它是一个独立的 orphan 分支，与本仓库 main 分支无任何关联。

## 你要下载的文件

**[local-devlog_BUILD_SPEC.md](./local-devlog_BUILD_SPEC.md)** — 开发规格书（AI 可自主执行版）

这一份是自包含的：把它整份交给 AI，AI 即可从零构建整个 skill，全程无需你回答任何选择题。
25 项技术决策已在文档 § 2 全部预先定好。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| `local-devlog_BUILD_SPEC.md` | **主文档**。交给 AI 直接开工用。含精确协议契约、8 个施工阶段、每阶段自测命令、10 步排查清单 |
| `local-devlog_AI_MASTER_PROMPT.md` | 流程版规范。保留了「作者判断权」，适合跑通之后写文章阶段使用 |
| `ARTICLE-OUTLINE.md` | 研习社文章大纲（12 节，对齐评分维度）+ 9 张截图清单 + 8 步提交清单 |
| `ModelScope-289-比赛介绍.md` | 赛事要求整理 |
| `local-devlog-reference/` | 一份参考实现草稿（17 文件）。**不是权威**，AI 卡住时可参照，但须按 BUILD_SPEC 校验 |

## 快速开始

把 `local-devlog_BUILD_SPEC.md` 交给 AI，然后发这段：

```text
读完 local-devlog_BUILD_SPEC.md 全文，然后按 § 6 从 STAGE 1 开始施工。
规则：
- 一次只做一个 STAGE，做完立刻执行该 STAGE 的自测命令并把真实输出贴给我
- 自测不通过就修到通过，不要进入下一个 STAGE
- § 2 的决策已经定了，不要问我选哪个
- 无法在当前环境验证的项，标注 NOT TESTED IN CURRENT ENVIRONMENT，不要声称通过
先输出你对本文档硬约束的理解清单（§ 1 逐条），然后开始 STAGE 1。
```

## 环境提醒

第一个坑大概率是 PowerShell 执行策略：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

只想验证协议链路、不想下载 0.9 GiB 模型时：

```powershell
$env:LOCAL_DEVLOG_BACKEND = 'rule'
```

## 参考实现的已知状态

`local-devlog-reference/` 已通过：37 项单元测试、ruff 静态检查、静态合规 13 项、
规则模式端到端。

**未验证**（沙箱为 Linux 无法执行）：PowerShell 脚本、Windows 命名管道、
openvino-genai 实际推理、Isvik 实际推理、模型下载、iGPU/NPU 设备路径。

`meta.json` 的 `icon` 与 `author` 为占位值，须替换。
