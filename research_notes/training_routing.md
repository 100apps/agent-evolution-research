# 训练、迁移预测与模型路由：8篇一手论文核验

核验日期2026-10-08。已取得8篇全文：6个指定arXiv、MeRF对应arXiv:2506.18485v3、CoPE对应PMLR正式版。OpenReview的forum/PDF/API本次返回验证页或403，改用作者arXiv版本及正式会议出版物；没有依赖视频/二手解读的实验数字。仅阅读，没有运行第三方代码或产生API费用。

“复现建议”均为待硬件、已有环境、数据许可和执行授权确认后的分级方案；没有假定用户Windows已安装GPU、WSL、CUDA或大模型。机制演示、发布工件离线重放、缩小真实实验、完整论文结果复现是四种不同证据级别。

## 一览

| 论文 | 真正改变/预测的对象 | 关键条件 | 无付费API的起步点 |
|---|---|---|---|
| CoEvolve | RL训练分布与策略共同更新 | 可执行环境、奖励、强探索LLM | 先用已有轨迹核验三类弱点检测和验证器 |
| EvolveR | 原则记忆+GRPO参数更新 | 检索库、奖励、冷启动SFT | 现成3B权重/记忆检索消融，免重新训练 |
| TuneAhead | 预测完整微调后性能 | 历史完整训练元数据+100步探测 | 有发布特征表时CPU重做回归；不能零数据预测 |
| Skill0.5 | 通用技能内化、专项技能调用 | 技能库、分层rollout、GRPO/JSD | 审计技能/任务划分；本地权重推理需另核可用性 |
| MeRF | 训练prompt显式描述奖励规则 | 可验证奖励、真实RL更新 | 规则验证器/提示对照；后者不等于训练收益复现 |
| STS | 预测跨域性能变化幅度 | 白盒激活、匹配SAE、示例 | 现成模型+SAE可做无新SFT预测；真值验证仍需训练 |
| CoPE | 计划/执行的协调加权优化 | 多rollout、MCTS、LoRA DPO/KTO | 对固定轨迹复算协调分数 |
| ACRouter | 跨模型路由状态在线更新 | 结果反馈、记忆、已训练小路由器 | 官方ID/OOD176离线重放，无需API或实时LLM |

## 1. CoEvolve

**文献**：Shidong Yang、Ziyu Ma、Tongwen Huang、Yiming Hu、Yong Wang、Xiangxiang Chu；*CoEvolve: Training LLM Agents via Agent-Data Mutual Evolution*；2026-04-17，arXiv:2604.15840v1，ACL2026。 [论文](https://arxiv.org/abs/2604.15840) / [全文](https://arxiv.org/pdf/2604.15840v1)

**问题与方法。** 固定任务集不能跟上策略的弱点变化。CoEvolve使用GRPO训练，并从rollout提取三种信号：曾成功现失败的遗忘；同一策略下成功/失败并存的边界；低频但出现过的稀有动作模式。LLM诊断失败后重新探索环境，把动作-观察片段抽象成新任务/解法，经过环境执行验证再加入训练。新颖点在“反馈→重新探索→验证任务→更新数据”，并非一种新的GRPO梯度公式。GRPO仍使用组内优势、裁剪importance ratio和KL惩罚。[§3，pp.3–5](https://arxiv.org/pdf/2604.15840v1#page=3)

**关键证据。**

- 表1的五项指标均值（AppWorld TestN/TestC各TGC、SGC，加BFCL-v3 multi-turn）分别：Qwen2.5-7B 3.08→22.51（+19.43pp），Qwen3-4B 11.72→27.30（+15.58pp），Qwen3-30B-A3B 22.64→40.78（+18.14pp）。这不是相对提高19.43%，也不是一个统一任务成功率。[表1，p.5](https://arxiv.org/pdf/2604.15840v1#page=5)
- 更直接的GRPO控制：7B在AppWorld TestN TGC为26.78→27.98、BFCL56.00→61.50；4B为28.57→35.71、58.00→63.00；30B-A3B为48.81→54.76、64.00→67.00。[表2，p.6](https://arxiv.org/pdf/2604.15840v1#page=6)
- 去掉环境验证：4B的BFCL63.00→58.50、AppWorld35.71→27.38；同样Qwen3-4B作探索器，Synthesis Only53.00→CoEvolve56.50，强Qwen-Max探索器则58.00→63.00。[表11–12，p.14](https://arxiv.org/pdf/2604.15840v1#page=14)

**资源与复现。** veRL；7B/4B用8×H20，30B-A3B用16×H20；100个初始合成任务，120训练步，每10步补数据，GRPO组8、batch32、lr1e-6；探索LLM为Qwen3-Max。[附录A.2，pp.12–13](https://arxiv.org/pdf/2604.15840v1#page=13)。[论文代码链接](https://github.com/AMAP-ML/CoEvolve)本次重定向到[StoneHanaMori/CoEvolve](https://github.com/StoneHanaMori/CoEvolve)，当前根目录只有README、LICENSE、docs/img，不能说完整训练代码已可运行。

**判断与边界。** 相对zero-shot的巨额涨分主要还包含普通RL训练收益，算法增量应看表2；“没有人工示范”仍依赖环境任务结构、可验证奖励和强模型。BFCL在validation集评测，合成任务相似度分析也用了validation参照，后续复现应新增独立封存测试集并做任务模板去重。先从真实固定轨迹复现信号检测/任务可执行性，再考虑小模型动态数据对照；不要把仅生成新prompt的演示叫完整共同进化。

## 2. EvolveR

**文献**：Rong Wu等11位作者；*EvolveR: Self-Evolving LLM Agents through an Experience-Driven Lifecycle*；首发2025-10-17，核验v3（2026-05-16），ICML2026。[论文](https://arxiv.org/abs/2510.16079) / [全文](https://arxiv.org/pdf/2510.16079v3) / [官方代码，当前KnowledgeXLab](https://github.com/KnowledgeXLab/EvolveR)

**方法。** 离线冻结策略，把成功/失败轨迹自蒸馏为自然语言原则+结构化三元组；相似检索后再作语义去重、合并、评分和淘汰。原则效用s(p)=(成功使用数+1)/(使用数+2)。在线动作包含检索经验、检索知识和回答；GRPO再更新策略。奖励为EM正确性+0.1×格式/思考/检索形状奖励。其“离线自蒸馏”主要生成外部原则文本，不是该阶段训练一个学生网络。[§3，pp.3–6](https://arxiv.org/pdf/2510.16079v3#page=4)

**证据。** NQ/HotpotQA训练域；TriviaQA、PopQA、2Wiki、Musique、Bamboogle评估泛化；主指标Exact Match。

- Qwen2.5-3B七项均值：Search-R1-instruct .325，EvolveR .382；7B为.385→.417。[表1，p.8](https://arxiv.org/pdf/2510.16079v3#page=8)
- 3B保持同样训练、仅测试去掉经验检索：.382→.340；只原则+检索而不RL为.357；完整闭环.382。[表3–4，p.10](https://arxiv.org/pdf/2510.16079v3#page=10)
- 0.5B用GPT-4o-mini教师蒸馏优于自蒸馏（.220 vs .150）；3B自蒸馏略高于教师（.382 vs .370）。不能概括成“自蒸馏总比强教师好”。[表2，p.9](https://arxiv.org/pdf/2510.16079v3#page=9)

**资源。** BGE-M3向量化，top3知识与top3原则，8192输入/1024输出；3B完整生命周期约39.4小时、8×A100-80GB。官方README提供3B模型、数据和本地Wikipedia检索路线。[附录A.1，p.16](https://arxiv.org/pdf/2510.16079v3#page=16)、[仓库](https://github.com/KnowledgeXLab/EvolveR#-model-zoo)

**判断与最小复现。** 适合检验“参数学习+外部经验互补”，但无检索后下降也说明知识未完全内化。七个QA集不等于开放环境的长期终身学习；原则成功统计是使用相关性而非因果贡献，易受检索偏好和难度混杂影响。免付费路线可从已发布3B模型、固定本地小知识库和封存测试题开始，比较原始轨迹记忆/去重原则/无记忆；这验证推理部分，不能替代重训GRPO所得增益。应确保原则库仅来自训练题，不能包含评测题答案。

## 3. TuneAhead

**文献**：Yuxiang Luo等9位作者；*TuneAhead: Predicting Fine-tuning Performance Before Full Training Begins*；2026-06-16，v1，ICML2026 poster。[论文](https://arxiv.org/abs/2606.17660) / [全文](https://arxiv.org/pdf/2606.17660v1)

**方法。** 把候选“数据集×LoRA超参数”编码成14个静态+10个动态特征，后者来自标准化100步训练探测；LightGBM拟合完整训练后分数，SHAP给出特征归因。静态包含长度、重复、语义多样性、参考困惑度；动态包含损失/梯度、曲率代理、激活稀疏度与小规模域外退化。目标是回归性能，阈值筛选只是后续部署策略。它不是零训练的预言器。[§§3–4，pp.3–5](https://arxiv.org/pdf/2606.17660v1#page=5)

**证据。** Qwen2.5-7B-Instruct，1300+完整LoRA运行，370测试运行，真值三seed平均。

- MMLU RMSE=1.47pp、R²=.99，95.1%预测误差≤3pp；ProxyLM2.11pp、85.8%，early-stop7.43pp、32.8%；仅静态3.50pp，仅动态3.38pp。[表1，p.6](https://arxiv.org/pdf/2606.17660v1#page=6)
- Llama3-8B RMSE5.02pp、Qwen2-0.5B3.75pp；**各目标模型重新训练预测器**，不是同一预测器零样本跨模型迁移。[表2，p.6；解释p.7](https://arxiv.org/pdf/2606.17660v1#page=7)
- 阈值55%时，36.1%候选被送去完整训练，论文估算净节省58.4%，保留94.5%真正达标运行。节省依赖候选池失败率、阈值和probe成本，不是普适节省常数。[表4，p.7](https://arxiv.org/pdf/2606.17660v1#page=7)

**资源与边界。** 数据来自Alpaca/Dolly等及其子采样/噪声/域切分变体，500–25k样本；lr1e-5/2e-5/3e-5，batch8/16/32；100步probe平均7.76分钟为论文测量，不能套用于未知硬件。预先训练预测器需要大量带真值完整运行，其沉没成本不能忽略。[附录A，pp.16–17](https://arxiv.org/pdf/2606.17660v1#page=16)

**判断与最小复现。** 本次一手论文未找到已验证官方代码/完整特征表入口，不能直接声称可复跑1300次实验。若取得真实特征与标签表，CPU即可复核LightGBM及bootstrap；否则先在已有小模型的既有训练日志上做留一数据源验证。论文按实验运行随机切分（seed36），需要额外检验同源数据变体跨split相似性；SHAP筛选明确不触碰测试集，这是正面设计，但并不自动解决数据源泄漏。SHAP是关联归因，不是“改这个数据属性必然提高模型”的因果证明。

## 4. Skill0.5

**文献**：Jiapeng Zhu、Jianxiang Yu、Yibo Zhao、Chengcheng Han、Qi Gu、Xunliang Cai、Xiang Li、Weining Qian；*Skill0.5: Joint Skill Internalization and Utilization for Out-of-Distribution Generalization in Agentic Reinforcement Learning*；2026-05-27，v1。[论文](https://arxiv.org/abs/2605.28424) / [全文](https://arxiv.org/pdf/2605.28424v1) / [代码](https://github.com/JasonZhujp/Skill0_5)

**方法。** 通用认知原则放进权重，具体场景技能继续外部检索。第一阶段只给专项技能，采样8条轨迹估算通过率；全部失败为hard，低于最近窗口平均为medium，其余easy。

- hard：补充通用技能让同一模型生成成功教师轨迹，再以token级JSD蒸馏回不含通用技能的学生输入。
- medium：复用第一阶段轨迹做GRPO。
- easy：额外运行无技能诊断，计算有技能−无技能的通过率差，把该利用优势加到RL优势，减少对训练域捷径的依赖。

不是持续自动发明全部技能；依赖预先给定的分层skill bank。[§3，pp.4–5](https://arxiv.org/pdf/2605.28424v1#page=4)

**证据。** Qwen2.5-7B-Instruct：

- ALFWorld：ID/OOD成功率93.1/58.5；SkillRL90.8/45.3；GRPO80.5/43.4。[表1，p.6](https://arxiv.org/pdf/2605.28424v1#page=6)
- WebShop：ID/OOD 40.4/40.6；SkillRL38.3/36.7；GRPO33.6/32.3。[表3，p.14](https://arxiv.org/pdf/2605.28424v1#page=14)
- ALFWorld ID为Pick/Cool/Clean，OOD为Look/Heat/Pick2。**测试OOD时会提供训练期间未见过的OOD专项技能**；不是不给新知识的零样本泛化。WebShop也采用产品类别拆分并开放相应OOD技能。[§2.3，p.3；§4.1，p.7](https://arxiv.org/pdf/2605.28424v1#page=3)

**资源与最小复现。** 4×H800，batch16，ALFWorld120步/WebShop150步；最长30/15环境步；Qwen3-Embedding-0.6B检索top3技能，窗口W=5，JSD取top64 token。[附录D，p.13](https://arxiv.org/pdf/2605.28424v1#page=13)。先核验技能划分、固定轨迹上的tier路由与权重，再在已有本地模型做“相同技能信息”的推理对照；完整验证需三种损失的真实训练，不能用纯prompt结果代替。

**判断。** 最有价值的是“内化什么、保留什么”这个系统设计问题。局限为两个文本模拟环境、人工划分通用/专项技能；诊断pass-rate差带有rollout噪声，不能直接当作严格因果效应；还应测试过时/错误/互相冲突的新技能以及没有适用技能时的行为。

## 5. MeRF

**文献**：Junjie Zhang、Guozheng Ma、Shunyu Liu、Haoyu Wang、Jiaxing Huang、Ting-En Lin、Fei Huang、Yongbin Li、Dacheng Tao；*A Simple “Motivation” Can Enhance Reinforcement Finetuning of Large Reasoning Models*；arXiv首发2025-06-23，核验v3（2026-03-09），ICLR2026。[指定OpenReview](https://openreview.net/forum?id=3owSlsYDQf) / [可访问一手全文](https://arxiv.org/pdf/2506.18485v3)

**方法。** 在训练rollout的system prompt加入实际可验证奖励函数的自然语言描述；外部打分与GRPO更新不变。K&amp;K例子包括正确性与输出格式分，给分规则在生成前可见；不提供当前题正确答案。目的在引导探索，不是让模型获得人类心理意义的“动机”。[§3，pp.3–5](https://arxiv.org/pdf/2506.18485v3#page=4)

**证据。** K&amp;K训练3–7人题4500个，评估2–8人每档100个；主表测试移除motivation。

- Qwen2.5-7B-Instruct：全部档均值RLVR .51→MeRF .63；ID .51→.65。
- 14B-Instruct：总均值.72→.83。DeepSeek-distill-Qwen1.5B .14→.17，仍然低，说明不能只靠提示把弱模型变强。[表1，p.6](https://arxiv.org/pdf/2506.18485v3#page=6)
- 数学四基准平均pass@1 33.38→36.78、pass@8 50.45→54.95；AIME25 pass@2反而16.7→10.0，所以“所有格子都上涨”不成立。[表2，p.7](https://arxiv.org/pdf/2506.18485v3#page=7)
- 某设置140步的pass@4/8超过普通RLVR280步终点；这是步数比较，不能据此宣称GPU时间减半。[Fig.3，p.7](https://arxiv.org/pdf/2506.18485v3#page=7)

**资源/边界。** veRL+Logic-RL，batch16、lr1e-6、1–2epoch、GRPO组8/clip.2/KL.001；未找到论文明确GPU型号、总GPU时或官方独立代码入口。[附录p.15](https://arxiv.org/pdf/2506.18485v3#page=15)。规则完整性与正确性影响训练；反向规则实验中的恢复不能解释为普遍抵抗误导提示。基准主要是封闭可验证题，不是开放Agent的持续环境学习。

**本地起步。** 无费用可先建立K&amp;K/CountDown验证器和固定奖励说明，对同一冻结小模型做有/无说明测试，验证格式与即时行为；但论文显示主要收益来自真正RL训练，因此这一步只检验提示机制。若后续有已可用的训练环境，再做同seed、同token预算、同GRPO设置的成对训练，并把答案正确率与格式奖励分开。

## 6. SAE as a Crystal Ball / STS

**文献**：Qi Zhang、Yifei Wang、Xiaohan Wang、Jiajun Chai、Guojun Yin、Wei Lin、Yisen Wang；*SAE as a Crystal Ball: Interpretable Features Predict Cross-domain Transferability of LLMs without Training*；2026-03-03，v1，ICLR2026。[论文](https://arxiv.org/abs/2603.02908) / [全文](https://arxiv.org/pdf/2603.02908v1) / [代码](https://github.com/PKU-ML/STS)

**方法。** 用训练域少量ICL示例，引起冻结模型内部激活变化；用稀疏自编码器SAE分解激活并选top100变化维度。然后测不同下游域在这些维度的激活强度（STS_act）或加入该域示例后的变化（STS_ICL），把它作为训练后影响幅度的预测信号。假设是ICL与SFT改变相近可解释特征，而不是直接预测某个任务最终准确率。[§§3–4，pp.4–6](https://arxiv.org/pdf/2603.02908v1#page=6)

**证据与限定。** LIMO817条数学样本用于SFT验证；Llama3-8B、Qwen2.5-7B、Gemma2-9B；MMLU-Pro跨域。

- STS_ICL与变化幅度的Pearson分别.81±.01、.78±.01、.77±.01；STS_act为.71、.90、.60。[Fig.3，p.7；表6，p.17](https://arxiv.org/pdf/2603.02908v1#page=7)
- 代码/健康训练域的相关为.77±.01/.71±.02，预测top100变化维度与实际重叠62/57。[表1，p.7](https://arxiv.org/pdf/2603.02908v1#page=7)
- 原始激活/跨域表示相似度/训练后表示相似度/STS的相关分别.03/.11/.61/.79。[表5，p.16](https://arxiv.org/pdf/2603.02908v1#page=16)
- **关键边界**：作者附录明确预测变化大小，不预测正负。LIMO SFT后多数域下降；图3还依据真实SFT变化选择极端域展示。不能把“相关&gt;.7”写成“无需训练就预测每个领域会提高还是降低、并给精确分数”。[附录A，p.14](https://arxiv.org/pdf/2603.02908v1#page=14)

**资源/复现。** 需要白盒中间层和匹配模型/层的已训练SAE；本文SAE在OpenWebText激活上训练。预测本身不更新LLM，但SAE不是免费从空白产生。用于核验真值的SFT为4×H20、10epoch、FSDP fp32、batch256；ICL变化采样20k token，下游每域10k token。[附录B，pp.15–16](https://arxiv.org/pdf/2603.02908v1#page=15)

**判断。** 是训练风险筛查/解释辅助工具，不是自动进化闭环本体。最小本地实证需先确认现有模型及匹配SAE；可重做前向特征与分数，但验证预测好坏还需要独立已微调checkpoint或真实训练。应预先固定全部目标域与示例、同时报告符号/幅度、加入留一训练域测试，避免只在已知退化的极端域上获得漂亮相关。

## 7. CoPE

**文献**：Huanxi Liu、Kun Hu、Qiang Wang、Yuanzhao Zhai、Feng Dawei、Bo Ding、Huaimin Wang；*CoPE: A Framework for Optimizing Coordination between Planning and Execution in LLM-based Agents*；ICML2026，PMLR306:76571–76601。[指定OpenReview](https://openreview.net/forum?id=9aU4vrHPKD) / [正式出版页](https://proceedings.mlr.press/v306/liu26az.html) / [正式全文](https://raw.githubusercontent.com/mlresearch/v306/main/assets/liu26az/liu26az.pdf) / [代码](https://github.com/Octobrist/CoPE)

**方法。** 区分“计划不可执行”和“执行偏离计划”。Self-Refining MCTS在计划节点上运行多个执行轨迹，用环境得分估计划质量；失败轨迹用于改写计划。计划可执行性cp来自多轨迹动作序列的平均一致性（归一化Levenshtein）；执行遵循度cτ由语义/动作匹配加动态规划对齐得到。计划训练使用权重(cw−cl+1)/2的DPO；执行使用KTO加cτ加权SFT，并去除偏好轨迹共享前缀，聚焦真正分歧。[§4，pp.4–6](https://raw.githubusercontent.com/mlresearch/v306/main/assets/liu26az/liu26az.pdf#page=5)

**证据。** 主表五次独立运行均值，指标是Average Reward，不应把ScienceWorld分数当成功率。

- Qwen2.5-7B：ALFWorld seen/unseen 88.00/86.27，最强基线80.62/81.64；ScienceWorld64.67/65.76，最强基线58.22/58.18。
- Qwen3-32B：ALFWorld93.65/92.27，ScienceWorld80.84/81.30；相应轨迹更短。[表1，p.7](https://raw.githubusercontent.com/mlresearch/v306/main/assets/liu26az/liu26az.pdf#page=7)
- 作者主动给出负面边界：短程HotpotQA加入显式计划34.92→28.25，WebShop44.20→39.66；这些场景协调差距接近零。[附录B.1，p.16](https://raw.githubusercontent.com/mlresearch/v306/main/assets/liu26az/liu26az.pdf#page=16)

**资源。** 先SFT再多轮优化，LoRA rank64；7B一次优化迭代在4×A100上，ALFWorld数据收集60小时、协调评分30分钟、优化2小时；ScienceWorld分别75小时、40分钟、2小时。开销大头是搜索采样，不是DPO训练。[表13，p.22](https://raw.githubusercontent.com/mlresearch/v306/main/assets/liu26az/liu26az.pdf#page=22)

**判断/最小复现。** 应先复算固定计划-轨迹上的Levenshtein、语义对齐与加权损失；这属于组件复现。完整验证需训练计划和执行模型、环境多rollout，普通机器不能据此承诺短时间完成。应检验“不同但合理的执行路径”是否被一致性分数误罚，以及错误计划时是否允许合理偏离。协调是好任务结果的代理，不能取代环境成功验证。

## 8. Agent-as-a-Router / ACRouter

**文献**：Pengfei Zhou等11位作者；*Agent-as-a-Router: Agentic Model Routing for Coding Tasks*；首发2026-06-22，核验v3（2026-06-26）。[论文](https://arxiv.org/abs/2606.22902) / [v3全文](https://arxiv.org/pdf/2606.22902v3) / [官方仓库](https://github.com/LanceZPF/agent-as-a-router)

**方法。** 每任务做Context→Action→Feedback→Context循环。路由器综合任务元数据、维度先验、top10记忆邻居和已微调Qwen3.5-0.8B，经加权投票挑选后端；验证器执行代码/代理指标，记忆只吸收过去已选模型的得分、成本与执行痕迹。形式为contextual bandit，r=性能−0.1×成本；累计regret相对逐题oracle。它是“在线记忆适应+离线训练小路由器”，不是全部零训练。[§3，pp.4–6](https://arxiv.org/pdf/2606.22902v3#page=5)

**基准与证据。** CodeRouterBench约10k题、8个后端、15+来源，7,080 probing、2,919 ID、176 OOD agentic任务；7类执行评分，3类用代理/LLM judge。数据来源有复用公开代码基准，需看去重/时间范围。

| v3表3方法 | ID AvgPerf % | ID CumReg | OOD AvgPerf % | OOD CumReg |
|---|---:|---:|---:|---:|
| ACRouter | 49.98 | 205.5 | 62.50 | 17.0 |
| DimensionBest | 47.50 | 277.4 | 不适用 | 不适用 |
| LinUCB | 46.84 | 296.9 | 49.82 | 31.1 |
| Qwen3.5-0.8B-Finetuned | 46.41 | 309.1 | 55.36 | 27.2 |
| Always-Opus4.6 | 43.83 | 387.1 | 57.14 | 26.7 |

[表3，p.9](https://arxiv.org/pdf/2606.22902v3#page=9)。**同页新增说明：更新后的独立GPT-5.4后端在同OOD集75.00%，高于表中ACRouter62.50。** 所以不能写“胜过所有单模型”。

**最新仓库与论文不一致，必须分栏。** 核验日README期望ID=50.14、CumReg202.0、成本$22.31；OOD176=73.30、CumReg15.9、成本$86.72。它明确说离线重放无需API/live模型；提供run_id.py、run_acrouter_ood176.py、run_baselines_ood176.py、真实矩阵和参考输出。当前发布工件数字不可倒填v3论文表。[仓库复现说明](https://github.com/LanceZPF/agent-as-a-router#reproduce-the-main-results)

**无付费复现优先级：本组最高。** 先在获准环境中固定commit和数据哈希，审阅脚本，再运行官方ID/OOD重放，检查输出数量、路由选择、regret、成本合计；不需要新调用8个付费后端。它是真实发布工件的重放，不是端到端新解题实验；把所有模型真值同时给路由器会构成oracle泄漏，在线决策必须只见当前可用先验和过去反馈。

**其他限制。** OOD只有176题且40步上限，不是标准250步；模型API和计费/缓存变化会影响成本。基准代理指标/LLM judge并不等于全部真实程序正确性；stream顺序、warm-start和检索相似度影响适应收益。适合验证低成本系统选择，但不直接证明被选择的大模型自身学会了新技能。

## 综合建议

1. 全文分析先纠正标签：预测器（TuneAhead/STS）、训练数据进化（CoEvolve）、记忆与权重共同学习（EvolveR/Skill0.5）、训练规则提示（MeRF）、计划执行协同（CoPE）、在线模型选择（ACRouter）解决的是不同环节。
2. 无付费实验优先采用ACRouter官方离线重放，再做JitRL清洁机制测试；有合适已有本地模型时才增加真正交互任务。
3. 任何实验都同时报告预算、任务划分、信息可见性、模型版本和失败结果；公开仓库结果不等于某一论文版本的原始实验记录。

## 附录：ACRouter发布工件的精确离线重放审计

### A. 固定版本、许可与下载范围

核验的GitHub main为 **e43839edb0d5d0a9feec2f7078019406ab4d64bd**（2026-06-29），由公开commit页及git ls-remote双重确认。

- [固定commit](https://github.com/LanceZPF/agent-as-a-router/commit/e43839edb0d5d0a9feec2f7078019406ab4d64bd)
- [176题数据JSON，固定版本](https://raw.githubusercontent.com/LanceZPF/agent-as-a-router/e43839edb0d5d0a9feec2f7078019406ab4d64bd/data/matrices/phase2_ood/unified/matrix_acrouter_ood176.json)
- 数据文件SHA256：`f0fe49db24cf2c1d5552a1dd512544676825e0e4f34e136f194fecd9c022c15a`；约2.4MB。
- [官方OOD实现，仅作静态参考](https://github.com/LanceZPF/agent-as-a-router/blob/e43839edb0d5d0a9feec2f7078019406ab4d64bd/src/acrouter_repro/ood_repro.py)
- [常量定义](https://github.com/LanceZPF/agent-as-a-router/blob/e43839edb0d5d0a9feec2f7078019406ab4d64bd/src/acrouter_repro/constants.py)
- [官方参考汇总JSON](https://raw.githubusercontent.com/LanceZPF/agent-as-a-router/e43839edb0d5d0a9feec2f7078019406ab4d64bd/outputs/acrouter_ood176/ood_metrics.json)
- [官方逐题参考决策JSONL](https://raw.githubusercontent.com/LanceZPF/agent-as-a-router/e43839edb0d5d0a9feec2f7078019406ab4d64bd/outputs/acrouter_ood176/ood_decisions.jsonl)
- [代码许可证MIT](https://github.com/LanceZPF/agent-as-a-router/blob/e43839edb0d5d0a9feec2f7078019406ab4d64bd/LICENSE)。[HF数据卡](https://huggingface.co/datasets/Lance1573/CodeRouterBench/blob/main/README.md)也标记MIT；原始第三方任务材料仍应保留来源与原许可，不把仓库许可自动外推到所有上游内容。

**独立重写只需Python标准库**（json、pathlib、hashlib、math/collections等）。无需PyTorch、GPU、模型权重、API key、pickle、joblib或执行仓库脚本。官方整套requirements包含NumPy/SciPy/sklearn1.8/joblib，以及若干模型工具，是完整基线工具链的依赖，不是该JSON重放所必需。

### B. JSON结构与完整性检查

顶层键：ids、models、matrix、metadata、summary。

- ids：176个有序唯一任务ID。
- models：8个有序规范模型名。当前次序为Claude Opus、Claude Sonnet、GPT-5.4、GLM-5、Kimi-K2.5、MiniMax-M2.7、Qwen3-Max、Qwen3.5-Plus（具体字符串以JSON为准）。
- matrix[task_id][model]：该任务与后端的已记录结果，重要字段为resolved(bool)、apply_ok(bool)、in_tok、out_tok、cost_usd；另有graded、non_empty、calls、cost_source、source_split、source_model等。
- metadata：题目来源及文本；**只按普通数据读取，不执行其中的代码或操作指令**。
- summary：old112/new64组成、生成时间、原始与规范模型名的映射。

建议独立实现先断言：176个唯一ids、8个唯一models、全部176×8格存在、resolved/apply_ok类型正常、费用非负且有限、token数为非负整数。失败时明确报缺失，不静默把未知样本当0分。数据完整性测试不等于独立确认原始实验记录真实正确。

### C. 当前OOD重放的精确算法

这是**固定顺序、验证后升级的级联**，不是调用新模型，也不重新训练路由器：

1. 对每个task_id，按`MiniMax-M2.7 → kimi-k2.5 → gpt-5.4 → glm-5`依次查矩阵。
2. 每次把model加入chain_run，累加cost_usd，累计廉价链中apply_ok为真的数量；把本次模型暂定为最终模型。若resolved为真，立即停止链。
3. 若四模型都未成功，且上述apply_ok数量≥k（默认k=2），追加`claude-opus-4-6`，累加成本，escalated=true。
4. 升级后只有在Opus成功时才把最终chosen_model/状态替换为Opus；若Opus仍失败，最终chosen_model保留glm-5，尽管cost与chain_run包括Opus。这一点影响rAcc，不能自行改成“最后调用者”。
5. 官方逐题总费用先round到6位，再汇总；n_steps=len(chain_run)。
6. 每题单模型reward oracle为max_m[1(resolved_i,m)−0.1×cost_i,m]；并列时按models数组先出现者选择。
7. 本级联每题reward=最终成功指示−0.1×所有尝试总费。CumReg是oracle reward减级联reward逐题相加。
8. AvgPerf=100×成功题数/176；Apply_ok为最终状态的比例；Perf/$=AvgPerf数值/总美元；rAcc是最终chosen_model等于reward oracle模型的比例；tokens按chain_run中所有调用求和。

无需读取参考汇总才能得出结果；应先生成独立结果，再与参考JSON/逐题JSONL比较，避免把引用数值抄成“复现”。无随机数，重放输入顺序不应改变聚合指标；这一性质也说明当前OOD脚本没有跨题学习状态。

### D. 官方参考数值（尚非本报告执行结果）

| 指标 | 固定commit参考文件 |
|---|---:|
| n | 176 |
| AvgPerf% | 73.30 |
| CumReg | 15.9 |
| $Total | 86.72 |
| Perf/$ | 0.85 |
| rAcc_reward_oracle | .3807 |
| Apply_ok% | 85.80 |
| AvgSteps | 2.66 |
| Escalations | 29 |
| TotInTok | 74,536,066 |
| TotOutTok | 1,128,908 |

$86.72及token量是发布矩阵中原始后端运行的累计估算；**本次只读取JSON不会发生这些模型调用或费用**。当前文档未执行重放；独立运行结果应由执行环境另附日志、脚本哈希和逐题输出。

### E. 必须披露的两个实现/数据边界

**实现与论文概括不同。** [当前ID源码](https://github.com/LanceZPF/agent-as-a-router/blob/e43839edb0d5d0a9feec2f7078019406ab4d64bd/src/acrouter_repro/id_repro.py)默认policy=hierarchical：在train+val上按任务ID前缀、来源、dimension学习group→model映射，min_count=50、shrink=500，以均值性能选择；test执行静态分层回退。OOD则是上述固定级联。这些工件确实可重放，但不能将它们描述成重新运行了论文文字中的0.8B策略+kNN记忆在线投票全闭环。

**new64规范名折叠了不同后端版本。** 数据summary明确记录：gpt-5.4-medium→gpt-5.4，kimi-k2.6→kimi-k2.5，MiniMax-M2.5→MiniMax-M2.7，qwen3.6-plus→Qwen3-Max。这样便于表格统一，但不能据此声称176题全部由同一版本的每个模型运行。应保留原始source_model和别名映射，在研究报告中显式标注版本混合。

因此推荐最终实验名称为：**“ACRouter公开OOD176结果矩阵的独立标准库重放与一致性审计”**。它比合成玩具例子更接近真实论文工件，同时仍然不同于新执行176道代码任务、验证全部原始模型输出或重现原论文完整在线进化机制。
