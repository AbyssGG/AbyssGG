# Production AI Skills 大赛——从「智能体工作流」迈向「生产力 Skills」

> 来源：[ModelScope 活动 289 · 比赛介绍](https://www.modelscope.cn/events/289/%E6%AF%94%E8%B5%9B%E4%BB%8B%E7%BB%8D)（内容经改写整理以符合授权要求）

## 基本信息

| 项目 | 内容 |
|---|---|
| 主办方 | Intel、OpenVINO、魔搭社区（ModelScope） |
| 赛事类型 | 应用开发赛（competition） |
| 奖池 | 10000 元奖金 + 10000 元礼品 |
| 报名开始 | 2026-07-07（北京时间） |
| 报名截止 | 2026-08-31 23:59（北京时间） |
| 参赛形式 | 个人参赛（组队人数上限 1） |
| 已报名人数 | 141（抓取时数据） |
| 作品提交表单 | https://alidocs.dingtalk.com/notable/share/form/v01Q35O85pPVW83Al9V_dv19yqvsgs3oebp3pcjys_1qX0QQ0?source=link |

## 一、承前启后：第三期为「生产力」而来

Agent Skills 征文大赛此前已办两期，见证端侧 AI 从概念走向落地：

- **第一期**（3.22–4.30，OpenClaw Skills 挑战赛）：聚焦生成式 AI 工具（VLM / ASR / TTS / 图像生成）的本地封装，完成从 0 到 1 的「单点能力封装」。
- **第二期**（5.1–6.30，Agent Skills 大赛）：升级为本地可用的 Skill 封装，首次要求基于本地小模型搭建智能体应用，推动构建完整 Agentic 工作流。
- **第三期（本期）**：目标锁定「生产力」，鼓励面向生产力级 AI Agent 工具（Qoder、WorkBuddy、TRAE Work 等）集成本地 Skill，让端侧智能嵌入日常工作流，产出可复用、可商用、有真实价值的技能资产。

## 二、活动背景：Agentic AI 与 Hybrid AI

AI 正从对话机器人转向能理解意图、自主规划、调用工具并产生实际结果的「智能体」（Agentic AI）。随着端侧算力增长，Hybrid AI 架构成为趋势：云端负责超大规模逻辑，高频响应、隐私敏感与强个性化的任务下沉到 AI PC。

Intel 通过 CPU + GPU + NPU 异构算力整合为 Agentic AI 落地提供硬件基础，魔搭社区提供丰富模型储备。本期希望把这些能力沉淀为生产力：把逻辑复杂但体积精炼（≤ 35B）的模型部署到本地，降低推理成本、保证隐私数据不出机，并让 Skill 直接服务真实生产力场景。

## 三、征文主题与硬性约束

### 核心主题
面向生产力级 AI Agent 工具（Qoder、WorkBuddy、TRAE Work 等）集成一项本地 AI 工具调用（OCR / ASR / TTS / RAG / 数据分析等），解决真实生产力场景需求，产出可复用、可商用的 Agent Skill。

### 技术约束
- **部署方式**：推荐 Client/Server 的模型服务部署方式，实现 Skill 随时调用。
- **运行环境**：Skill 涉及的 AI 模型必须支持纯本地运行（localhost）。
- **工具适配**：Skill 需适配生产力级 AI Agent 工具（Qoder、WorkBuddy、TRAE Work 等），能被其作为技能稳定调用。
- **推理框架**：推荐使用 OpenVINO™ 及生态工具（如 Optimum-intel）构建本地 AI 工具，释放 GPU / NPU 潜力。
- **验证基准**：以上述生产力级 Agent 工具作为「Skill 能否被 Agent 大脑稳定调用」的基准测试环境。
- **官方指南**：AI PC local skill 参考标准 <https://github.com/openvino-dev-samples/local-ai-skill-authoring>

## 四、推荐方向与场景参考

| 推荐方向 | 生产力场景示例 | Agentic / Hybrid 价值 |
|---|---|---|
| 办公提效 | 本地会议纪要自动提取、PPT 一键风格改稿、Excel 复杂公式智能填充 | 零延迟响应，企业内部敏感会议数据不外泄 |
| 开发辅助 | 本地代码 Review、Git Commit 自动生成、API 文档反向生成（可在 Qoder 中执行） | 离线高效编程，保护核心算法 |
| 创作创意 | 短视频脚本生成、公众号/小红书文案适配、本地图文自动排版 | 端云协同：云端搜集素材，本地用 35B 模型深度二次创作 |
| 知识管理 | 个人 PDF / 笔记库 RAG、研报摘要提取、本地私人知识库问答 | 构建「永不掉线」且完全私有的数字第二大脑 |
| 数据分析 | CSV 自然语言查询、本地数据可视化、系统日志异常自动归因 | 直接读取本地大容量数据集，规避云端流量成本 |

另有二维码资源：Intel AI PC 专区（开发工具、技术文档、实战案例）与官方比赛群（赛事同步、技术答疑）。

## 五、参赛流程（四步）

1. **编写本地 AI 工具**：推荐用 OpenVINO 做量化与异构加速优化，调动 GPU / NPU。
2. **生成并验证 Skill**：按 [魔搭 Skills 中心](https://www.modelscope.cn/skills) 规范封装技能，并在生产力工具（Qoder、WorkBuddy、TRAE Work 等）环境下完成指令测试。
3. **发布作品包**：在 [魔搭 Skills 中心](https://www.modelscope.cn/skills) 发布，添加「AI PC」自定义标签；作品需含代码、文档与测试用例。
4. **提交技术文章**：在 [魔搭研习社](https://www.modelscope.cn/learn) 发表文章，记录实践路径、在生产力级 Agent 工具中跑通 Skill 的完整截图/录屏、优化心得与 Hybrid AI 思考，并添加「Intel AI PC」专题标签。

## 六、评分标准（合计 100% + 5 附加分）

| 维度 | 权重 | 说明 |
|---|---|---|
| 场景价值 | 30% | 问题真实性、生产力场景落地深度、用户群体广度 |
| 商用生产力 | 30% | 商用/量产潜力、稳定性与可维护性、能否嵌入真实生产工作流 |
| 工具使用 | 20% | 对 Qoder、WorkBuddy、TRAE Work 等工具的集成质量、OpenVINO/GPU/NPU 优化、工程实现 |
| 文章质量 | 10% | 结构清晰度、可复现性、教学价值 |
| 创新性 | 10% | 思路新颖度、与已有方案的差异化 |
| 传播附加分 | +5 | 将作品截图/流程图/Skill 成果连同研习社文章与 Skill 链接发布至小红书，@OpenVINO中文社区 与 @魔搭ModelScope社区，带话题 #英特尔 #openvino #魔搭 #agentic #skills；截至 8 月 31 日三处累计阅读量超 1000 次可得 5 分 |

## 七、激励

- **实物奖励**：前 50 名完整提交作品可领 OpenVINO / 魔搭社区限量周边。
- **现金大奖**：TOP 10 作品各得 1000 元（含税）。
- **生态推广**：入选《AI PC Skills Collections》，获魔搭与 Intel 官方全渠道流量扶持。
- **合作池入驻**：优秀开发者优先进入「Intel ISV 生态合作伙伴池」，对接后续商业合作与资源。
