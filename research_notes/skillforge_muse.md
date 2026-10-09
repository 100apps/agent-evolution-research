# 四篇技能演化论文核查

核查时间：2026-10-08。基于完整原始 PDF，必要时交叉检查 arXiv HTML、作者官方代码与基准仓库；未执行第三方代码。页码为 PDF 页码；SAGE 同时给会议页码。下述“作者结果”均为论文报告，非独立复现。“判断/建议”是分析者推断。

## 1. MUSE-Autoskill

- 原文：[arXiv v2](https://arxiv.org/abs/2605.27366v2)；[PDF](https://arxiv.org/pdf/2605.27366v2)；[HTML](https://arxiv.org/html/2605.27366v2)。2026-07-03 修订；30 页；arXiv 标记 Under Review。必须使用 v2：v1 的 51 任务、87.94% 等数字已被修订。
- 问题与方法（§3，pp.5–9）：将技能作为持久资产管理：ReAct 内部生成 SKILL.md/可选代码与测试、登记与检索、失败后修补、每技能经验记录、长期记忆、两级上下文压缩。无需权重训练。文本技能可以只靠执行与轨迹反馈验证，并非每个技能都包含单测。
- 作者结果（Table 2，p.10；Table 4，p.11）：统一 GPT-5.5 后端，SkillsBench 可被四个运行时共同执行的 75 任务，各跑 5 次。MUSE 无技能 46.95%，人工技能 59.67%，自生成 53.42%；自生成对照 Codex 47.52%、Claude Code 44.27%。自生成覆盖 47/75，未覆盖计零。85.24% 对 81.17% 的“胜过人工技能”仅限这 47 个成功覆盖任务，不能替代全任务结论。独立 SkillLearnBench 的 100 实例各跑一次，MUSE 43/72/48%（无/人工/自生成）。
- 作者结果（Table 5，p.12）：转给 Hermes，MUSE 技能 51.90%，Hermes 无技能 37.24%、人工技能 48.02%；只验证了流入 Hermes 这个目标运行时。
- 作者结果（Table 7，p.14，已视觉核对）：50 个生成包覆盖 47 任务；90% 只有 SKILL.md，8% 带 scripts，8% 带 tests。不能把工程设计中的测试能力写成“全部生成技能通过单测”。
- 作者结果（Appendix F/Table 11，pp.26–27）：另设人类技能、两轮 verifier-feedback 实验；记忆系统关闭/开启第二轮 60/74%，第一轮 48/64%。开启时按任务顺序在实例间积累记忆；该协议不同于主表。判断：支持整个记忆系统在重复任务中的价值，不能单独证明每技能记忆这一组件、也不能与主表拼接比较。
- 成本（Table 6，p.13）：MUSE 覆盖子集的一次技能生成中位数约 364K tokens/156.3 秒；每次复用 499K/434.7 秒，人工技能 638K/755.7 秒。作者估计约三次复用摊平生成 token 成本。未披露可复现实验总美元价或本地 GPU 配置；token 日志跨运行时不完整，不能据此给出统一成本排名。表内 one-time generation 也不应被理解为整个发现与评测项目总成本。
- 公平性/泄漏边界：作者承认在同一任务成功轨迹上蒸馏，再在同一任务重跑可能高估收益（Limitations，p.17）；75/94 任务筛选排除了部分复杂容器任务；仅五次运行。作者人工审计未发现硬编码答案/读取真值，但部分技能保留固定路径、数值范围等特定假设（§4.6）；HVAC 有 80%→20% 退化个案（p.13）。判断：同后端排除了模型差异，但提示、工具、压缩、技能处理仍同时变化，主表不是各模块因果消融；成功覆盖子集选择效应明显。
- 开源核验：全文/摘要未给作者官方实现或生成技能库链接，检索未验证到官方仓库。[Akshay2695/muse_autoskill](https://github.com/Akshay2695/muse_autoskill) 的 README 是 GPT-4o 工程实现，不能作为论文 GPT-5.5 系统的官方复现证据。[SkillsBench](https://github.com/benchflow-ai/skillsbench) 和 [SkillLearnBench](https://github.com/cxcscmu/SkillLearnBench) 基准公开；当前基准版本可能已改变，应锁版本与 75 任务清单。
- 无付费 API 本地复现判断：原数复现受闭源 GPT-5.5 和未验证官方实现阻碍；机制复现可行。用本地开放模型、5–10 个无需外部凭据的文件/表格任务，先比较无技能、成功轨迹蒸馏、蒸馏+记忆。必须另造同分布新实例与变更路径/数值的留出实例，避免只证明“同题再做”。固定模型、预算、提示；同时报告全任务成绩与覆盖率。此为建议方案，未运行。

## 2. SkillForge

- 原文：[arXiv v2](https://arxiv.org/abs/2604.08618v2)；[PDF](https://arxiv.org/pdf/2604.08618v2)；[HTML](https://arxiv.org/html/2604.08618v2)。2026-04-29 修订；下载 PDF 实为 19 页，摘要 comments 仍写 18 页/3 表；作者标明 SIGIR 2026 Industry Track accepted，关联 DOI [10.1145/3805712.3808466](https://doi.org/10.1145/3805712.3808466)。
- 问题与方法（§2，pp.2–5；App. A/E）：云客服技能缺少业务依据，也缺少从失败定位技能缺陷的闭环。用历史工单挖掘流程/工具/知识，生成技能；四维 Failure Analyzer（知识、工具、澄清、风格）→聚合→Diagnostician 定位文件段落→Optimizer 最小增量修改并版本化。技能只有说明/参考资料与已验证工具 schema，不允许运行任意脚本；生产回答由客服人员审核。
- 作者结果（Table 1，p.5）：账户、域名、DNS、OSS、ECS 五场景，共 1,883 工单/3,737 单轮任务。v2 明确各场景按工单时间排序，四个各约 25% 分片：前三片依次供三轮演化，第四片留出评测，避免同工单轮次跨集合。评分是 LLM-judge 与历史专家答案/最终工单结局的一致性 CR，不是用户问题实际解决率。
- 作者结果（Table 2，p.6）：Domain vs Generic 的 Strict CR 五场景为 64.0/60.5/65.4/62.5/50.6%，Generic 为 58.0/57.9/63.0/59.1/43.4%，平均 +4.3pp；Lenient +3.6pp。每次离线评测重复三次报均值。
- 作者结果（Table 3，p.6）：三轮后，相对各自初始技能，manual/domain/generic 的 Strict CR 分别 +10.99/+9.23/+11.60pp；Lenient +12.21/+8.00/+4.90pp。§3.4（p.7）报告 v3 对 legacy 系统 +13.76pp Strict CR，但未提供该段完整绝对分数、区间或等预算表。
- 公平性判断：Generic creator 是 Claude Code+Claude-Sonnet-4.5，只得到挖掘的工具 schema，被禁止读领域知识与工单；Domain creator 是内部 Qwen3-Max，能读这些资料。因此初始 +4.3pp 混合了知识访问、模型和流程差异，不能视为领域生成算法的干净消融。主体执行用 Qwen3-Max，未固定可复现快照；没有去掉 Analyzer/Diagnostician/Optimizer 的组件消融。虽声明评测工单未用于演化，初始化知识与历史工单挖掘是否同样严格排除全部留出内容，文字尚不够明确，需作者确认，不能直接指控泄漏。
- 评分与外推限制：judge 接收整个工单最终结局作离线判分依据（App. D，pp.14–15）；允许合理替代方案，但还把风格、转人工、揭示 AI 身份等产品规则纳入评价。作者仅称与两专家共识 &gt;90% 一致，未报样本数/混淆矩阵；不能当通用技术正确性指标。§3.3.2 承认知识失败在第一轮后平台化、历史专家回答矛盾及隐性经验缺失，不能推论无限自我提升。没有显著性区间。
- 开源/成本核验：全文、摘要和针对作者/阿里域的检索未验证到官方代码、脱敏工单或初始/演化技能集；不要把其他同名 SkillForge 仓库算作本论文开源。没有 token、美元、延迟或 GPU 总预算；内部 Qwen3-Max 与私有业务工具不可作为免费可复制依赖。
- 无付费 API 本地复现判断：只能方法级迁移，不能重现论文数值。以公开软件项目 FAQ/issue 构造可分享的支持问答，用本地模型承担 Creator/四维 Analyzer/Diagnostician/Optimizer；以固定文档快照、模拟只读工具和人工小样本验证评分。按工单/时间切分，在初始化前完成划分，另设“相同模型+相同领域资料”的 generic baseline，控制预算。重点验证三阶段诊断是否优于一次直接反思改写。

## 3. WikiSkill

- 原文：[arXiv v1](https://arxiv.org/abs/2608.27454v1)；[PDF](https://arxiv.org/pdf/2608.27454v1)；[HTML](https://arxiv.org/html/2608.27454v1)。2026-08-27；28 页，Google Research/Virginia Tech；未核验到正式录用记录。
- 方法（§3，pp.4–6）：把不可改写的执行轨迹、持续演化 wiki、可执行技能分成三层。Maintainer 汇总成功/失败模式；Proposer 每轮提出一个新增或修改技能的候选；验证集严格提升才接受，失败仅回滚技能，wiki 连失败提案/差分也保留。任务执行器只能得到技能，不能读 wiki；全部技能直接放进 prompt，实验不测试检索路由。附录给算法与角色 prompt。
- 作者结果（Table 1，p.8，已视觉核对）：五基准、五模型；每种方法完整演化重复三次，paired bootstrap 1,000 次。五基准等权平均，无技能→WikiSkill：Qwen3.5-4B 26.2→38.5%，9B 29.9→47.4%，Qwen3.6-27B 39.4→63.3%，Gemma4-31B 41.3→54.9%，Gemini3.5-Flash 49.5→68.1%。各模型的最佳其他技能演化 baseline 平均分分别 35.2/42.3/53.3/49.1/56.1%。这些是百分点提升，不是相对百分比。
- 作者结果（Table 3，p.11）：Gemini 四基准均值，Proposer 可读 wiki、执行器不读为 63.7%；无 wiki 与 Maintainer 为 48.7%；执行器也能读 wiki 则 60.9%。支持“将经验编译成技能”的隔离设计，但移除 wiki 时还同时移除 Maintainer，不是单一存储格式消融。
- 正反迁移（Table 2，p.10）：27B 技能给 9B 的表格任务 50.5%，高于 9B 自己技能 33.6%/无技能24.3%；但 4B 技能给 Gemini 的表格成绩 50.5→18.1%，表明模型专用补丁可有害。4B 本身 OfficeQA 30.2→28.5% 也退化；不能写“所有任务都提升”。
- 数据协议（Table 6/App. B，p.20）：train/val/test 数量：LiveMath 35/18/124；SealQA 16/10/85；SpreadsheetBench 80/40/280；OfficeQA 50/24/172；ALFWorld 39/18/134。OfficeQA 提供预解析 oracle 参考页，故不是从原始全集独立检索的完整难度；SealQA 使用 Google Search API（2026-07 数据）。
- 公平性/泄漏判断：有不交叉 train/val/test，强于同题蒸馏再测；但反复使用 10–40 条的小验证集有选择过拟合/噪声，作者已承认。全文未给足以独立确认所有基准近重复清理的材料；不能据此宣布完全无污染。优化器调用未等成本；4B/9B 属于 Qwen3.5，27B 为 Qwen3.6，“规模趋势”同时含模型代际差异。推理能否访问 wiki 的消融与主要结果协议需保持一致。
- 成本与局限（App. C/D，pp.21–23）：每轮 Maintainer 最多采样 8 条轨迹（5 失败/3 成功），各截 15K 字符；Proposer 约 10–20 步，full-batch 优化器每轮 11–21 次调用。所谓 O(1) 仅针对优化器调用数，不包括执行所有训练/验证任务的调用或 token 总成本。未披露总 GPU 小时、实测总 token/费用；开放模型用 vLLM。有限迭代（表5按0–7轮统计），无长期 wiki 剪枝，未验证几百步/数小时任务。
- 开源核验：全文与作者/Google 域检索未验证到作者官方代码、技能快照或精确 split 清单；[kenhuangus/wikiskill](https://github.com/kenhuangus/wikiskill) 与 [poweredbyGEN/wikiskill](https://github.com/poweredbyGEN/wikiskill) 明确自称独立实现，不能冒充官方。公开 [ALFWorld](https://github.com/alfworld/alfworld) 可作为本地任务环境。
- 无付费 API 本地复现判断：四篇中适合优先做轻量机制实验的一篇。用本地4B/9B、数学客观判分或少量离线表格任务，不选需要 Google Search 的 SealQA；按三个集合隔离，比较无技能/无wiki的技能改写/持久wiki/每轮清空wiki，并记录失败提案保留是否有帮助。精确权重、量化、上下文上限须依硬件验证；不承诺普通机器可完整重跑。缺官方实现时标注“独立机制复现”。

## 4. SAGE: Reinforcement Learning for Self-Improving Agent with Skill Library

- 原文：[ACL 2026 正式页面](https://aclanthology.org/2026.acl-long.69/)；[PDF](https://aclanthology.org/2026.acl-long.69.pdf)。ACL 2026 long paper，pp.1529–1550（PDF 22页）；对应早期 arXiv 2512.17102，不应误列成与2026首发方法同一时间。
- 方法（§3，PDF pp.3–5/会议1531–1533）：技能是生成后立刻执行并保存的 Python 函数；两任务 Sequential Rollout，让前题产生的函数供后题复用。基于 GRPO，加上同时鼓励前题生成和后题成功调用的 skill-integrated reward；完整参数 RL，前置专家轨迹 SFT。区别于前三篇，不是纯推理时文本记忆。
- 作者结果（Table 1，PDF p.7/1535）：Qwen2.5-32B-Instruct。Test-Normal：GRPO TGC/SGC=69.2/51.8%，SAGE=72.0/60.7%；步骤16.4→12.1，输出tokens3613→1475。8.9 是 SGC 的百分点；26%/59% 是相对该 GRPO 的下降。Test-Challenge TGC/SGC=40.7/26.9→50.1/32.4%。三次评测同一训练后模型，并非三次独立RL训练。
- 关键消融（Tables 2/5/7，PDF pp.8–9）：SAGE有/无技能 SGC60.7/54.8%，TGC72.0/71.4%；技能主要改善连续场景全部完成及效率。只用 outcome reward SGC55.4，对照完整60.7。控制SFT后，SFT+GRPO TGC66.1/SGC51.2、tokens1284；SAGE更准，但tokens1475反而更多。因此“更准且少59%token”不适用于所有公平基线。
- 作者对检索/任务链的检验（Tables 3/4，PDF pp.8–9）：默认同场景标签检索理想化；N-gram检索SGC60.1接近60.7；相似度构造任务链SGC62.5接近/略高默认60.7。三题链比两题链更差（Table8，PDF p.14：SGC54.8 vs60.7），不能认定链越长越好。
- 数据与外推：AppWorld模拟9个app/457 API，750任务：Train105、Dev60、TestNormal168、TestChallenge417；TestChallenge含训练未见app API。默认同一场景的三道测试题顺序做，前题技能供后题复用，这是有意的在线适应协议，不是逐题冷启动独立泛化。技能无报错即保存不代表语义正确。作者承认只测AppWorld，跨环境迁移未知（Limitations，PDF p.10/1538）。
- 算力/成本（App. D–F，PDF pp.14–16/1542–1544）：论文训练采用4个8×H100节点，SFT亦32×H100；全参数训练。Claude3.5-Sonnet-V2拒绝采样产生1129条有效专家例子；上下文28048、每步输出最多1500、最多40交互步；SAGE每训练步384 rollouts，最佳checkpoint第75步。未报总GPU小时/美元。
- 代码核验：[amazon-science/SAGE](https://github.com/amazon-science/SAGE) 为论文直接链接的官方实现；2026-07-10已归档只读，CC BY-NC 4.0。README当前要求RL至少2个8×H100节点，SFT至少4个8×H100，vLLM评估1个8×A100节点；这是运行说明最低配置，别与论文实际32×H100训练混淆。修改AppWorld/LLaMA-Factory的补丁及锁定commit可见；README第二个复制补丁示例似重复指向appworld，应先静态核对。未在README验证到训练好checkpoint或专家数据下载链接；不能直接说“权重已开源”。[AppWorld官方仓库](https://github.com/StonyBrookNLP/appworld) 数据/模拟环境公开。
- 无付费API本地复现判断：不是普通本地首选。完全重现需要大规模训练及论文闭源教师数据；没有已验证checkpoint/数据交付，不能许诺零API复现原分数。可在自建小型离线函数环境和小开放模型上仅验证两任务rollout+reward机制，或用自蒸馏/RL warm-up替代教师（Table6 SGC分别53.6/55.3 vs专家SFT60.7）；这些改变必须标为降配变体，不是原实验复现。

## 综合判断（分析者）

四篇共同支持“经验需经过结构化、评测、保留/回滚才可能成为有用技能”，不支持“自动生成技能必然提高能力”。机制级本地学习顺序建议 WikiSkill → MUSE 精简生命周期 → SkillForge 同资料对照 → SAGE 两任务RL小实验。若目标是精确复现论文结论，SAGE代码证据最清楚但算力最大；SkillForge私有数据阻碍最大；MUSE与WikiSkill要先承认官方实现/精确产物未验证。任何端到端复现都应额外报告生成成本、成功覆盖率、全任务分母、新实例泛化和负迁移。

### 未确认硬件时的降配建议（分析者估算，不是论文配置）

- CPU-only/16GB 系统内存：先做一个离线、短上下文的机制演示；选择机器能运行的1–4B量化开放模型，三个角色顺序复用同一个模型进程，避免并发、网络搜索和大容器。先以10余个合成客观题/小CSV变换检查原始轨迹→知识→技能→验证回滚是否跑通，然后才扩大数据。系统内存不等于显存，不能承诺论文的4B/9B整套长上下文评测能在16GB下顺畅运行。
- 原始权重容量的理论下界：4B参数×4bit约2GB，9B约4.5GB；这不含量化元数据、未量化层、KV缓存、运行时、操作系统、文件与容器。故仅看模型文件大小不能判定可运行性，需在取得具体CPU/GPU/RAM及本地服务状态后测峰值内存和每秒tokens。
- 首轮只核对无技能/持久wiki/清空wiki三组，固定任务、随机种子和推理预算；准确率无提升也应保留失败报告。CPU推理时间没有实测，不提供“几小时跑完”的承诺。SAGE完整RL不列入此档位；即使能做小模型强化学习，也已是新的降配实验。
