# JitRL：非参数记忆驱动的测试时策略改进

核验日期：2026-10-08。依据 arXiv v4 全文（26 页）、官方仓库 README 和公开源文件静态阅读。没有运行作者代码，没有调用付费 API，也没有完成基准复现。下文明确区分论文结果、代码事实和本报告的审阅判断。

## 1. 文献信息与一句话结论

- **标题**：Just-In-Time Reinforcement Learning: Continual Learning in LLM Agents Without Gradient Updates
- **作者**：Yibo Li、Zijie Lin、Ailin Deng、Xuan Zhang、Yufei He、Shuo Ji、Tri Cao、Bryan Hooi；National University of Singapore。
- **版本**：首发 2026-01-26；本文核验版本 v4，2026-09-27。论文首页标记 ICML 2026 / PMLR 306；官方 README 自述 Spotlight。
- **主链接**：[arXiv](https://arxiv.org/abs/2601.18510)、[v4 全文](https://arxiv.org/html/2601.18510v4)、[v4 PDF](https://arxiv.org/pdf/2601.18510v4)、[官方代码](https://github.com/liushiliushi/JitRL)。
- **类别**：测试时学习 / 跨回合经验记忆 / action-level policy adaptation；不更新基础模型权重，不训练价值网络。
- **结论**：值得作为“Agent 自动进化不一定需要训练权重”的核心案例。证据支持低样本重复交互中的记忆收益；不支持“无条件胜过参数 RL”“已解决一般持续学习”或“任何笔记本都能复现原成绩”。

## 2. 问题与系统闭环

冻结模型反复执行任务时会重复犯错；整段历史塞进上下文既耗 token，也不保证模型遵循历史经验。JitRL 把经验转成可检索的局部动作价值，在决策时直接改候选动作分数。

闭环：执行一回合 → 评价每步贡献 → 算折扣回报 → 存储状态、动作、回报 → 遇到相似状态时检索 → 估值与重排 → 执行 → 继续积累。

这里的“进化对象”是外部经验库和由它诱导的动作分布。知识通常只在带着该记忆模块运行时生效；删除记忆不会留下权重内的技能更新。它更接近非参数强化学习/案例决策，而不是模型自我改写或自动发现新算法。[论文 §§4.1–4.3，pp.3–4](https://arxiv.org/pdf/2601.18510v4#page=3)

## 3. 方法与公式解读

### 3.1 经验、状态和回报

记忆 M = {(s_i, a_i, G_i)}。回合结束后，LLM evaluator 根据完整轨迹提供每步奖励 r_t；G_t = Σ_{u=t}^T γ^(u−t) r_u。

- WebArena：规范化 URL，把具体 ID 替换成占位符，再加页面有效状态与局部操作历史；操作中的瞬时元素 ID 转成 accessibility tree 语义描述。
- Jericho：压缩成实体/动作摘要，维护目标、进度和去环路的位置历史；候选受游戏引擎提供的 valid-actions 限制。
- 检索：总体采用结构化文本/Jaccard；附录另述 Jericho 状态/历史双索引，权重 0.75/0.25。WebArena 先按页面类型筛选，再比较有效状态。

应保留这套工程细节：让“两个状态够相似”“旧动作能重新映射到当前 UI”成立，往往比最后的加法公式更难。[附录 F，pp.15–16](https://arxiv.org/pdf/2601.18510v4#page=15)

### 3.2 价值估计

检索 k 个邻居 N(s)：

- V̂(s) = 邻域所有回报的均值。
- Q̂(s,a) = 邻域中执行动作 a 的回报均值。
- 没出现过的动作：概率 λ 取 V̂(s)+α/|N(s)|，否则取 0，以鼓励有限探索。
- Â(s,a)=Q̂(s,a)−V̂(s)。附录实际算法还使用 max-absolute 归一化。

候选集合包含 LLM 给出的动作与邻域中历史动作的并集。历史独有动作被赋予初始分数 0。因此它能找回模型本回合遗漏的旧动作；但仍不能凭空发现模型及历史从未产生过的动作。[式3–7，pp.3–4；式23、25，pp.15–16](https://arxiv.org/pdf/2601.18510v4#page=4)

### 3.3 策略目标

max_{π′} E_{a~π′}[Â(s,a)] − (1/β) KL(π′ || π₀)

解为 π*(a|s) ∝ π₀(a|s) exp(βÂ)，即 z′=z+βÂ。

直观上：保留基础模型先验，再指数性增加高回报动作的概率。β 越大，越信经验；β 越小，越信基础模型。这里写出的实际目标是 **KL 惩罚形式**，而非直接给定硬 KL 上限的优化问题。

作者提供两种动作先验：读取索引 token 的 logprob；或让黑盒模型输出 0–100 的口述信心分数。后者需要人为定义从信心到先验的映射，不能直接等同于模型真实 token logits。[§§4.3–4.4，pp.4–5；实现说明 p.5；附录 B，pp.11–12](https://arxiv.org/pdf/2601.18510v4#page=4)

### 3.4 理论适用边界（审阅判断）

闭式解本身是有限动作集合、给定优势下的 KL-正则重加权结果；不是“保证完整长程任务取得全局最优”的定理。进一步的一致性要求：状态/策略正则性、无偏有界噪声、覆盖、k→∞ 且 k/N→0、各动作样本数增长、记忆中的旧策略与当前策略差异趋零。实际 k=10、有限回合、自评奖励与长期旧经验并未直接满足这些渐近条件。

另外：未归一化时，V̂ 是对所有动作都相同的常数，在 softmax 中会抵消，故基线并非独立增加排序能力；关键是 Q̂、候选集合、探索与缩放。附录证明中的均值方差界也应额外检查时序相关经验所需的独立/弱相关条件。以上是技术审阅推断，不是作者已经验证的结论。[附录 C–D，pp.12–13](https://arxiv.org/pdf/2601.18510v4#page=12)

## 4. 实验：一定同时标明协议和数值

### 4.1 WebArena 主表

同一任务连续执行 5 次；Avg 是所有尝试平均成功率，Final 是第五次尝试成功率，不是 pass@1，也不是五次任一次成功的 pass@5。训练免费组使用 Gemini-2.5-Flash。

| 方法 | Avg % | Final % |
|---|---:|---:|
| Static | 35.63 | 36.30 |
| Memory | 41.36 | 43.00 |
| Reflexion | 41.08 | 42.12 |
| AWM | 39.37 | 40.32 |
| EvoTest | 39.24 | 42.49 |
| JitRL | 46.98 | 51.35 |

JitRL 相对 Static 的提升为 Avg +11.35、Final +15.05 个百分点；相对最好的 Memory 汇总指标为 +5.62、+8.35 个百分点。这些差值由表中数值计算。[表1，p.6；协议 §5.2.1，pp.5–6](https://arxiv.org/pdf/2601.18510v4#page=6)

### 4.2 对参数更新方法：不能只挑最漂亮一行

| 比较设置 | JitRL | 对照 | 结论 |
|---|---:|---:|---|
| 主表 WebArena-Lite，Final | 60.00% | WebRL 46.06% | 骨干/适应条件不完全相同，不能单独归因于算法 |
| Llama-3.1-8B，同任务 5 次在线适应 | 32.97% | WebRL 27.27% | 更支持小样本在线适应优势 |
| Llama-3.1-70B，同训练任务、165 个 held-out Lite 任务、禁止测试集适应 | 40.88% | WebRL 46.06% | 严格离线对照中 JitRL 较低；SFT 为23.00% |

来源：[表2，p.6](https://arxiv.org/pdf/2601.18510v4#page=6)、[表12，p.21](https://arxiv.org/pdf/2601.18510v4#page=21)、[表13，p.22，附录 J.1 的协议在p.20](https://arxiv.org/pdf/2601.18510v4#page=22)。SFT 的数值来自原论文，附录 E 说明没有可用 SFT checkpoint；WebRL 则重新评估了作者 checkpoint。正文对 SFT/checkpoint 的概括和附录说明不够一致，报告宜按附录的详细说明表述。

### 4.3 Jericho

Library、Zork1、Zork3，每个游戏50回合。表内顺序为 Avg / 第50回合分数：

| 方法 | Library | Zork1 | Zork3 |
|---|---:|---:|---:|
| Static | 10.0 / 10 | 8.5 / 10 | 0.2 / 0 |
| EvoTest | 21.5 / 26 | 46.8 / 54 | 2.6 / 4 |
| GRPO | 13.6 / 11 | 16.2 / 10 | 1.1 / 2 |
| JitRL | 25.9 / 30 | 53.0 / 69 | 3.1 / 5 |

[表3，p.6](https://arxiv.org/pdf/2601.18510v4#page=6)。Fig.3 标注游戏最高分分别30、350、7；因此 Zork1 最终69不等于通关。

同 Qwen3-32B 对照的 Avg：JitRL 20.8 / 42.1 / 2.3，GRPO 13.6 / 16.2 / 1.1。[表14，p.22](https://arxiv.org/pdf/2601.18510v4#page=22)

更充分调参后，GRPO 的 Zork1 验证平均达到40.7、最大55，需要3,200条训练轨迹；默认GRPO为400条，JitRL为50条。注意附录 O.4 文字把53.0称为“同Qwen3-32B JitRL”，与表14的42.1不一致。应引用表14作为同骨干比较，不能复述这一处53.0。[附录 O，p.23；表20，p.25](https://arxiv.org/pdf/2601.18510v4#page=25)

### 4.4 泛化和消融

- 仅可检索不相交任务记忆：Admin/GitLab/Map/Reddit/Shopping，JitRL 为48.37/38.73/35.78/55.04/36.98%，Static 为36.96/37.25/31.19/36.43/23.44%。支持同类网站内的程序知识转移，仍不是跨任意环境泛化。[表5，p.7](https://arxiv.org/pdf/2601.18510v4#page=7)
- 同检索信息，Admin/Reddit 的 prompt-update 为48.35/54.57%，logit-update 为52.31/57.64%。[表8，p.8](https://arxiv.org/pdf/2601.18510v4#page=8)
- GPT-5-mini、DeepSeek-V3.2 的 Admin/Reddit 也测过；DeepSeek Reddit Avg 54.42低于Reflexion55.04，所以不能写“每个指标都最好”。[表4，p.7](https://arxiv.org/pdf/2601.18510v4#page=7)
- 检索扩展测试仅到约2,500条记忆，耗时15–47ms；不足以外推到百万记忆或长期多用户部署。[表19，p.25](https://arxiv.org/pdf/2601.18510v4#page=25)

## 5. 计算、数据与 API

### 论文实际配置

- 候选动作3，检索k=10，温度0.8。
- Jericho：γ=.5、阈值.95、λ=.65、α=5，50回合、每回合60步。
- WebArena：γ=.1、阈值.8、λ=.05、α=5，任务相似度阈值.27，history/task权重.7/.3；附录表11写10步、50回合，但正文主实验明确为每任务5次，必须核实运行配置。
- 作者仓库使用 OpenRouter；需游戏ROM、Jericho依赖；WebArena还需站点环境和BrowserGym。仓库介绍含812个WebArena任务配置。[表10–11，pp.20–21](https://arxiv.org/pdf/2601.18510v4#page=20)、[README](https://github.com/liushiliushi/JitRL#installation)

### 成本的正确解释

表9给出 JitRL $290、Static $200、其他免训练方法$220–250，WebRL约$9,900。所谓“30倍便宜”来自这组特定 API 用量与训练成本估算，不是无成本，也不是实际端到端延迟快30倍。以该表计算，JitRL对Static反而增加45%费用。

WebRL预算按16×H200、154小时、两节点每小时$64估算约$9,856；含SFT、任务生成、rollout、reward labeling及优化。GRPO扫描使用4×H200。API定价、硬件租价、环境运行费是否纳入、调用token总数与任务范围都会影响比较；不是当前购买报价。[表9，p.8；附录 P，pp.23–24](https://arxiv.org/pdf/2601.18510v4#page=24)

JitRL自身不用反传，所以能用本地推理模型；**不等于原始Gemini实验可以纯本地等价复现**。

## 6. 官方代码审计：论文公式与当前实现有实质差异

检查的是官方master，当时最新commit为 [143d22185d95fbf633a0befe6861d5e8b732543b](https://github.com/liushiliushi/JitRL/commit/143d22185d95fbf633a0befe6861d5e8b732543b)，提交日期2026-07-21；早于本文核验的v4。以下只能判断**这个公开版本**，不能反推作者所有实验实际用了什么私有版本。

1. **加到概率上，不是加到logprob上。** Jericho先对token logprob取exp，口述模式则confidence/100；后续用该normalized_prob加advantage。WebArena也这样做。[Jericho L707–736](https://github.com/liushiliushi/JitRL/blob/143d22185d95fbf633a0befe6861d5e8b732543b/Jericho/src/jitrl_agent.py#L707-L736)、[L375–387](https://github.com/liushiliushi/JitRL/blob/143d22185d95fbf633a0befe6861d5e8b732543b/Jericho/src/jitrl_agent.py#L375-L387)、[WebArena L377–378](https://github.com/liushiliushi/JitRL/blob/143d22185d95fbf633a0befe6861d5e8b732543b/WebArena/memory_agents/jitrl_agent.py#L377-L378)。
2. **选最大分数，不是softmax采样。** [Jericho L769–773](https://github.com/liushiliushi/JitRL/blob/143d22185d95fbf633a0befe6861d5e8b732543b/Jericho/src/jitrl_agent.py#L769-L773)、[WebArena L1130–1131](https://github.com/liushiliushi/JitRL/blob/143d22185d95fbf633a0befe6861d5e8b732543b/WebArena/memory_agents/jitrl_agent.py#L1130-L1131)，对照论文p.26 Algorithm 1。
3. **归一化和探索还有差异。** 有正优势时按最大正值归一化，不是max|A|；Jericho加上随回合1→1.5的权重，探索概率也由历史质量自适应计算。新增未见动作后还重算动作均值基线。[L305–348](https://github.com/liushiliushi/JitRL/blob/143d22185d95fbf633a0befe6861d5e8b732543b/Jericho/src/jitrl_agent.py#L305-L348)
4. **默认设置不等于论文配置。** Jericho默认50步，而论文表10是60步；默认口述confidence。[main.py](https://github.com/liushiliushi/JitRL/blob/143d22185d95fbf633a0befe6861d5e8b732543b/Jericho/main.py#L20-L68)
5. **原模型快照已退役。** README明确披露原Gemini成绩使用google/gemini-2.5-flash-preview-09-2025，现默认stable，数值可能变化。[README复现说明](https://github.com/liushiliushi/JitRL#jericho-text-adventure-games)

这不是单纯变量名问题。自行构造例子：p=(.9,.1)，bonus=(0,1)，概率加法得到(.9,1.1)，选择第二动作；log概率加法得到(log .9,log .1+1)，仍选择第一动作。因此公开代码的策略并不与论文闭式目标恒等。复现时应分列“作者代码原样”和“按论文公式实现”，不要静默修正后仍称精确复现。

## 7. 评测与泄漏风险清单

以下是本报告审阅判断：

- **允许测试时适应≠普通一次性测试。** 同任务复试并把其经验留在记忆里是该任务定义的一部分，不能简单叫作违规泄漏；但必须把它与无测试适应的held-out结果分开。
- **同任务记忆与跨任务泛化要分离。** 固定任务顺序、同模板近邻、任务ID/答案进入状态、轨迹中的成功状态都可能扩大收益。需公布任务清单、顺序、划分和检索来源。
- **自评奖励偏差。** evaluator可能误判或受轨迹文本影响；训练奖励与最终成功判定宜用独立信号。状态压缩可能混淆“看起来相似但隐藏状态不同”的场景。
- **valid-actions是额外帮助。** Jericho引擎提供可执行命令候选，可能大幅缩小搜索空间。比较必须给所有方法相同候选信息。
- **模型预训练污染未知。** Zork等经典游戏可能存在在线攻略；论文没有证明基础模型完全未知这些内容。跨游戏/新生成场景可补充验证。
- **统计不足。**主表未提供多seed置信区间；表11指定seed0。单个最终回合分数不能代替稳健收敛证据。
- **不能把Final−Avg当作严格学习效率。** 该差值受随机性与曲线形状影响，只有配合逐回合曲线、重复seed、样本成本才有解释力。
- **非平稳环境未充分验证。** 持续记忆可能积累过时或错误动作；冻结权重避免参数遗忘，但不能保证系统行为没有“被坏记忆覆盖”的功能退化。
- **复现先解决文本内部不一致。** WebArena 5次/50次、Qwen Zork1 42.1/53.0、原始快照退役、公开实现与公式差异，均要记录而非自行猜测。

## 8. 无付费 API 的分级复现建议

用户Windows硬件、已有模型和本地工具尚未确认。本节是待环境检查后选择的方案，不要求现在安装，也不假定GPU、WSL或游戏ROM已可用。

### A. 机制验证：最小且零API成本

纯标准库编写一个小型离散环境，手工指定基础动作概率，在线存储真实环境奖励，实现Jaccard/kNN、Q均值、探索、z+βA与softmax。检验：

1. β=0时回到原策略；空记忆安全回退，无除零。
2. 增大某动作经验回报时其概率增加；概率和为1。
3. 给所有优势加同一常数不改变softmax。
4. 加法logits与π₀·exp(βA)归一化数值等价。
5. 错误检索、奖励噪声、环境奖励反转后性能如何变化。

这只能称“公式/机制演示”，**不是论文复现、不是LLM Agent实验**；即便曲线变好，也不能当作WebArena或Jericho结果。

### B. 最小真实缩小复现：本地冻结LM + 单个Jericho游戏

前提是已有或另行获准下载的本地instruction LM、可用推理后端、合法获得且可运行的ROM。优先复用现有环境。模型大小由实际硬件决定，不能在未检查前承诺7B/8B可流畅运行。

- 先1回合/短步数做联通性验证，再做50回合研究；没有计费服务、网络API调用或远程embedding依赖。
- 本地LM生成3个动作，另一步固定候选并读取单token索引logprob；不依赖从任意JSON倒数第二token猜索引。
- 状态、目标与历史摘要以及奖励评价均使用同一本地模型；可另设仅使用游戏真实分数增量的控制组。更换奖励方式必须单列为变体。
- 分别实现“论文公式”和“公开仓库重排”。初始先验统一、候选统一、step limit统一，比较Static、相同记忆的prompt基线及两种JitRL实现。
- 至少预注册多个seed、完整回合顺序、ROM/模型哈希；记录每步状态、候选、先验logprob、邻居来源、Q/A、最后动作、真实分数及耗时。
- 输出全部回合均值、末段均值和不确定性；最后一个回合也可报告，但不要只挑最大分数。

这属于“真实任务上的缩小复现/方法迁移验证”。换小模型会改变候选生成、判断和奖励质量；不能声称重现Gemini原表数值。

### C. 完整论文复现：目前有明确缺口

需要WebArena站点基础设施及确定的任务划分；原模型快照无法访问，作者实验commit与配置不清；严格参数RL对照涉及70B/32B模型及大GPU。没有这些条件时不应启动昂贵训练。现阶段最有价值的顺序是：代码/公式一致性核对 → 纯机制测试 → 获准后本地真实单游戏 → 再决定是否投入完整WebArena。

## 9. 对Agent自动进化的价值与下一步研究

实用价值：可插入既有Agent决策层，记忆可审计、可删除；适合重复UI操作、有结构化状态、有反馈的窄域任务。不能把外部记忆优势理解成基础模型能力永久升级。

更值得追问的研究方向：

- 用可信环境奖励替换/校准LLM自评，测量奖励错误传播。
- 加时间衰减、版本化状态、反例记忆与环境变更检测。
- 将动作重排的收益与更好候选生成/摘要/valid-actions约束的收益彻底分离。
- 比较真实logprob、口述信心、概率加法与KL重加权的校准和收益。
- 在独立新任务上冻结记忆评测，再开放在线适应，分别报告泛化与适应。

**推荐报告中的表述**：JitRL显示，冻结LLM配合经验记忆与动作重加权，可以在特定重复交互任务中获得可测量的测试时改进，且不需要梯度更新；其成本优势与胜过参数RL的结果依赖具体模型、数据和评测协议。公开实现与论文数学算法的差异，是复现时优先处理的问题。
