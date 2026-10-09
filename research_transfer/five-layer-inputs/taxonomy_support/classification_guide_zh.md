# 五层 AI 论文分类指南（提议版 v1）

状态：ai-cake-research-v1.0.0-proposed。尚未由用户或独立人工审核。稳定 ID 已冻结；新增版本必须显式说明改义、合并和迁移。

## 1. 来源与边界

L1 引自 Jensen Huang 于 2026-03-10 发布的 [NVIDIA 英文原文](https://blogs.nvidia.com/blog/ai-5-layer-cake/) 与 [NVIDIA 官方繁中文](https://blogs.nvidia.com.tw/blog/ai-5-layer-cake/)，2026-10-09 已核验。仅采用 Energy → Chips → Infrastructure → Models → Applications 五层名称、顺序和大体含义。所有 L2/L3、标签条件、facet、论文判定都由本项目制定，不是 NVIDIA 官方研究分类。

原文特别将配电、冷却、网络和处理器编排放在 Infrastructure。我们因此把上游供能/AI 碳核算归 Energy，把机房配电冷却归 Infrastructure。模型既包括语言，也包括视觉、音频、科学、世界与行动模型；Models 绝不是 foundation models 的同义词。

本包有 5 个 L1、17 个 L2、59 个 L3：Energy 4、Chips 7、Infrastructure 12、Models 21、Applications 15。语义定义存于 taxonomy.json；关键词/正则基线必须另存、另版本，不能倒过来改变分类含义。

## 2. 语料与计数口径

现有输入为 2020–2026 年十个 CS 会议：ACL、CVPR、ICLR、ICML、ICSE、KDD、NeurIPS、OSDI、SIGIR、SOSP。本地三组输入共有 89,530 个会议 occurrence（ML 57,957；ACL/CVPR 25,380；systems/IR 6,193）。这不是去重后的独立论文数，更不是全球产业或全 CS 论文总数。

已知覆盖限制必须随主表及 Explorer 保留：NeurIPS 2026 的 5,522 项是暂定不完整会前项目；OSDI 2026 有研究轨道/原 ATC 范围变化；CVPR 2026 实际索引 4,042 与公布接收 4,089 不一致；SIGIR 2026 实际记录 233 与页面 234 不一致。SOSP 2020/2022 无届，不能填零。主表不要自动沿用旧标题-only分析的分类字段；应记录这次真正使用的 title/abstract/full_text。

arXiv 已有汇总计数，不代表已经完成 arXiv 论文级采集、去重、摘要取得或本分类。没有原始论文记录就不能补造主表行。能源、芯片在这个会议篮子中稀少，不能解释为对应领域研究不活跃。

推荐主表一行一个 work；另存 occurrence 表，并把简化 occurrences_json 内嵌以便单 CSV Explorer 使用。DOI/arXiv/OpenReview 等可靠标识符优先；仅标准化同标题不足以静默合并。各类按 distinct paper_id 计数，venue/year 按 distinct occurrence_id；两者不得混用。多标签类别相加允许大于论文数，不能做假装互斥的饼图。

## 3. 最小判定流程

1. 先看文本覆盖：有无真实摘要、是否截断、是否只有标题。不能用 venue 代替内容证据。
2. 判断是否明确研究 AI 能源/芯片/系统、AI 模型方法或 AI 应用。纯非 AI CS 保留在主表。
3. 找中心贡献/直接研究对象。把“使用的模型/机器、引用、动机、基线”与“论文新研究的东西”分开。
4. 对照叶子定义与排除条件，可跨层或同层多标。每个标签要有独立可定位证据；没有最低标签数或强制主类。
5. 从有证据 L3 计算同一路径的 L2/L1 祖先闭包。应用依赖下层并不意味着论文贡献横跨全部五层。
6. 记录独立 facets；不因为 safety/evaluation 词而机械创建叶子。
7. 输出方法、版本、输入、字面命中跨度、证据、状态与覆盖；自动初轮永远清楚显示候选性质。

四种 classification_status：
- classified：按本次方法至少分配一个叶子；是否已审核另看 label/review 状态。
- outside_scope：有足够内容明确中心研究不在本 AI 范围；类别空。
- insufficient_evidence：关键内容缺失/歧义，或规则没有能力判；类别空。不能当非 AI。
- taxonomy_gap：AI 相关性明确，但现有树无法表达；记录待扩展主题，不硬塞最近类。

这四项是主表状态，不是“第六层”。若知道 L1 但没有足够 L3 证据，把粗粒度判断记 candidate_topics_json，正式 category_ids 仍可为空。若已有一个确定叶子，另一个仅疑似主题，保留确定叶子并把后者放 warnings/候选，不把整行强制变 insufficient_evidence。

## 4. 关键边界

- Energy 是 AI 所需的能源/碳核算；AI 预测电网、天气或农业属于 A.03.03。energy-based model 的 energy 是数学量，不能匹配 Energy。
- Chips 要有物理硬件/架构/设计产物或直接硬件对象。只在 GPU 上跑、降低 GPU memory 或做量化，不够。
- 芯片 SRAM/HBM 器件归 C.02.01；读写 HBM/SRAM 的 kernel 归 I.02.01；KV 分页服务归 I.02.03；Agent 经验/情节记忆归 A.01.02；RAG 模型记忆归 M.04.03。
- 泛用 attention/Transformer 不等于 foundation。model_scope=foundation 要有广泛预训练与跨任务复用证据；没有则 unknown 或 task_specialized/general_method。
- 预训练过程、预训练数据/目标的研究与“使用 pretrained model”不同。后者不能机械记为预训练贡献。
- 后训练需要参数/模型适配或偏好/RL 训练证据；Reflexion 的文本反思记忆不因标题含 reinforcement learning 就变成 M.03.02。
- RL 多智能体学习算法归 M.02.03；LLM 多 Agent 系统组织归 A.01.04。传统 agent 一词不证明是 LLM Agent。
- 学会工具调用的模型归 M.04.04；工具连接器/执行器归 A.01.03；完整控制循环归 A.01.01；AgentBench 等交互基准归 A.01.05。通用 Agent 不必虚构行业域。
- 测试时参数适配通常 M.02.03/M.03.01（视实质）且 stage=test_time_adaptation；增加搜索计算以提升答案正确率归 M.04.02；吞吐/时延/批处理服务归 I.02.03。
- 领域数据作为通用方法实验不能自动赋 Applications；领域任务约束、工作流/用户成果是中心贡献才赋应用。领域专用新模型与应用成果同时成立时可跨层。
- 评测资源/方法为主要贡献才能赋 M.05.01/A.01.05；每篇论文有实验并不都是 benchmark 研究。普通准确率/时延结果可放 evaluation facet。
- 对齐偏好不自动代表危害、安全或隐私研究；DPO 不因 alignment 一词自动得到 M.05.03。

## 5. 自动分类器与证据契约

首轮主表应明确写 classification_label_status=candidate、review_status=automated、classification_method=rules_candidate_v1 或实际模型方法。rule_id 命中、基于 title 或 abstract、原文跨度必须可回查。语义复读样例的 review_status=ai_adjudicated，仍不是 human_reviewed，也不是金标准。

纯 lexical rule 命中只证明字词出现，不能冒充已判定中心贡献。建议 evidence_strength=needs_review，basis=lexical_rule_candidate；模型/人工读完语义后可记 explicit 或 supported_inference。没有标注样本的校准与验证就不要生成 0.87 等“置信度”。任何基线未命中默认 no_rule_match/insufficient_evidence，而不是 outside_scope。

每条 category_evidence_json 至少包含：category_id、source_field、source_url、span_start、span_end、quote、assignment_role、rationale_zh、evidence_strength、basis、rule_ids、review_status。原文 quote 与对应字段的 [start,end) 必须一致。跨度按 Unicode code point 计数；JavaScript 用 Array.from(text) 切片，不能对含非 BMP 字符直接按 UTF-16 单元切。缺摘要就不能伪装 title_abstract。

field_provenance_json 对每个可变元数据字段保留 source_url / source_record_id / retrieved_at / status / transform。摘要缺失与无关键词、无安全实验等不是同一回事。JSON null 表示未查/未知，[] 表示查过而当前无值；标量未知留空。CSV 用 RFC4180 正确转义 JSON、逗号和换行，禁止手工逗号拼接。

建议分类提示要求输出简洁依据而非思维过程：
“使用冻结 taxonomy；只根据给定 title/abstract/fulltext 及其来源判断；先检查覆盖与 AI 范围，再找中心贡献；逐项给原文字面证据和短理由；执行所有排除条件；允许多标签/弃权；只补路径祖先；输出结构化记录；自动结果是候选，不提供未经校准概率。”

最小质量流程：先运行本包 adversarial_tests.json；分层抽样覆盖 venue/year、title-only 与 abstract、各层、未分类和多标签；由独立审核者标注；报告标签精确率/召回率、弃权率和分层误差。18 个示例只能帮助对齐边界，不能当总体准确率。不得把 24 个合成测试通过率称为真实论文准确率。

## 6. Facets（与五层正交）

method：算法/机制，例如 diffusion、RL、RAG、PEFT；task：问题，例如推理、检索、软件修复；stage：pretraining/posttraining/inference/test_time_adaptation/agent_assembly 等；evaluation：任务完成、准确率、时延、能耗、理论等；safety：安全、隐私、公平、鲁棒等。另有 contribution_type、domain、model_modality、model_scope、agent_form。所有词表见 taxonomy.json。

不同 facet 可重叠；叶子不能替代它们。尤其 Agent+Memory+Evaluation 可以有 A 层路径与多个 facet；pretraining/posttraining/reasoning 不会因压到五层而消失。安全 facet 未提及不代表安全；没有证据时不要猜具体模型家族。

## 7. 已有论文的示范判定

以下 17 例均读取本地已有标题与摘要；第 18 例真实缺摘要。JSON/CSV 保存原摘要、来源 URL、原文件/行、证据原文及跨度。判断是 AI 示范复核，用户/独立人工仍可更正。

### EX01 · LLMCarbon: Modeling the End-to-End Carbon Footprint of Large Language Models
ICLR 2024 · [论文](https://openreview.net/forum?id=aIok3ZD9to)
判定：能源 / AI 能源与碳管理 / 能耗与生命周期碳核算
不是新 AI 模型或新 GPU；测量工具名称含 Modeling 不决定层。
证据摘要：模型在此指碳核算工具；中心目标是 AI 生命周期碳。

### EX02 · Winning the L2RPN Challenge: Power Grid Management via Semi-Markov Afterstate Actor-Critic
ICLR 2021 · [论文](https://openreview.net/forum?id=LmUJqB1Cz8)
判定：应用 / 科学与专业领域应用 / 能源、环境与农业应用；模型 / 学习与预训练 / 学习算法与优化
电网是 AI 的使用对象；不是给 AI 供能。传统 RL agent 不等于 LLM harness。
证据摘要：电网管理是 AI 应用目标。；提出算法来解决状态/行动空间挑战，有方法层贡献。

### EX03 · Data-Driven Offline Optimization for Architecting Hardware Accelerators
ICLR 2022 · [论文](https://openreview.net/forum?id=GsH-K1VIyy)
判定：应用 / 科学与专业领域应用 / 科学与工程应用；模型 / 学习与预训练 / 学习算法与优化
摘要未明确目标是 AI 芯片。不能只因 accelerator 一词加 Chips；补全文确认 AI 加速器研究对象后可加 C.01.04。
证据摘要：用学习方法做硬件工程设计。；离线学习优化方法也是核心贡献。

### EX04 · FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness
NeurIPS 2022 · [论文](https://papers.nips.cc/paper_files/paper/2022/hash/67d57c32e20fd0a7a302cb81d36e40d5-Abstract-Conference.html)
判定：基础设施 / AI 执行系统 / 内核、编译器与运行时
HBM、SRAM、GPU 是执行平台；没有提出芯片，也不能把吞吐提升自动当能源研究。
证据摘要：中心贡献是既有 GPU 上的 attention 执行及 IO 优化。

### EX05 · Language Models are Few-Shot Learners
NeurIPS 2020 · [论文](https://papers.nips.cc/paper_files/paper/2020/hash/1457c0d6bfcb4967418bfb8ac142f64a-Abstract.html)
判定：模型 / 模型家族与表示 / 语言模型与基础模型；模型 / 学习与预训练 / 预训练目标与扩展规律；模型 / 推理与决策方法 / 提示与上下文学习
规模大或训练用 GPU 本身不能证明分布式系统或芯片贡献。
证据摘要：新通用语言模型产物。；主要研究规模与通用能力。；无梯度的上下文示例使用是中心结果。

### EX06 · Direct Preference Optimization: Your Language Model is Secretly a Reward Model
NeurIPS 2023 · [论文](https://papers.nips.cc/paper_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7-Abstract-Conference.html)
判定：模型 / 后训练与适配 / 偏好对齐与 RL 后训练
对齐偏好不自动等于具体安全研究；算法更轻量不自动变成系统论文。
证据摘要：以偏好数据直接优化已有语言模型。

### EX07 · LoRA: Low-Rank Adaptation of Large Language Models
ICLR 2022 · [论文](https://openreview.net/forum?id=nZeVKeeFYf9)
判定：模型 / 后训练与适配 / 监督与参数高效适配
GPU memory requirement 是结果；改变可训练参数不是芯片或 serving 系统。
证据摘要：参数高效适配是主要方法。

### EX08 · Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
NeurIPS 2020 · [论文](https://papers.nips.cc/paper_files/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html)
判定：模型 / 推理与决策方法 / 检索、知识落地与模型记忆
使用向量索引不表示数据库引擎贡献；外部知识记忆不是 Agent 情节记忆；通用 QA 验证不等于办公应用。
证据摘要：检索与生成结合的模型方法。

### EX09 · Toolformer: Language Models Can Teach Themselves to Use Tools
NeurIPS 2023 · [论文](https://papers.nips.cc/paper_files/paper/2023/hash/d842425e4bf79ba039352da0f658a906-Abstract-Conference.html)
判定：模型 / 推理与决策方法 / 学习式工具使用与 Agent 策略
调用多个 API 是模型能力的训练目标；摘要没有独立工具连接平台贡献。
证据摘要：工具决策能力通过训练获得。

### EX10 · ReAct: Synergizing Reasoning and Acting in Language Models
ICLR 2023 · [论文](https://openreview.net/forum?id=WE_vluYUL-X)
判定：模型 / 推理与决策方法 / 推理、搜索与测试时计算；应用 / 通用 Agent 系统 / Agent 编排与 Harness；模型 / 推理与决策方法 / 提示与上下文学习
能跨 Models 与 Applications；没有权重 RL 证据不能归 RL 后训练。
证据摘要：推理与行动耦合的方法贡献。；明确的计划/行动/异常处理交互循环。；少样本上下文实现也是方法的重要证据。

### EX11 · ReAct: Out-of-distribution Detection With Rectified Activations
NeurIPS 2021 · [论文](https://papers.nips.cc/paper_files/paper/2021/hash/01894d6f048493d2cacde3c579c315a3-Abstract.html)
判定：模型 / 模型评测与可靠性 / 鲁棒性、不确定性与分布偏移
与 2023 年同名 ReAct 不同。只靠简称会误标 Agent。
证据摘要：此 ReAct 是 OOD 检测方法。

### EX12 · Reflexion: language agents with verbal reinforcement learning
NeurIPS 2023 · [论文](https://papers.nips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html)
判定：应用 / 通用 Agent 系统 / Agent 编排与 Harness；应用 / 通用 Agent 系统 / Agent 持久记忆与状态
标题有 reinforcement learning，但摘要明确不更新权重；情节记忆不是模型 checkpoint。
证据摘要：围绕已有模型的反馈工作流。；Agent 持久情节记忆是中心设计。

### EX13 · AgentBench: Evaluating LLMs as Agents
ICLR 2024 · [论文](https://openreview.net/forum?id=zAdUB0aCTQ)
判定：应用 / 通用 Agent 系统 / Agent 评测与环境
评测现有 LLM 或建议提高训练质量，不等于提出新模型或后训练算法。
证据摘要：以交互环境测试完整 Agent 的行动成果。

### EX14 · SWE-bench: Can Language Models Resolve Real-world Github Issues?
ICLR 2024 · [论文](https://openreview.net/forum?id=VTF8yNQM66)
判定：应用 / 数字工作与交互应用 / 软件工程应用
难题需要 reasoning 不等于提出推理算法；测量应用级代码修复，不自动等于通用模型基准。
证据摘要：软件工程应用任务及评测是核心对象。

### EX15 · Denoising Diffusion Probabilistic Models
NeurIPS 2020 · [论文](https://papers.nips.cc/paper_files/paper/2020/hash/4c5bcfec8584af0d967f1ab10179ca4b-Abstract.html)
判定：模型 / 模型家族与表示 / 视觉、图像与视频模型；模型 / 学习与预训练 / 学习算法与优化
热力学启发或 energy 词不属于 Energy；图像生成模型不是创作界面/工作流。
证据摘要：图像生成模型为主要研究对象。；提出模型学习目标；摘要没有证明这是可复用模型的预训练。

### EX16 · Reshape and Adapt for Output Quantization (RAOQ): Quantization-aware Training for In-memory Computing Systems
ICML 2024 · [论文](https://proceedings.mlr.press/v235/zhang24i.html)
判定：模型 / 后训练与适配 / 压缩、量化、剪枝与蒸馏
研究受硬件约束，但摘要中的产物是量化适配、权重/激活重塑；没有新的 IMC 器件/阵列。
证据摘要：改变训练/模型以适配硬件量化误差。

### EX17 · DotHash: Estimating Set Similarity Metrics for Link Prediction and Document Deduplication
KDD 2023 · [论文](https://dl.acm.org/doi/10.1145/3580305.3599314)
判定：outside_scope
现有摘要的中心产物是集合交集/相似度无偏估计器，没有 AI 学习/推理或 AI 专用系统贡献。基于这份摘要判为 outside_scope；全文如揭示新的 AI 中心贡献可复核。

### EX18 · Real or Not Real, that is the Question
ICLR 2020 · [论文](https://openreview.net/forum?id=B1lPaCNtPB)
判定：insufficient_evidence
本地记录缺摘要，标题没有足够具体的方法/对象。ICLR venue 不能替代内容证据。

## 8. Explorer 接入与展示

1. taxonomy.json 为树与文案唯一真源；category_ids_l3_json 为叶子，调用参考代码补祖先/路径。
2. 默认展示清楚标注的“自动候选”口径，可切已审核；按论文数与 occurrence 数分别统计。
3. 左侧保留五层树；另给 classification_status、venue/year、来源/摘要覆盖、method/task/stage/evaluation/safety 独立筛选。
4. 未分类/非 AI 数据仍可浏览；不要从总分母悄悄删除。
5. 每篇卡片显示 title、abstract、路径、证据及来源、判定方法、review 状态。多标签卡片只显示一次。
6. 年度趋势显示采集覆盖、2026 暂定/结构断点；Energy/Chips 为零时提示会议篮子覆盖局限。
7. CSV 导入时验证 JSON、ID、路径、证据跨度和 null 语义；导出保持字段原样，不将 JSON 数组 flatten 成难以解析字符串。

## 9. 全部 L3 定义

以下仅列叶子，完整 L1/L2 定义在 taxonomy.json 与 taxonomy_nodes.csv。

### Energy · 能源

#### E.01.01 发电与电网容量 (Power generation and grid capacity)
面向 AI 计算需求的电力来源及电网容量。
纳入：AI 数据中心负荷驱动的能源供给、选址电力约束。
排除：AI 用于预测普通电网负荷。
边界：给 AI 集群规划电网扩容→此类；用 AI 管电网→A.03.03。

#### E.01.02 储能与供能调度 (Storage and supply dispatch)
保障 AI 负载供能的储能、供电组合及能源调度。
纳入：AI 负荷相关储能、可再生能源配比、供能合同研究。
排除：普通储能控制应用；UPS 硬件设施设计。
边界：研究储能如何承接 AI 电力波动→此类。

#### E.02.01 能耗与生命周期碳核算 (Energy and lifecycle carbon accounting)
以 AI 能源需求、运营/隐含碳为中心的测量建模。
纳入：训练、推理、设备生命周期碳/能量测量和核算。
排除：只顺带报告功耗；能源词用于概率模型。
边界：LLMCarbon→此类；energy-based model 不因此属于 Energy。

#### E.02.02 能源灵活性与碳感知负载 (Energy flexibility and carbon-aware demand)
以电力/碳约束为主要优化目标的 AI 需求管理。
纳入：时空移负荷、碳感知 AI 任务调度、供需协调。
排除：只优化时延或利用率；通用电网 RL。
边界：碳感知训练调度若同时创新调度系统，可加 I.02.04。

### Chips · 芯片

#### C.01.01 GPU 与张量处理器架构 (GPU and tensor processor architectures)
用于 AI 的 GPU/张量处理物理计算架构。
纳入：执行单元、指令/数据通路硬件、处理器微架构。
排除：使用 CUDA/GPU 或优化软件内核。
边界：新增张量硬件单元可归此；FlashAttention 不归此。

#### C.01.02 专用数字加速器 (Specialized digital accelerators)
针对 AI 工作负载的 ASIC/FPGA 等硬件架构。
纳入：推理/训练加速器、稀疏硬件、专用数据流。
排除：仅进行模型量化或 FPGA 上运行现成设计。
边界：新加速器电路/架构方案须为主要产出。

#### C.01.03 新型与存内计算硬件 (Emerging and in-memory compute hardware)
模拟、光子、神经形态、存内计算等 AI 硬件本体。
纳入：器件、阵列和硬件运算架构的提出与分析。
排除：仅适配已有模拟硬件的模型训练；只用脉冲网络。
边界：RAOQ 只改量化训练，不能仅凭 IMC 词归此。

#### C.01.04 AI 硬件设计空间与协同设计 (AI hardware design-space and co-design)
直接设计 AI 芯片架构参数/硬件方案的优化方法。
纳入：硬件设计空间探索、软硬协同产出新硬件方案。
排除：只对固定 GPU 选择批量、kernel、模型大小。
边界：PRIME 若证明设计对象是 AI 加速器，归此；摘要未说明 AI 硬件对象则待补证。

#### C.02.01 存储器件与硬件层次 (Memory devices and hierarchies)
AI 芯片的 SRAM/HBM/存储器件及硬件组织。
纳入：存储容量/带宽硬件设计、内存芯片架构。
排除：KV cache 算法、软件分页。
边界：新 HBM 控制器架构→此类；PagedAttention→I.02.03。

#### C.02.02 片上与封装互连 (On-chip and package interconnects)
AI 芯片内部及封装级硬件互连。
纳入：NoC、die-to-die、电/光芯片互连硬件。
排除：机架交换网、分布式通信软件。
边界：片上路由结构→此类；集群 all-reduce 软件→I.02.02。

#### C.02.03 封装与 Chiplet 集成 (Packaging and chiplet integration)
AI 芯片物理封装、异构集成与硬件系统构成。
纳入：2.5D/3D 封装、chiplet、AI 芯片热/供电协同设计。
排除：机房冷却；只报告器件制造碳。
边界：芯片封装散热→此类；数据中心液冷→I.01.01。

### Infrastructure · 基础设施

#### I.01.01 设施配电与冷却 (Facility power delivery and cooling)
AI 数据中心内部电力输送、冷却、设施设计。
纳入：机房供配电、液冷、热管理、建设/机架设施。
排除：发电供应；芯片内部热设计。
边界：NVIDIA 原文将 power delivery 与 cooling 列入 Infrastructure。

#### I.01.02 数据中心与集群网络 (Datacenter and cluster networks)
连接 AI 服务器/集群的网络基础设施。
纳入：集群拓扑、交换、传输、拥塞控制用于 AI。
排除：芯片 NoC；仅非 AI 数据中心网络。
边界：专门针对分布式训练的集群拥塞方案可归此。

#### I.02.01 内核、编译器与运行时 (Kernels compilers and runtimes)
把 AI 算子映射为高效执行的软件方法。
纳入：IO-aware kernel、算子融合、AI 编译、执行 runtime。
排除：芯片硬件；改变模型学习目标。
边界：FlashAttention→此类，不因 GPU/HBM 而加 Chips。

#### I.02.02 分布式训练系统 (Distributed training systems)
跨设备协作完成模型训练的系统组织。
纳入：并行训练、通信、张量/流水并行、训练状态分片。
排除：仅分布式优化的统计收敛；通用共识协议。
边界：ZeRO 类训练内存分片属于此；优化理论另看 M.02.03/04。

#### I.02.03 推理服务与执行 (Inference serving and execution)
将模型推理作为可用服务的系统技术。
纳入：连续 batching、KV 内存管理、分离式推理、服务 QoS。
排除：test-time reasoning 策略；模型压缩本身。
边界：PagedAttention 可归此；多想几步提升正确率→M.04.02。

#### I.02.04 调度与资源管理 (Scheduling and resource management)
AI 作业和计算资源的分配管理。
纳入：GPU 集群调度、弹性、放置、多租户资源管理。
排除：Agent 任务规划；无 AI 关联的 OS 调度。
边界：调度训练 GPU→此；规划网页任务→A.01.01。

#### I.03.01 AI 数据接入与流水线 (AI data ingestion and pipelines)
AI 数据处理在系统层的获取、变换与供应。
纳入：数据加载吞吐、AI ETL、训练输入平台。
排除：语料内容质量或合成数据方法。
边界：加快训练数据读取→此；挑选更好训练样本→M.02.02。

#### I.03.02 存储、检查点与模型状态 (Storage checkpointing and model state)
AI 模型和训练/推理状态的存储系统。
纳入：检查点、模型制品存储、恢复、AI 专用存储。
排除：通用文件系统没有 AI 研究关联；语义 Agent 记忆。
边界：模型权重 checkpoint→此；Agent 经验反思库→A.01.02。

#### I.03.03 向量检索与索引基础设施 (Vector retrieval and indexing infrastructure)
支撑 AI 检索的数据库/索引执行系统。
纳入：面向 AI embedding 的 ANN 后端、向量数据库服务。
排除：通用集合相似度算法无 AI 证据；RAG 检索学习。
边界：向量数据库引擎→此；RAG 训练配方→M.04.03。

#### I.04.01 MLOps、可靠性与可观测性 (MLOps reliability and observability)
AI 系统生命周期与运维保障。
纳入：实验/模型管理、系统故障恢复、监控、可复现平台。
排除：模型幻觉/偏差分析；只释出代码。
边界：服务容错是此类；OOD 可靠性是 M.05.02。

#### I.04.02 边缘与端侧部署系统 (Edge and on-device deployment systems)
将 AI 能力部署到受约束终端的系统。
纳入：端云协同、端侧 runtime、设备部署平台。
排除：只有小模型/量化方法；普通手机软件。
边界：端云推理切分系统→此；量化优化→M.03.03。

#### I.04.03 AI 基础设施安全与隔离 (AI infrastructure security and isolation)
AI 计算平台与服务底座的隔离及安全。
纳入：训练/服务平台访问隔离、执行沙箱、系统漏洞防护。
排除：模型隐私攻击；Agent 指令注入本身。
边界：GPU 多租户隔离→此；模型成员推断→M.05.03。

### Models · 模型

#### M.01.01 语言模型与基础模型 (Language models and foundations)
以语言模型结构、表示或通用语言模型产物为主要贡献。
纳入：新语言架构、训练出的通用语言模型、语言表示模型。
排除：只用/测试 GPT；所有后训练论文自动加此。
边界：GPT-3→此；LoRA 的核心是适配方法 M.03.01。

#### M.01.02 多模态与跨模态模型 (Multimodal and cross-modal models)
以多模态信息融合/对齐的模型结构为主要贡献。
纳入：视觉语言、多模态基础模型、跨模态表示。
排除：只是用图文数据评测；单一模态系统。
边界：新视觉语言融合架构→此。

#### M.01.03 视觉、图像与视频模型 (Vision image and video models)
以视觉表示、感知或生成模型本体为中心。
纳入：视觉表征、图像/视频生成、视觉模型架构。
排除：任何用了图像 benchmark 的泛用学习算法。
边界：DDPM 以图像生成模型为核心，可归此。

#### M.01.04 语音、音频与音乐模型 (Speech audio and music models)
面向声学/语音/音频的模型本体与表示。
纳入：语音识别/合成模型、音频生成、通用声学模型。
排除：使用转写 API 的会议应用。
边界：新语音编码结构→此；会议助手→A.02.02。

#### M.01.05 结构化、图与时序模型 (Structured graph and temporal models)
表格、图、时间序列等的模型架构与表示。
纳入：GNN、表格基础模型、时序模型、推荐表示模型。
排除：传统图算法无学习/推理关联。
边界：TabPFN 新模型→此；纯图最短路不自动归 Models。

#### M.01.06 世界、行动与科学模型 (World action and scientific models)
以物理世界、行动、科学对象的通用模型为中心。
纳入：世界模型、动作/策略基础模型、蛋白/化学/物理模型。
排除：仅行业工作流或普通数值模拟；所有机器人论文。
边界：可泛化世界模型→此；具体抓取系统→A.04.01。

#### M.02.01 预训练目标与扩展规律 (Pretraining objectives and scaling)
一般模型学习目标和预训练规模配置。
纳入：自监督/生成预训练目标、数据/模型/算力 scaling、预训练配方。
排除：后训练偏好目标；只是从头训练应用模型。
边界：GPT-3 的规模与通用能力研究可归此。

#### M.02.02 训练数据策划与合成 (Training data curation and synthesis)
改变学习数据内容、质量或选择方式。
纳入：语料去重/过滤、合成数据、课程、数据配比。
排除：只加速数据输入；领域 benchmark 发布无训练目的。
边界：Data selection→此；加载器吞吐→I.03.01。

#### M.02.03 学习算法与优化 (Learning algorithms and optimization)
AI 统计、监督、无监督、强化学习及优化方法。
纳入：优化器、泛用 RL、联邦/持续/迁移/元学习算法、因果学习。
排除：纯优化数学无 AI 关联；系统通信实现。
边界：新 actor-critic 算法→此；现成 RL 调电网仅 A.03.03。

#### M.02.04 学习理论与统计分析 (Learning theory and statistical analysis)
直接研究 AI 学习、估计、泛化的理论。
纳入：样本复杂度、泛化界、学习动力学、可识别性。
排除：无 AI/学习对象的纯数学、通用集合估计。
边界：学习界→此；DotHash 集合估计不因 KDD venue 自动归入。

#### M.03.01 监督与参数高效适配 (Supervised and parameter-efficient adaptation)
对已有模型的监督式参数/表示适配。
纳入：SFT、LoRA/adapter、指令微调、任务/域适配。
排除：只是对多个 LoRA 做服务调度；上下文提示。
边界：LoRA→此；无需更新权重的提示→M.04.01。

#### M.03.02 偏好对齐与 RL 后训练 (Preference alignment and RL posttraining)
基于偏好、奖励或验证反馈改变已有模型。
纳入：RLHF/RLAIF、DPO、可验证奖励 RL、奖励模型。
排除：泛用 RL；只用反思文本记忆不训练。
边界：DPO→此；Reflexion 不是参数后训练。

#### M.03.03 压缩、量化、剪枝与蒸馏 (Compression quantization pruning and distillation)
通过模型级改变降低资源需求或传递能力。
纳入：量化、剪枝、蒸馏、稀疏化、硬件感知压缩。
排除：硬件器件改变；软件 KV 内存分页。
边界：RAOQ 的量化感知训练→此，不自动加芯片。

#### M.04.01 提示与上下文学习 (Prompting and in-context learning)
不以权重更新为必要条件的上下文驱动能力方法。
纳入：提示设计、few-shot ICL、上下文适配机制研究。
排除：每篇使用提示的应用；仅 Agent 完整工作流。
边界：GPT-3 few-shot 研究可归此；简单调用 API 不足。

#### M.04.02 推理、搜索与测试时计算 (Reasoning search and test-time compute)
面向能力的推理过程、搜索、规划和测试时计算。
纳入：CoT、tree search、验证器推理、符号 AI 规划、反思推理。
排除：token 吞吐加速；Agent 组件编排只有系统贡献。
边界：提升答案正确率的搜索→此；推理 serving→I.02.03。

#### M.04.03 检索、知识落地与模型记忆 (Retrieval grounding and model memory)
改变模型利用外部/参数知识的推理或学习机制。
纳入：RAG、retriever-generator 联训、知识更新、模型级记忆。
排除：向量数据库执行；Agent 跨任务经验管理。
边界：RAG 模型→此；episodic Agent memory→A.01.02。

#### M.04.04 学习式工具使用与 Agent 策略 (Learned tool use and agent policies)
模型学习如何选择动作、工具与交互策略。
纳入：工具调用能力训练、函数选择策略、agentic policy learning。
排除：仅连接 API 的 harness；一般 RL 无工具/Agent 能力焦点。
边界：Toolformer→此；工具协议与连接器→A.01.03。

#### M.05.01 模型能力基准与测量 (Model capability benchmarks and measurement)
对模型能力进行新的测试、基准或测量。
纳入：通用模型/推理能力基准、评测方法与污染分析。
排除：每篇论文做实验；行业端到端评测。
边界：新模型能力基准→此；SWE-bench 主归应用评测。

#### M.05.02 鲁棒性、不确定性与分布偏移 (Robustness uncertainty and distribution shift)
模型在分布变化、噪声或未知条件下的可靠性。
纳入：OOD、校准、对抗鲁棒性、可靠泛化、幻觉不确定性。
排除：平台 uptime；一般学习理论无可靠性中心。
边界：ReAct OOD 2021→此，和 2023 Agent ReAct 不同。

#### M.05.03 模型安全、隐私与行为对齐 (Model safety privacy and behavioral alignment)
模型层风险、隐私、偏见和安全行为。
纳入：有害输出、越狱、模型隐私、公平、危险能力。
排除：泛化 preference alignment 无具体安全问题；系统隔离。
边界：DPO 不自动加 safety；须有具体安全目标/证据。

#### M.05.04 可解释性与机制分析 (Interpretability and mechanistic analysis)
直接解释模型内部表示、机制及因果行为。
纳入：mechanistic interpretability、特征归因、因果探针。
排除：仅声明方法可解释；普通消融实验。
边界：专门识别模型电路→此。

### Applications · 应用

#### A.01.01 Agent 编排与 Harness (Agent orchestration and harnesses)
整合模型、状态、执行循环和任务控制的 Agent 系统。
纳入：Agent loop、规划执行协同、工作流/harness、错误恢复。
排除：服务 batching；只有模型推理技巧无交互系统。
边界：ReAct 的推理—行动交互可与 M.04.02 同标。

#### A.01.02 Agent 持久记忆与状态 (Persistent agent memory and state)
管理 Agent 的经历、长期状态和跨试次学习素材。
纳入：情节/长期记忆、经验压缩、记忆读写和检索策略。
排除：KV cache；模型权重；普通 checkpoint；RAG 通用语料。
边界：Reflexion 的 episodic memory→此。

#### A.01.03 工具与环境集成 (Tool and environment integration)
Agent 与软件工具、环境和接口连接的系统设计。
纳入：工具适配、协议、执行器、沙箱交互、环境连接。
排除：仅训练模型选择 API；工具作为基准但无整合贡献。
边界：新的通用工具执行层→此；Toolformer 主归 M.04.04。

#### A.01.04 多 Agent 协作 (Multi-agent coordination)
多个 AI Agent 在系统层交流、协作和任务分工。
纳入：多 Agent 工作流、协商、合作/竞争组织。
排除：数据并行多 GPU；只有 MARL 参数学习算法。
边界：部署多个 Agent 分工→此；MARL 学习方法→M.02.03。

#### A.01.05 Agent 评测与环境 (Agent evaluation and testbeds)
测量完整 Agent 在交互任务中的行为与成果。
纳入：端到端基准、环境、harness 评测、任务完成/安全评测。
排除：单次模型问答基准；普通使用 benchmark 验证。
边界：AgentBench→此；可无行业域。

#### A.02.01 软件工程应用 (Software engineering applications)
AI 面向真实软件开发任务和产物。
纳入：代码仓库修改、调试、测试、审查、开发 Agent 与其评测。
排除：泛用代码预训练模型本体；纯非 AI 开发工具。
边界：SWE-bench→此；通用代码 LM 训练可能属 M.01.01。

#### A.02.02 知识工作、搜索与生产力 (Knowledge work search and productivity)
AI 面向用户的信息获取、知识管理和办公任务。
纳入：知识助手、搜索问答产品工作流、文档与办公自动化。
排除：通用 RAG 方法；非 AI 传统搜索。
边界：企业文档助手任务整合→此；原始 RAG 论文→M.04.03。

#### A.02.03 推荐、排序与广告 (Recommendation ranking and advertising)
AI 优化信息分发、个性化和商业匹配任务。
纳入：推荐排序系统、广告匹配、个性化检索及任务评测。
排除：所有表示学习在推荐数据上测试；传统启发式无 AI。
边界：推荐目标明确的扩散推荐方法可归此并按贡献加模型标签。

#### A.02.04 创作媒体与人机交互 (Creative media and human-AI interaction)
AI 创作使用过程、用户体验和交互系统。
纳入：创意工作流、共同创作、交互原型、人机协作评估。
排除：通用图像生成模型；只以创作作动机。
边界：创作编辑界面实验→此；DDPM 不自动属于创作应用。

#### A.03.01 健康、生物与药物发现 (Health biology and drug discovery)
AI 针对健康、生物与药物任务的具体结果。
纳入：临床决策、药物发现流程、疾病预测和领域评测。
排除：泛用蛋白基础模型只有模型贡献；普通医学统计无 AI。
边界：候选药物筛选工作流→此。

#### A.03.02 科学与工程应用 (Scientific and engineering applications)
AI 用于具体科学发现、模拟或工程设计。
纳入：材料/物理发现、AI 辅助实验、硬件/工程设计。
排除：纯数值计算无 AI；通用科学基础模型本体。
边界：PRIME 数据驱动硬件设计→此；未证明 AI 芯片对象时不强加 C。

#### A.03.03 能源、环境与农业应用 (Energy environment and agriculture applications)
AI 作为工具解决能源、气候、环境或农业问题。
纳入：电网 RL、天气/碳通量预测、农业感知任务。
排除：为 AI 计算供能或核算 AI 碳足迹。
边界：L2RPN 电网管理→此；LLMCarbon→E.02.01。

#### A.03.04 专业、教育与公共服务 (Professional education and public services)
AI 用于金融、法律、教育和公共服务等工作。
纳入：法律/金融助手、教学、政务和社会服务应用/评测。
排除：只有金融文本作泛用模型数据；纯社会统计。
边界：法律工作流评测→此；法律语料预训练本身→Models。

#### A.04.01 机器人与自主系统 (Robotics and autonomous systems)
AI 面向物理行动、机器人及自动驾驶任务。
纳入：操控、导航、自动驾驶系统、具身任务/环境评测。
排除：通用视觉模型；纯机械结构无 AI。
边界：机器人任务完成实验→此；通用动作基础模型可另有 M.01.06。

#### A.04.02 产业、物流与建筑环境 (Industrial logistics and built environment)
AI 面向生产、供应链与建成环境流程。
纳入：制造质检、物流调度、建筑运营、工业决策应用。
排除：普通优化调度无 AI；AI 数据中心设施属于 I。
边界：AI 工厂产线优化→此；生产 AI 算力的数据中心→I。
