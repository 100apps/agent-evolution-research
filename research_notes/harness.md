# Harness 与自进化论文原文核验

核验日期：2026-10-08。本文件依据下载的全文 PDF、论文附录及作者官方仓库；没有执行第三方项目代码，也没有调用收费模型 API。页码是 PDF 印刷页码。下述“最小实验”为建议方案，不是已完成复现实验。百分比提升区分百分点（pp）与相对百分比。排行榜名次只描述论文当时报告，不能当作今天的排名。

## 1 Meta-Harness

- 完整题名：Meta-Harness: End-to-End Optimization of Model Harnesses。Yoonho Lee 等；arXiv:2603.28052v1，2026-03-30，26页。[固定版原文](https://arxiv.org/pdf/2603.28052v1)；[项目](https://yoonholee.com/meta-harness/)；[作者代码](https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact)。
- 问题与方法（§3，pp4–5）：固定执行模型，将提示、记忆、检索与编排视为可改写的 Python harness。外层 Claude Code/Opus-4.6 可查询所有历史候选源码、分数、原始轨迹，自选历史、诊断和改写，而非只读一个候选的压缩反馈。候选先通过接口检查，再独立运行评估；性能/上下文成本以 Pareto frontier 选取。关键是“完整可查询经历”，不是把全部日志一次塞入上下文。
- 具体发现（附录B，pp18–22）：分类 harness 用标签清单、每类相关例子与 query-anchored 对比样例；低成本变体先生成分类草稿，再检索5个支持例及5个反例。数学 harness 按词法路由到组合、几何、数论、其他，分别 BM25 检索、去重与难度重排。编码最佳变体主要是在首轮前收集 OS、目录、语言/包管理器、内存快照，增加约80行，并保留 Terminus-KIRA 主循环。
- 实验与结果：
  - 分类：GPT-OSS-120B；LawBench 215类、Symptom2Disease 22类、USPTO-50k 180类；20轮×2候选。表2 p6 独立测试平均48.6%，ACE40.9%、MCE40.0%、全量few-shot40.8%；额外上下文11.4K token，ACE50.8K，约4.46倍节省。+7.7pp不是7.7%相对提升。
  - 表3、4 p7 为搜索集：完整轨迹 median/best 50.0/56.7；仅分数34.6/41.3；分数+摘要34.9/38.7。GEPA32.6/40.2、Best-of-N34.0/44.2、OpenEvolve39.1/43.3、TTT-Discover34.1/45.6。不能把56.7当测试成绩。评估次数匹配，未证明总 token 或总美元成本匹配。
  - OOD分类：9个未见数据集，表5 p8 平均73.1%，ACE70.2%，32-shot69.6%。
  - 数学：250题搜索、40轮109候选；最终200题（100 IMO-AnswerBench、60 IMO-ProofBench、17+23 ArXivMath），每题3次采样平均 pass@1。表6 p8 五模型平均：无检索34.1、dense k5 38.1、BM25 37.5、Meta38.8。相对无检索+4.7pp，相对最强固定平均基线仅+0.7pp；不是所有模型/所有基线都赢。GPT-OSS-20B也用于搜索，因此“5个全为未见模型”措辞不严，真正新增模型是4个。数学语料535,356条，去重与0.8 Jaccard近似过滤（表10/11，p24）。
  - TerminalBench-2：表7 p9，Opus4.6 76.4% vs KIRA74.7%；Haiku4.5 37.6% vs Goose35.5%。论文明确搜索与最终评估都用同89题（§4.3），属于 benchmark-specific discovery。官方 artifact 说明89题×5次；其他框架多取官方排行榜，非全部同设施重跑。
- 局限与核验意见：作者承认仅强 proposer Claude Code 验证，其他 proposer 泛化未知（p10）。TB2没有独立搜索/测试划分；字串泄漏审计不能消除统计过拟合。数学搜索集正文250题与附录D实施建议“88 problems”不一致，复现须询问/查配置。表9的Ctx是字符，表2是token，不可直接混比。全文有经验性因果解释，但不等于严格因果实验。
- 复现资源：公开仓库是最终 TB2 agent artifact（agent.py、prompt-templates、Anthropic caching），不是分类/数学/完整外循环的完整一键发行。README要求 Harbor、Anthropic key、Runloop；原成绩依赖收费闭源模型及大量隔离执行。作者称几小时完成搜索，但无完整成本账单。开源120B执行模型并不意味着一般笔记本能原样复现。
- 无付费API最小实验（建议）：先独立实现20个纯文本分类小任务，搜索集10、验证5、锁定测试5；固定本地模型与token上限，比较“分数”“分数+摘要”“源码+可查询完整轨迹”，3种子、每组5轮×2候选。保护评测器与测试标签，仅允许改 harness；记录测试正确率、总输入/输出token、模型调用数和搜索开销。没有本地模型时只用预置候选验证日志索引/隔离/选择逻辑，称为机制测试，不能声称复现性能。建议普通CPU先做机制测试；7B级量化本地模型资源取决于部署，不能保证再现Opus proposer能力。

## 2 Agentic Harness Engineering

- 完整题名：Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses。Jiahang Lin 等；arXiv:2604.25850v4，2026-05-18（v1为4月28日），[固定版](https://arxiv.org/pdf/2604.25850v4)；[官方仓库](https://github.com/china-qijizhifeng/agentic-harness-engineering)。
- 方法（§3，pp4–5）：NexAU将系统prompt、工具说明、工具实现、中间件、skill、子agent配置、长期记忆显式文件化。Agent Debugger把约千万token轨迹做成总览→按任务报告→原轨迹的可下钻证据。Evolve Agent改组件时写manifest，声明失败证据、原因、预期修复与回归风险；下一轮任务级变化验证，文件粒度回滚。模型、评分器、原始记录只读。主张是“可观测且可证伪的工程改动”，并非权重训练。
- 实验（§4、附录A）：full 89-task TB2上单次10轮搜索，约32小时；GPT-5.4作为角色基础模型。正文概述high，但表4 p16明确 Code Agent high、Evolve/Explore xhigh，不能说角色推理预算完全相同。每题2 rollouts、最多300执行轮、200K上下文、每次生成32K、96并发E2B、每题1小时，debugger16并发/600秒。基础故障/超时计失败，token均值排除中止trial。
- 精确成绩：
  - 表1 p6：seed NexAU0 69.7%，AHE77.0（+7.3pp），ACE68.9、TF-GRPO72.3、Codex71.9、Terminus2 62.9、OpenCode47.2。Hard30题 AHE53.3低于Codex56.7，不可说全部难度最优。
  - 表2 p7，冻结harness直接迁移SWE-bench-verified500题：75.6% vs seed75.2%，只+0.4pp（约2题）；token/trial461K vs526K，约-12.4%。ACE74.6%/679K、TF-GRPO74.2%/582K。没有显著性检验，不能把“最高平均”扩写为稳定明显正确率提高。
  - 图3 p8：DeepSeek-v4-flash51.7→61.8（+10.1pp），Qwen3.6-plus56.2→62.5（+6.3pp），Gemini3.1-flash-lite36.5→41.6（+5.1pp）；GPT5.4 medium65.7→68.0、xhigh72.5→74.7（四舍五入差与文内+2.3一致按作者口径）。
  - 表3 p8：memory-only75.3、tool-only73.0、middleware71.9、prompt-only67.4 vs seed69.7。组件并非可加：3个正向单件合计+11.1pp，全件仅+7.3pp；Hard上memory-only63.3高于完整53.3。
  - 图4 p9：修复预测precision33.7%、recall51.4%；回归预测precision11.8%、recall11.1%。作者承认“能解释改善但看不见多数退化”，审计记录不等于可靠自知。
- 局限：同TB2搜索与评估；仅一个10轮campaign；泛化预算与GPT5.4-high超时/步数耦合。公开的组件消融支持工具/记忆价值，但不是三个observability支柱各自的完整因果消融。无成熟安全隔离保证；把“有manifest”直接当成生产自治安全是误读。
- 代码/资源：官方README明确 Agent Debugger 仅部分开源，受公司策略限制。Python≥3.13、uv、tmux、模型endpoint、E2B与Serper；可自托管E2B但不是开箱即用单机Docker。不要把仓库后来GPT5.5的84.7%混入本论文GPT5.4的77.0%。
- 无付费最小实验（建议）：自行做10个沙盒Python修复任务，每题2次，保持模型与硬超时固定；seed仅shell；3轮演化，组件限定prompt/tool/middleware/memory，manifest强制列“预计修复/预计退化”，次轮计算precision/recall并用5个锁定任务测泛化。本地模型可先仅产生结构化patch提案，人工审查后在无网络临时目录运行。若不用原Debugger与E2B，应称可观测演化机制复现，不能称原实验复现。保留只换memory、只换prompt两项消融比追大榜更值钱。

## 3 Continual Harness

- 完整题名：Continual Harness: Online Adaptation for Self-Improving Foundation Agents。Seth Karten 等；arXiv:2605.09998v1，2026-05-11，28页，PDF内日期5月12日。[全文](https://arxiv.org/pdf/2605.09998v1)；[项目](https://sethkarten.ai/continual-harness/)；[代码](https://github.com/sethkarten/continual-harness)。
- 方法（§2–3，pp3–5）：在不重置的同一游戏episode中，actor行动，每F步（warmup W后）Refiner读轨迹，依次更新system prompt、子agent、技能、记忆；四者为外部状态，基础模型冻结。与EvoTest的episode间更新不同。第二层训练用256步在线rollout→PRM评分→frontier teacher重标低分窗口→soft SFT，在下一训练迭代接续同一模拟器存档。
- 输入不是纯视觉：屏幕、按钮之外还有由模拟器RAM生成的局部ASCII地图及get_party_hp等通用原语（附录A p14）。没有攻略/全局目标不等于没有人工环境接口。全文把Red/Crystal分辨率160×144、Emerald240×160，2倍放大，120帧/观察步。
- 必须分开三类证据：GPP先前完整通关Blue/Yellow Legacy/Crystal包含人类在环迭代；自动Continual Harness是Red/Emerald阶段性里程碑评估；模型+harness co-learning也是阶段性进展，不是全自动通关所有游戏。
- 实验：至少3种子，报告中位数与透明单种子；Hmin最小接口、Hexpert人写A*、类型表/伤害计算/目标；CH from-scratch、bootstrap-frozen、bootstrap-updating。图5 p7是Red11个里程碑子集与Emerald9个；图6 p8用Emerald31里程碑集合与24小时种子，不能混读为通关率。
- 结果（§4.4，p7；图6 p8）：Gemini Pro from-scratch 100%里程碑/$130中位数，Hmin98%/$215，约40%成本降低；Flash bootstrap-updating80%/$42 vs Hmin77%/$30，收益波动；Flash-Lite CH仅3–13%，低于Hmin20%且成本相同或更高。这是非常直接的能力门槛反例：弱模型不一定能使用自写工具。
- 机制证据：图8 p9导航skill路径成本相对Dijkstra缺口从接近50%降至个位数，但报告top10%技能，不能称整个技能库平均。附录图16 p22：Emerald phase1建99技能，仅17被调用、5至少成功一次；Red phase1建110，33被调用、3至少成功一次。说明“生成技能很多”不等于可用能力增长。
- Co-learning（pp25–27）：LoRA r=α=256、bf16、8K上下文、Unsloth/H200；SFT lr2e-5；offline GRPO G4、lr1e-6、KL0.04、batch8、590步；在线256步rollout、PRM stride8、soft SFT3epoch/lr5e-6，教师Gemini3.1pro。图7仅展示5条有进展运行（+2至+5里程碑），不是所有run总体均值。附录D.2称Red可用31B初始policy，D.4却称26B SFT，存在初始化描述不一致；Red canonical18里程碑与D.4出现24/30编号亦需配置解释，不能填补猜测。
- 局限：未独立拆开更多交互时间、teacher重标、权重更新、harness更新各自贡献；未与相同任务/预算reset训练正面对比；小模型共同担任教师/学生未成功；尚无收敛证明。附录案例也有1003轮卡住、工具schema脆弱和反馈盲区。
- 代码门槛：当前MIT仓库有最小/专家/CH scaffolds，Python3.10–3.11；Red用PyBoy、Emerald用mGBA；必须自备合法游戏ROM，ROM未附带；官方后端配置主要是收费API。CH需显式 --enable-prompt-optimization，否则只stub；README演示F=50。代码已历多次更新，需固定commit，不默认完全对应论文。
- 无付费最小实验（建议）：最现实先用自建10×10局部可见网格迷宫，不含商业ROM，固定步数和3种子；冻结本地文本模型，每20步允许仅修改记忆/导航函数；比较无更新、继承但冻结、继承并继续更新；记录有效率、实际被调用技能占比、path-cost、总推理token。此为reset-free机制缩小实验，不是Pokemon分数复现。真正Pokemon可先验证模拟器+存档+日志；原共同训练需要大显存与frontier teacher，无法“无API完全复现”原结果。

## 4 Autogenesis

- 完整题名：Autogenesis: A Self-Evolving Agent Protocol。Wentao Zhang 等；arXiv:2604.15034v5，2026-06-20，29页（v1 4月16日）。[固定版](https://arxiv.org/pdf/2604.15034v5)；[官方仓库](https://github.com/DVampire/Autogenesis)。
- 方法（§3–4，pp3–6）：AGP协议分两层。RSPL把Prompt、Agent、Tool/MCP/Skill、Environment、Memory登记成有状态、生命周期和版本的被动资源；模型/版本/动态加载/轨迹管理为共用基础设施。SEPL把更新规约成Reflect→Select→Improve→Evaluate→Commit，受learnability mask限制，可回滚。AGS通过Agent Bus让规划者与并行子agent共享资源与结果。协议是接口/治理抽象，reflection是主要实验优化器；TextGrad/GRPO等兼容性不等于全部验证过。
- 科学数学（表1 p7）：GPQA-Diamond198题、AIME24/25各30题，无外部工具、至多3轮演化、exact match。GPT4.1 vanilla 65.15/23.34/20.00，joint67.67/40.00/33.33；GPT4o47.98/13.34/6.67→58.08/16.67/13.34；Gemini3-flash88.38/83.33/83.33→90.40/93.33/93.33。GPT4.1 AIME24 +16.66pp约+71.4%相对，不是+71.4pp。反例：GPT4.1 GPQA Prompt-Evo与Solution-Evo均68.68，比joint67.67高，正文“joint consistently outperforms”应视为概括过强。
- 通用agent（表2、图2 p7；§5.2 p8）：GAIA val165/test300题；Gemini3.1-pro-preview、top planner最多30步、specialists20步。Agent-Evo val89.70→93.33（+3.63pp），test79.07→89.04（+9.97pp、+12.61%相对）；HLE59.6%由o3-mini按官方协议judge。论文列系统是跨模型/设施排行榜，不能据此把差异因果归于协议。正文称“四个”specialists却枚举五类，配置需仓库核对。
- 代码题（表3 p8；§5.3 p9）：自建100道较新LeetCode，Gemini3flash +3轮Solution-Evo。通过数 Python79→87、C++84→99、Java84→98、Go82→95、Kotlin75→95；比较的是更多推理/执行反馈后的解题改进，非资源协议本身的独立消融。代码性能同样有代价：Python和Kotlin内存上升。
- 局限（§6 p9）：演化增加延迟/token，尚无严格budget匹配效率研究；Environment/Memory虽实现但未独立消融；版本/回滚提供可审计性，不构成对齐或真实世界安全的形式化保证。附录反射伪码（p25）的safe/non-degrading依赖Accept判定的正确性，不能由协议语法自动推出。
- 资源：开源当前框架已大幅发展，README安装脚本会装Python3.12/Node，整框架在Docker中、bind-mount源码，且挂Docker socket以启动sibling容器；这不是不可信自修改代码的强隔离。当前README有不需API的默认非integration pytest；真实任务需要模型key，GAIA/HLE还需网页、浏览器等外部资源。
- 无付费最小实验（建议）：先只测注册/版本/rollback：5种资源各建v0、允许修改1种、故意失败一次并确认原状态恢复；测试评测器不可写及并发访问一致性。第二阶段可用本地模型在10个字符串/算术小任务上对比固定prompt、prompt-only、solution-only、joint，固定3轮和相同总生成token。此能检验协议与迭代收益，不能声称重现GAIA。不要运行默认全权限Docker-socket架构处理敏感目录。

## 5 AEvo

- 完整题名：Harnessing Agentic Evolution。Jiayi Zhang 等；arXiv:2605.13821v1，2026-05-13。[全文](https://arxiv.org/pdf/2605.13821v1)。[官方占位仓库](https://github.com/FoundationAgents/Harnessing-Agentic-Evolution)，[另一官方仓库](https://github.com/FoundationAgents/AEvo)。核验时前者只有README/LICENSE，后者为空，不能写“已提供可运行开源代码”。
- 方法（§3–4，pp3–6）：把搜索过程本身看作环境。状态是累积候选/反馈/轨迹/失败/成本；meta-agent的动作修改下一段搜索机制（选择规则、变异/提示、memory、工具、停止策略），不是直接生成下一个解。Procedure variant改显式演化程序，Agent variant改内层coding agent运行context。独立harness维护轮数/记录并保护hidden evaluator，meta-agent分段介入。
- 设置（§5与附录B/C）：GPT5.4/Codex与Opus4.7/Claude Code作为优化接口；标准任务执行Gemini3Flash；temperature1、high、128K，标准任务20轮、开放任务100轮/25轮无改进早停。标准bench Avg@3，开放任务Best@3，不可混称“平均”。
- 表2 p7：Terminal-Bench ReAct28.6，DGM/AFlow44.3（最强baseline），AEvo53.8；ARC-AGI-2 ReAct21.8、ADAS36.0（最强baseline）、AEvo47.0。两者相对提升21.4%、30.6%，均值约26%；不是+26pp。正文明确每轮优化成本约procedure基线3倍，因此“相同轮数”不是“相同总算力/美元”。正文/附录未清楚披露这两套数据的版本、完整题数及search/test划分，报告不能擅自补成完整TB2/完整ARC test。
- 表1 p7：circle_packing_26 best sum radii2.6359，多方法同分；AC2 Opus Agent0.9459 vs Claude Code0.9438；模拟VLIW/SIMD kernel GPT5.4 Agent1138cycles vs Codex1667、ClaudeCode1615；100→200轮可1121（图3 p8）。这是模拟器cycle，不是实际GPU内核吞吐。GPT5.4 AEvo每轮成本$1.23；此是论文当时API口径，不是实时价格。
- 消融（表3 p13）：无meta-skill三run最优2379/1536/1407cycles且有提前停止；无harness三run之一1167有效，另外两run reward hack导致N/A。完整1138是主表最佳口径，消融样本很小；支持保护评测器重要，不证明一般攻击下安全。
- 局限：无完整代码/数据切分和成本匹配控制；Best@3强调可达上限而非稳定期望；更强优化推理与框架的贡献仍混合。作者建议更多环境、更低成本meta intervention与安全部署；不是“自修改机制已经无限递归加速”的证据。
- 无付费最小实验（建议）：不用缺失官方实现，从论文接口做透明复刻：仅优化简单字符串匹配算法或8圆packing；独立只读评分器；固定20候选预算，对比固定best-parent变异与每5轮允许meta-agent改选择/搜索温度。同一本地模型，总生成token与评估调用均匹配，3种子，记录best-so-far/无效候选/提前停止/篡改评分尝试。无模型可用时用预置调度策略测试治理边界，不能标为agent性能复现。

## 6 Huxley-Gödel Machine

- 完整题名：Huxley-Gödel Machine: Human-Level Coding Agent Development by an Approximation of the Optimal Self-Improving Machine。Wenyi Wang、Piotr Piękos等；arXiv:2510.21614v3，2025-10-29。[固定版全文](https://arxiv.org/pdf/2510.21614v3)；[官方代码](https://github.com/metauto-ai/HGM)。仓库说明ICLR2026 oral；论文版本日期与会议年份分开。
- 核心问题（§1–3，pp2–7）：当前agent解题强，不必然更会生成更好的子agent，称metaproductivity–performance mismatch。CMP衡量某祖先整个后代分支未来可达的优良结果；实际用clade所有已观察成功/失败聚合估计，Thompson sampling挑待扩展父节点。扩展与评估解耦，按单agent–task粒度评估，以类似无限臂bandit规则决定生成新agent或继续测旧agent，异步利用并发。基础模型不训练，搜索agent源码/工具/prompt。
- 理论边界（Assumption1/Theorem1，p5）：真CMP oracle足以模拟本文受限Gödel Machine接受机制，前提是只关心最终agent效用、可重复独立评估、证明不消耗预算、每次修改固定成本1。实际估计CMP不是真oracle；“有定理”不代表实际HGM保证全局最优，更不等于通用自我改进安全保证。
- 实验：SWE-Verified-60搜索GPT5扩展/GPT5-mini评估；Polyglot扩展Qwen3Coder480B-A35B（int4/int8混合）、评估30B-A3B。相同DGM祖先，最多800次task evaluation，HGM α0.6；表1 p8 weighted Pearson相关SWE0.778 vs DGM0.285/SICA0.444，Polyglot0.626 vs0.383/0.274。相关是完成树上的经验CMP，经去除目标分支处理；仍非对任意未来搜索分布的保证。
- 表2 p9：SWE60：初始40%，HGM56.7%、DGM53.3%、SICA50.0%；HGM517 allocated CPU-hours vs DGM1231（2.38倍），SICA360次后反复上下文错误。Polyglot：初始20.3%，HGM30.5/347 CPUh、DGM27.1/2385、SICA25.4/572。CPU-hour含分配资源与异步利用，不等于总LLM token、GPU-hour或实际墙钟同倍加速。
- Full SWE-Verified500题（§4.3.1 p9）：调整更强祖先53.2%，8000次评估后61.4%。这是在同benchmark优化的成绩，不应独立泛化解读。
- 真正去重迁移（表3/4 p10）：SWE-Lite300题与Verified重合93题，作者另报207题filtered。GPT5-mini HGM filtered40.1 vs祖先34.8、SWE-agent39.6；standard49.0 vs44.0/47.6。换GPT5后HGM filtered47.8 vs SWE-agent48.3；standard57.0 vs56.7。因此标题“Human-Level”指接近人写agent系统排行榜，不是与人类程序员同场实测，也非去重集明显胜出。
- 资源（附录C p18）：初步每次执行限1h，full阶段自修改/评估限5h；所有方法实验总支出约$5000。开源Apache2仓库含外循环、树、best_agent、Docker、SWE/Polyglot接口，Python3.10；主实验依赖GPT API或480B级模型。README明示运行不可信模型生成代码风险。
- 无付费最小实验（建议）：最先做纯CPU的固定合成树搜索，设置一些“当前差但后代好”分支，比较greedy、node-level Thompson、clade-level Thompson；同800次伯努利评估预算，至少30随机种子，报告最终最佳真成功率/置信区间。它直接检验选择策略，不需LLM也不执行第三方代码，但只验证算法机制。下一步再用本地模型在10个小代码题生成20个受限候选，锁定额外测试，证明源码自改时是否仍有收益；不能把合成树结果当SWE复现。

## 7 JIT-Agent

- 完整题名：JIT-Agent: Scaling Harness Intelligence via Just-in-Time Harness Evolution。Guibin Zhang等/JIT-Agent Team；arXiv:2608.25593v2，2026-09-03（v1 8月26日）。[原文](https://arxiv.org/pdf/2608.25593v2)；[代码](https://github.com/bingreeky/JIT)；[公开27B模型](https://huggingface.co/JIT-Agent/jit-27b)。与JITRL不是同一篇、也不是同一学习对象。
- 方法（§3–4，pp4–7）：把harness严格分为M记忆、P规划、A动作、F能力编排，运行依赖次序M→P→F→A。HarnessFactory统一重实现13种人工scaffold作为种子库。训练基于Qwen3.6-27B的生成器，收到任务、协议、工具注册表及近邻harness参考，直接输出可执行模块。
- 三阶段训练：I强教师生成/验证task-adapted harness，SFT+按reward/latency/cost优势加权DPO；II对失败harness及编译/接口/运行错误，模仿至多两轮成功repair；III Evo-GDPO比较组内候选与archive incumbent，独立归一化reward/延迟/费用通道，reward权重主导，PPO+KL到II检查点。部署时生成器权重冻结，static生成N个选1个执行，streaming将通过前沿条件的harness经验留入archive。因此“测试时自演化”主要是外部archive/生成产物变化，不能说每题在线更新生成器权重。
- 表2 p8的9基准分数都是0–100但语义不同（QA、约束满足、workspace成功等），平均是便于概览的宏均值。GLM5.2平均74.1→81.8（+7.7），DeepSeekV4Flash66.7→75.5（+8.8）；GLM Travel62.8→83.0（+20.2），DeepSeek Shop59.1→83.9（+24.8）。DeepSeek+JIT DSQA85.1 vs GPT5.6 76.0，Odyssey73.0 vs68.7，摘要比较的是这两个特定benchmark，不是全面超过GPT。
- 固定backbone更有解释力（表3 p8）：DeepSeek xBench JIT82.0/212K/$0.039 vs NanoBot78.0/527K/$0.075；DSQA JIT85.1/400K/$0.066 vs最强fixed NanoBot80.4/924K/$0.131。但DeepSeek AgentIF JIT63.8低于ClaudeCode66.9；Qwen3.6Flash DSQA JIT70.3低于NanoBot74.2。JIT在6设置里4个性能最高、6个token/费用最低，不是全面dominance。图4 p9另用DSQA100例、其他三基准各50例，不能混合为表2主测试规模。
- 复现缺口/推断：论文未充分给出训练数据规模、学习率/epoch、教师确切配置、GPU训练预算、主表多seed方差及完整数据切分；需要代码/作者配置补足。训练集来自既有agent benchmarks+合成任务，泛化声明需注意训练/测试污染控制资料不足。也要确认表中成本是否完整含候选生成、修复、选择及judge，不能仅按executor token推定端到端全部节省。
- 代码与权重状态：当前Python3.11仓库有harness_factory、jit、benchmark adapters、dataset、HTTP执行与judge接口；所有数据约1GB，模型服务需自备vLLM/SGLang。官方模型卡明确公开checkpoint是“Stage-I模型再蒸馏最终research checkpoint”的initial research release，并非原最终研究checkpoint。模型27.36B、BF16、建议163,840上下文、TP=4；权重本身理论约54.7GB（27.36B×2字节，推算），还未计KV/runtime，普通单卡直接full-context不现实。
- 无付费最小实验（建议）：先用固定seed harness跑5个离线文件/字符串任务，检查四模块protocol和最多2轮repair；再以已部署本地模型替代meta与executor，不用网页/Serper/Jina，候选N=1/3，固定同一批任务，记录编译通过率、repair成功率、最终正确率和包含所有角色的总token/时间。低资源可只评测已经生成的harness并用mock executor验证schema，称“协议与恢复烟测”。要检验论文JIT-27B能力应部署公开27B并承认它是蒸馏公开版；重训三阶段不适合作为首次本地项目。

## 8 EvoTest

- 完整题名：EvoTest: Evolutionary Test-Time Learning for Self-Improving Agentic Systems。Yufei He等；arXiv:2510.13220v2，2026-04-17，ICLR2026论文，37页。[全文](https://arxiv.org/pdf/2510.13220v2)；[ICLR poster](https://iclr.cc/virtual/2026/poster/10010217)；[官方代码](https://github.com/yf-he/EvoTest)。不是仅会议海报摘要，已有全文。
- 方法（§3–4，pp4–6）：J-TTL在同一Jericho文字游戏重复K个episode，每次重置到相同初始状态。Actor完成一局后，Evolver读完整叙述轨迹，改policy prompt、成功/失败记忆、温度/探索等超参，以及Python状态抽取/记忆访问routine；用UCB从父配置和子配置选择下一局。基础actor无梯度更新，利用叙述反馈作语义归因。
- 设置：Detective、Library、Zork1、Zork3、Balances、Temple共6游戏；每局110步、50局。Actor Gemini2.5Flash或Claude4Sonnet，Evolver o3-2025-04-16；SFT/GRPO主比较用Qwen3-32B，不能说主表全方法同底座。主要指标AUC=各局累计得分/(K×游戏最大分)，是学习过程归一化平均分，不是ROC-AUC或成功率。
- 表1 p7：Gemini平均EvoTest0.47 vs最强prompt0.34、Reflexion0.32、GRPO0.30、Static0.11；Claude0.50 vsprompt0.36。摘要38%与57%分别是0.47相对0.34与0.30的比例。Detective/Library可获胜；其他游戏AUC仍低，例如Zork1 0.14/0.16，不是所有游戏已掌握。
- 消融与同模型控制：表3 p9 Detective完整0.94，去prompt0.52、去UCB0.68、去memory0.82、去超参0.89、去tool-use0.91。表5 p10通用“改好一点”mutation仅0.65，结构化多部分evolver prompt重要。表6 p10同Qwen3-32B actor：SFT平均0.24、GRPO0.31、Qwen3-32B evolver0.35、o3 evolver0.40，支持方法有效，也显示强优化模型额外贡献。
- 多seed：表8 p22 Gemini五种子完整平均0.48±0.01，Promptbreeder/EvoPrompt0.35±0.03、GRPO0.31±0.03。表8 Memory行Detective0.56但给的六游戏平均0.13，逐项算应约0.183，疑似表格笔误；不自行改原数，也不引用此行做精确结论。
- 成本（表2 p9、附录C p17）：每次更新EvoTest1模型调用约20–30秒 vs SFT/GRPO 4×H100上5–10分钟；这只是更新步骤时间，不含整个50×110步actor消耗，不能声称整轮仅几十秒或免费。
- 局限（附录A pp16–17，作者明确承认）：固定底座能力天花板、单任务策略性过拟合、挪动钥匙等细微变化可能失效、依赖强且可能昂贵evolver、简单1+m/UCB也可局部最优。这里只证明反复玩同游戏学得更好，不是任务分布迁移或无限持续学习。
- 代码：官方仓库有Jericho游戏目录、actor/evolver与若干memory/summary/RAG基线，默认通过OpenRouter，需检查论文全baseline和完整日志是否均可用，不把承诺等同已核实全量发行。运行状态extractor涉及模型生成Python，需隔离。Jericho引擎不需GPU；主实验o3/actor仍收费；同Qwen32B版本有论文证据可作为无API方向，但需要本地显存。
- 无付费最小实验（建议）：一个可合法使用的Detective/自建IF小环境，10局×50步，3种子；本地同一模型担任actor/evolver，对比Static、prompt-only、完整+UCB，记录每局score、AUC、调用/token和可执行状态抽取失败率。另将钥匙位置/门规则更换作小型迁移测试。达到更高AUC才是学习证据，简单“程序跑通”仅烟测；原50局110步六游戏结果需更大预算。

## 9 Cordis

- 完整题名：A Programming Paradigm for Spatiotemporal Composability。Yifan Shi、Wei Zhang、Tianyi Cui；arXiv:2608.25512v1，2026-08-26，92页。[全文](https://arxiv.org/pdf/2608.25512v1)；[论文仓库](https://github.com/cordiverse/paper)；[实现](https://github.com/cordiverse/cordis)。论文仓库现在只保留README并指向arXiv，不是找不到原文。核查重点为定义/关键定理前提、实现对应、案例与讨论；未对92页证明做机器形式验证。
- 类型区别：这是编程语言/运行时论文。它不训练模型，不报告agent pass@1，不存在可与Meta-Harness放同一个性能榜的“提升百分比”。agent self-evolution是应用动机之一。
- 核心（§3–4）：时间可组合性要求卸载组件后撤回其受管理副作用；空间可组合性要求依赖动态出现/消失时组件按声明自动启停。revertible effects把变更和inverse配对，runtime按LIFO组合；reactive coeffects把依赖变化归类为激活/失活/保持；统一Context中介访问，组件fiber管理生命周期、嵌套和provider/consumer顺序。以观察等价而非物理状态完全相同表达独立性。
- 正式证据：Theorem68 recovery exactness p46/Corollary69 p47说明退回组件贡献并保留其他合法交错；Theorem70 ordering p47在依赖存在时激活、consumer先于provider撤回；Theorem71 resolution coherence p48约束激活中绑定一致性。Theorem73 progress p49需要依赖关系无环、effect长度有界、出现fiber集合有限。Confluence是满足规定的终态一致性，不是任何外部事件序列可交换。
- 实现（§5，pp57–69）：TypeScript core的ctx.effect、get/set、isolate/intercept、use及loader；表2 p58是理论→实现映射，表1是语义规则，不是benchmark。loader支持配置reconcile、热模块替换、失败后恢复旧模块缓存；版本脚注p69明确论文讲Cordis v4，而Koishi案例使用v3。
- 工程案例（§5.3 pp69–70）：Koishi四年约4000+社区插件，服务端bot和浏览器console皆可用同范式；能独立卸载/热更组件而保留其他连接/状态。作者明确这是单生态、单语言、观察性“存在与采用”证据，未做对照的性能overhead/开发生产率评估。
- 必须保留的边界：p59逆操作是否真能还原、coeffect操作是否满足交换性，是组件作者义务，runtime不验证。§6.1 pp70–71界定可独占且可恢复才在系统边界内；已发送消息等外部emission不能撤销。§6.3 pp72–73：语言代理只是访问约束，不是恶意代码sandbox，仍需进程/容器等外部边界。循环依赖可能永久inactive；独立包接口漂移、版本兼容与key冲突仍是开放工程问题（pp74–75）。所以“随意改任意代码安全回滚”不是论文结论。
- 复现资源：MIT TypeScript实现，当前workspace用Yarn4.14.1、Vitest测试、TS5.9.3；无需模型、GPU或数据集。生产v3与研究v4须锁版本。研究项目的Node HMR可能使用engine internal接口，不能宣称任意JS runtime完全兼容。
- 无付费最小实验（最可行）：3组件A供logger、B依赖logger注册listener/timer、C独立计数；加载B但A缺失时B不激活；加载A后B激活；卸A须先清B，C不中断；重装A/热更B后重复100轮，断言listener/timer/注册数无增长、dispose幂等、终态与静态直接装配一致；再注入错误inverse，验证框架本身不能神奇修复作者错误。全部纯CPU。这是比任何模型跑分更贴切的论文复现。

## 10 SoL-Pi

- 完整论文题名：SoL-Pi: Recursively Scaling Auto-Research Loops for Efficient Agent Harness。Haozhe Liu等；arXiv:2609.20519v1，2026-09-17，15页，PDF内日期2026-08-17。[论文](https://arxiv.org/pdf/2609.20519v1)；[项目](https://nvlabs.github.io/SoL-Pi/)；[代码](https://github.com/NVlabs/SoL-Pi)。项目标题为Scaling Auto-Research Loops for Efficient Agent Harnesses，与论文标题略异；视频说“尚无arXiv”已被当前发布状态更新。
- 研究设计（§2 pp2–5）：固定能力容忍门槛后探索效率改动；152个方向、535个开发环境（495真实issue–PR任务+40可执行合成verifier）、3000+run/60000+交互。独立实现/审查/验证的宽→深搜索保留4个机制；候选冻结后再独立验证，失败不把heldout反馈返给搜索。这里没有学模型权重，也没有已证明的搜索scaling law。
- 四机制：Action Fusion把edit/write与可预定的后续测试合成一个tool call；Online Context Compact在plan步骤完成时按剩余调用/上下文增长/cache重写成本决定压缩；ObservationPack对&gt;10KiB大输出前2次完整发送，第3次起稳定handle+约1KiB头尾摘要，支持精确分页召回；Evidence-Preserving Reducer把≥4KiB指定build/test日志交小模型提取receipt，以schema/hash/exit status/逐字引文/大小验证，失败或疑似凭据则退回原文。原论文辅助模型GPT5.6Luna high。压缩cost gate不单独给摘要调用计价（§2.5）。
- 数据划分（p6）：EdgeBench51公开任务中11用于冻结候选单向acceptance，40用于最终泛化；主表给51的汇总。作者说隔离搜索，但11题用于接受决定不能等同从未接触的40题；应要求40题单独报告及容忍阈值配置以更严格评估。不可将51称完全未参与选择。
- 精确结果（表1 p6/表2 p7）：GPT5.6Sol上Pi44.833平均分/2.1538B token/$1339；完整SoL-Pi Efficiency42.003/1.0990B/$894，即token-49.0%、费用-33.2%，分数下降约6.3%。Opus5 Pi44.756/2.3697B/$1741→42.224/1.3101B/$1158，token-44.7%、费用-33.5%、分数约-5.7%。故“相近能力的效率权衡”准确，“无损省一半token”不准确。
- Performance配置不是完整四机制：表4 p9按模型挑最高分单组件，Sol选ObservationPack47.208（+5.3%相对），Opus选ActionFusion50.482（+12.8%）。它与Efficiency是两个operating points，不能把最高分和最大节省拼成同一次运行结果；按结果选最优单组件也存在winner-selection乐观偏差。
- 其他验证（表3 p7）：TB4仅63个CPU任务，Pi18题/$286.45，SoL15题/$211.12，便宜但少解3题；IMO2026六题Lean4验证，SoL3题/$62.69、Pi3题/$75.95、Codex5题/$114.47。不同题覆盖不能只比cost/pass宣称绝对更好。
- 群体（§3.3/图5 pp7–8）：每配置仅一次2h run；Codex coordinator+20 Luna worker SoL1127模拟cycles/$60.11，Pi swarm1366/$82.12，单Codex1333/$39.20。SoL swarm相对Pi更好，但不是比单agent更便宜；没有多seed方差。所有费用采用2026-08-17 API价格，不是当前报价；每小时节省只是该评估设置的折算。
- 局限（§5.1 p12）：只有单开发backend与一个额外backend迁移；完整搜索昂贵，未在固定budget下验证breadth/depth因果；把节省重新投入下一代搜索的“recursive efficient improvement”明确是长期愿景，未展示复利。机制效果会相互干扰、缓存收益取决于provider与任务结构，token traffic含cache重复流量不等于unique reasoning token。
- 开源资源：MIT Pi extension，Node≥22.19、npm、Pi coding-agent0.85.1；四机制默认关闭、opt-in；有源码检查/测试。原始轨迹会本地长期存档，no-session也会写临时archive；Reducer可能把日志发给其配置的模型，需敏感数据边界。代码开源不等于535环境/152方向完整研究过程都已完整发行。
- 无付费最小实验（优先推荐）：先只重放人工构造日志测试ObservationPack：前2次全量、第3次handle、精确分页取回、hash一致、边界字符/截断无丢失；测100次上下文发送总字节/token与召回正确率。ActionFusion用临时小repo的edit+本地unit test验证返回顺序/失败不掩盖。两项完全不额外调用模型。若已有本地agent，再做10–20题paired pilot比较baseline/两模块/full，记录正确率、端到端所有角色token/耗时与缓存；单次pilot不能复现paper置信结论。Reducer先mock回执与坏hash/伪引文拒绝测试，未经批准不把日志发远端。

## 综合判断与复现顺序

这些工作分属不同层级，不能用一个“自进化提升”名词混合：Cordis解决运行时生命周期，Autogenesis规定资源与更新接口，HGM优化搜索选择，Meta-Harness/AHE改执行harness，AEvo改搜索机制，JIT-Agent训练按题生成器，EvoTest跨重复episode改配置，Continual Harness同episode中改配置，SoL-Pi发现并发布效率机制。

低资源优先顺序（分析建议）：1. Cordis生命周期测试；2. SoL-Pi ObservationPack/ActionFusion的确定性测试；3. HGM合成树调度；4. Meta-Harness分类或EvoTest小IF的本地模型pilot；5. AHE小代码任务与manifest回归预测；6. Autogenesis最小协议；7. AEvo重实现；8. JIT-27B部署/Continual Harness共同训练。排序依据是能否在不付费、不依赖缺失代码/商业ROM、不购买大GPU条件下验证核心机制，不表示论文科学价值高低。

共用验收：源码/论文固定版本；外部评分器与测试集不可修改；区分机制测试、缩小复现、原论文数值复现；固定总评估次数之外还记录全部模型调用与token；报告失败/回归，不只best-of-N；保留独立测试和至少3种子（廉价仿真可30种子）；所有模型生成代码先隔离与审查，禁止自改评测器/权限/密钥/网络边界。
