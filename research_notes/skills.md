# 技能演化论文核读（7篇主批次）

核验日期：2026-10-08。只读论文、官方仓库和发布资产，没有执行第三方代码。各篇已读取正文、实验及相关附录，并核对最新版；页码按 PDF 从1开始。本文的“审稿判断”“本地方案”是分析，不是作者实验结论。新增四篇另见 skillforge_muse 文件。

## 1. SkillX: Automatically Constructing Skill Knowledge Bases for Agents

- 版本/原文：[2604.04804v2](https://arxiv.org/html/2604.04804v2)，2026-04-19；全文可访问。
- 问题与方法：从强模型轨迹构建可跨模型复用的技能库。分规划、功能、原子三级；合并/过滤、最多3轮迭代，并用环境探索扩大覆盖。运行时先改写伪计划，再检索技能，不更新执行模型权重（§3–4）。
- 实证：[表1，PDF p6](https://arxiv.org/pdf/2604.04804v2#page=6)：Qwen3-32B 的 BFCL-v3 Avg@4 53.67→63.67，AppWorld 27.68→35.12；前者是+10.00个百分点，后者+7.44，不能统称“全部提高10%”。同一 GLM-4.6 教师的 ExpeL 对照分别59.33、32.94。
- 数据/算力：BFCL 50训练/150测试；AppWorld训练90例；每训练任务4次轨迹。教师GLM-4.6、嵌入Qwen3-Embedding-8B（§5.1/附录A）。未找到完整 GPU 小时/总成本。
- 公开资产：[官方仓库](https://github.com/zjunlp/SkillX)有抽取、过滤、推理代码及 appworld 技能库目录；README仍保留“计划发布”旧文案，不能据摘要断言尚未开源，也不能仅凭目录断言全部复现资产齐全。
- 审稿判断：§3.3式(8)及紧接文字明确按 Q_test 性能停止迭代，存在测试集选择偏差；应要求独立验证集。表1区分同模型抽取与强教师蒸馏，跨范式比较须控制教师、轨迹和预算。统一初始查询检索对原本动态记忆方法可能不利。论文未给出普遍跨环境零样本迁移的充分证据。
- 无付费本地方案：先复用已公开技能做“无技能/原始轨迹/三级技能”同执行器对照，再决定是否自采集。CPU-only适合结构、检索与评估器测试；16GB GPU用较小量化开放模型和小嵌入模型做机制复现。更换教师/嵌入后不是原表复现。原32B和8B嵌入同时运行、再加大教师，不应承诺16GB单卡可承载。

## 2. From Procedural Skills to Strategy Genes: Towards Experience-Driven Test-Time Evolution

- 版本/原文：[2604.15097v4](https://arxiv.org/html/2604.15097v4)，2026-09-17；全文可访问，beta technical report。
- 问题与方法：比较长篇技能包与紧凑控制对象。Gene用关键词、摘要、策略、AVOID与可选验证约束；GEP记录对象、执行证据和演化历史（§3/附录A）。
- 实证：[表1，PDF p7](https://arxiv.org/pdf/2604.15097v4#page=7)：45科学编程场景、4590 retained trials，checkpoint平均分：无提示51.0、Skill49.9、Gene54.0。Pro单独60.1→59.9，Flash41.8→48.2；收益不是两模型都增加。表13的约230-token匹配片段仍低于Gene。Fig5另报 CritPt 17.7→27.14。
- 数据/算力：Gemini 3.1 Pro/Flash Lite，温度0.05、输出上限16384、代码120秒超时；两轮演化各约2天。v4附录D的$0.81仅可观测输入/输出，不含不可恢复的 reasoning token，不能解释为全成本。
- 公开资产：[Evolver](https://github.com/EvoMap/evolver)、[skill2gep](https://github.com/EvoMap/skill2gep)、[70题CritPt提交与汇总](https://github.com/EvoMap/critpt-openclaw-reproducible-70)。skill2gep官方说明自己是协议适配/验证器，不保证任意技能自动蒸馏质量；未核实45场景完整原始基准及全部trial日志已发布。
- 审稿判断：checkpoint平均分不等于整题成功率；仅45场景、两个同厂闭源模型，无通用技能无效的结论。Skill在实验中被整包注入，不等价于按需读取技能的完整harness。CritPt额外包含两天演化和外部论文知识，未做充分等预算/相同信息对照，不能把收益单归因Gene格式；测试重叠/演化顺序隔离不够明确。
- 无付费本地方案：对自己可确定评分的小型Python任务，用同一本地模型比较无指导、长文、等token摘要、Gene、Gene去AVOID；冻结测试任务和提示预算。CPU可做JSON/schema和已有日志审计；16GB GPU可做小模型机制试验。原Gemini数字不能离线精确重现；不要自动连接共享网络或运行其自改代码循环。

## 3. Trace2Skill: Distill Trajectory-Local Lessons into Transferable Agent Skills

- 版本/原文：[2603.25158v5](https://arxiv.org/html/2603.25158v5)，2026-06-04；全文可访问。
- 问题与方法：冻结模型；并行分析成功/失败轨迹，错误分析器可检查文件和验证修复，再层级合并补丁成一个可携带技能目录。无需推理时向量检索（§2）。
- 实证：[表1，PDF p4](https://arxiv.org/pdf/2603.25158v5#page=4)：122B自深化+Combined，SpreadsheetBench-Vrf由48.33升至69.83；35B创建+Error迁给122B，在WikiTQ由23.73升至81.38（+57.65pp，相对弱Parametric基线）。表4中并行约3分钟、逐条约60分钟，但35B的Soft/Hard并非并行更好。
- 数据/算力：v5明确200进化/200留出，完整SpreadsheetBench剔除所有进化题；DocVQA改为50进化/5299评测。主要开放模型Qwen3.5-35B-A3B/122B-A10B，128并发；附录B1计时硬件为8×A100，而非旧版A800。
- 公开资产：[官方代码](https://github.com/Qwen-Applications/Trace2Skill)提供400题Verified数据、已发布xlsx技能、评估和演化入口，明确支持localhost OpenAI兼容接口。发布范围主要是电子表格，不能默认为论文所有领域代码齐全。
- 审稿判断：最新版数据隔离显著优于旧版表述，应引用v5。+57.65是挑出的单方向最大增益，不是整体平均；跨模型有负迁移，agentic错误分析并非所有配置胜出（表12）。同样轨迹与harness的消融比整体系统排名更有因果解释力。3分钟是大节点墙钟时间，不是单卡资源消耗，亦非整个流程成本。
- 无付费本地方案（优先）：先用公开技能、官方评分器和10–20留出题验证工具链，再以同一本地小模型生成独立训练轨迹，比较无技能/人工技能/顺序编辑/并行合并。16GB GPU先用小量化模型而非强装35B，降低并发；明确标为缩小模型机制复现。CPU-only先跑数据隔离、补丁冲突和评分器测试，推理仅做极小样本，不报告速度对标。

## 4. SkillClaw: Let Skills Evolve Collectively with Agentic Evolver

- 版本/原文：[2604.08377v2](https://arxiv.org/html/2604.08377v2)，2026-08-10；全文可访问。
- 问题与方法：跨用户收集会话，按技能归组；evolver选择refine/create/skip，经候选验证后同步共享库（§2）。
- 实证：[表3，PDF p7](https://arxiv.org/pdf/2604.08377v2#page=7)：Qwen3-Max、8模拟用户、6轮，WildClawBench六类中仅报告四类。Social54.01→60.34；Search22.73→34.55；Creative11.57→21.80；Safety24→32，均是作者best-skill部署视图。
- 数据/算力：完整Linux工具环境、15–50步、外部API/模型下载；生成、演化和验证均用Qwen3-Max。没有充分公开总token、美元或硬件成本。
- 公开资产：[官方实现](https://github.com/AMAP-ML/SkillClaw)、[WildClawBench](https://github.com/InternLM/WildClawBench)。现行代码有客户端代理、可选演化服务，支持本地文件存储；这不意味着原论文全部部署/数据已一键复现。
- 审稿判断：缺独立未见用户/未见任务留出说明。表5、7出现相同技能池重测后更高分成为best-so-far，单调曲线含选择效应。§2.3“只接受改进就不退化”仅对所测样本成立，不能保证真实分布。尤其不能把Safety类可靠性提升泛化成完整安全验证；集体会话还需隐私与技能注入隔离。
- 无付费本地方案：只使用合成、无敏感数据的两个模拟用户；本地存储和本地模型，先做旧技能/候选技能在相同种子、独立留出题上的配对比较。CPU适合证据归组与版本回退；16GB可做小模型演化；原Qwen3-Max与外部API任务只能改造，不能承诺原分数。

## 5. SKILL0: In-Context Agentic Reinforcement Learning for Skill Internalization

- 版本/原文：[2604.02268v2](https://arxiv.org/html/2604.02268v2)，2026-05-15；全文可访问。
- 问题与方法：训练时给技能、按验证集helpfulness逐步撤出，以GRPO让策略参数承担技能；把技能/历史渲染为视觉上下文（§3）。不是“完全不训练”的上下文学习。
- 实证：[表1，PDF p6](https://arxiv.org/pdf/2604.02268v2#page=6)：3B在ALFWorld87.9、Search-QA40.8，相对视觉AgentOCR78.2/34.2，+9.7/+6.6pp；每步上下文0.38k/0.18k。v2表2增加WebShop：3B成功率66.4。7B Search-QA44.4仍低于SkillRL47.1，不能称所有基线全面胜出。
- 数据/算力：Qwen2.5-VL 3B/7B；最多180训练步、4×H800；从训练集划验证，SkillBank来自SkillRL；检索QA需E5及知识索引（§4.1/附录E）。
- 公开资产：[SkillZero官方仓库](https://github.com/ZJU-REAL/SkillZero)含训练脚本、skills、视觉渲染与环境代码；依赖vLLM/FlashAttention/VeRL，Search索引另外下载。未核实可直接下载的最终训练checkpoint。
- 审稿判断：视觉与文本骨干/上下文压缩构成混杂，最有说服力的是相同视觉基线AgentOCR。3B SkillRL明确省去cold start和skill evolution，不能把它当完整强对手。每步token较少不等于总计算/延迟较少，视觉编码及训练成本未计入。开放基准预训练污染仍无法由训练/测试划分排除。
- 无付费本地方案：CPU或16GB单卡优先验证SkillBank分组、渲染和推理阶段；完整4×H800 RL训练不属于轻量复现。单卡若缩小batch、rollout及模型甚至改LoRA，应标“算法机制试验”并先测显存，不能预承诺能训或能重现主表。

## 6. Skill1: Unified Evolution of Skill-Augmented Agents via Reinforcement Learning

- 版本/原文：[2605.06130v3](https://arxiv.org/html/2605.06130v3)，2026-05-12；全文可访问。
- 问题与方法：一个策略联合学检索查询/重排、技能执行、轨迹蒸馏；任务回报的EMA趋势给选择信用，当前回报减最高效用给蒸馏信用（§3）。
- 实证：[表1，PDF p6](https://arxiv.org/pdf/2605.06130v3#page=6)：Qwen2.5-7B在ALFWorld97.5、RetroAgent94.9；WebShop成功82.9 vs82.3，仅+0.6pp。附录D的ALFWorld三种子97.5±0.6 vs94.9±0.9，Welch p=.021。表2无库80.9、无选择91.8、无蒸馏92.4。
- 数据/算力：官方环境train/test，库上限5000；8×H800-80GB、BF16 FSDP、vLLM TP4；约100–150步、ALFWorld约30小时（附录C）。
- 公开资产：[官方Skill1](https://github.com/AlphaLab-USTC/Skill1)已含VeRL、环境和训练脚本；环境数据来自ALFWorld/WebShop原项目，README未提供可直接验证的最终checkpoint。
- 审稿判断：除RetroAgent外，多数基线借自其他论文；同骨干不自动等于同harness/预算。附录同时写100–150 steps与“150 epochs”，复现应以脚本澄清。所有检索候选都更新同一回报，蒸馏奖励又是未来价值代理，不能当成无偏因果信用分配。仅两个文本环境，小幅WebShop收益未见同样显著性证明。
- 无付费本地方案：先复现技能效用EMA、选择/蒸馏奖励与库更新的单元测试；CPU可完成。16GB可做7B量化推理与小任务库对照，但不能等价复现8卡全参数RL。训练级比较待有多GPU或作者checkpoint；不调用付费API。

## 7. From Context to Skills: Can Language Models Learn from Context Skillfully?（Ctx2Skill）

- 版本/原文：[2604.27660v4](https://arxiv.org/html/2604.27660v4)，2026-07-27；全文可访问。
- 问题与方法：从给定长上下文自行出题、作答、判分；Challenger/Reasoner的技能共同演化，Proposer诊断、Generator改写；跨时间回放选兼顾难易探针的技能集（§3）。
- 实证：CL-bench500上下文/1899任务，所有rubric通过才算解出。[表1，PDF p7](https://arxiv.org/pdf/2604.27660v4#page=7)：GPT-4.1 11.1→16.5，GPT-5.1 21.1→25.8，GPT-5.2 18.2→21.4。表3最新轮14.7低于回放选择16.5。
- 数据/算力：每上下文5轮×5题，另有回放；核心实验闭源GPT系列，Judge GPT-5.1；附录B总API成本约$30K，含探索，不是单次使用成本。
- 公开资产：[官方仓库](https://github.com/S1s-Z/Ctx2Skill)、[数据/日志](https://huggingface.co/datasets/ssz1111/Ctx2Skill)、[生成技能](https://huggingface.co/datasets/ssz1111/Ctx2Skill-Skills)。代码有OpenAI兼容接口；数据网页预览出现类型转换错误，不等于底层文件不可下载。
- 审稿判断：v4表11换loop judge仍21.2（原21.4），缓解同judge偏好；表12约12500生成题的50/100-gram零重叠，只排除长字面抄袭，不能排除语义重合。技能和测试共享context是任务定义，不应直接指控泄漏。模型/任务生成成本明显超过单次Prompting，需等总预算对照；推理仍增加技能token，“无额外成本”应理解为无需重新演化，不是免费上下文。
- 无付费本地方案：先审计公开日志/技能；用合成规则文档和确定性答案校验器替代付费Judge，小模型完成1–2轮mini-loop，再测冻结未见问题。CPU可做评分与静态技能检查；16GB可做短上下文小模型自博弈。替换GPT/Judge后只能叫机制复现，无法核对原主表的闭源结果。

## 横向结论与建议（独立分析）

1. 不要把所有“自进化”合并成一种能力：SkillX是库构建/检索，Trace2Skill是技能文件归纳，SkillClaw是跨用户治理，Gene是表示与控制实验，Ctx2Skill是每个上下文的自博弈，SKILL0/Skill1真正改变模型权重。
2. 最常见误读是百分点与相对增长混用、最佳子项代替平均、checkpoint分数代替整题成功率、无权重训练代替无成本、最佳验证记录代替独立测试。
3. 小机器优先：公开资产与离线评分审计 → Trace2Skill的已发布技能对照 → Gene等token表示对照/简化Ctx2Skill → 有硬件再考虑RL。不应从8卡训练论文直接承诺16GB复现。
4. 统一公平协议：先按任务族划训练/验证/最终测试；技能生成只能读训练，选版本只能读验证；锁模型、工具、采样、token和总尝试预算；至少3种子并同时记录全部失败、整题成功率、token、时间、技能体积；最终测试只跑预注册配置。要宣称技能真正迁移，必须另设新模板/新文件/新任务族。
5. 16GB/CPU-only是计划档位，不是已确认用户硬件。小模型Q4权重尺寸只代表下界，还需要KV cache、视觉编码、运行时和并发余量。没有付费API仍有本地计算、电力与存储成本。
6. 当前仅完成文献/资产核验，未报告任何本地跑分。下载/安装依赖、运行生成的工具代码与修改用户机器都应在获准且环境就绪后再进行，使用隔离目录、无网络凭据及限时执行。

## 版本差异警告

- Trace2Skill v1与v5的DocVQA切分、性能、表格数据排除和硬件说明有实质变化。不要混引用“35B DocVQA下降6.2pp”的旧表与v5新结果。
- Ctx2Skill v4新增judge解耦、字面重叠和错配技能对照；批评必须保留这些补充证据。
- SkillX/Trace2Skill摘要或正文的“即将发布”可能落后于当前已可读仓库。发布状态按2026-10-08核验，代码存在不代表全部数据/checkpoint已公开。

## 本地证据归档

七篇最新版PDF及pdftotext文本已保存于同目录：skillx、genes、trace2skill、skillclaw、skillzero、skillone、ctx2skill。主结果表已逐张渲染并视觉核验，截图在 skills_figures/；版本、哈希与路径见 skills_source_manifest.json。PDF视觉核对优先于HTML解析结果。
