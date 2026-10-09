#!/usr/bin/env python3
"""Portable standard-library variant. Apply frozen AI labels; this is not fresh semantic annotation."""
import json,csv,hashlib,math
from pathlib import Path
from collections import Counter
P=Path(__file__).resolve().parent
S=json.load(open(P/'audit_sample_unlabeled.json'))
# Class names: central_llm_agent_loop, non_llm_rl_multiagent,
# incidental_tool_memory_other, unclear_from_abstract.
C='central_llm_agent_loop'; O='non_llm_rl_multiagent'; X='incidental_tool_memory_other'; U='unclear_from_abstract'
# audit_id, category, LLM/VLM centrality, action-observation loop, confidence,
# short exact abstract quotation, Chinese rationale.
L=[
('A01',O,'no','no','high','generate scene-consistent multi-agent trajectories','多主体轨迹预测；Transformer 用于预测场景内运动主体，摘要没有语言模型控制器。'),
('A02',O,'no','yes','high','policy optimization in safety critical tasks modeled via constrained Markov decision processes','贝叶斯世界模型用于约束 MDP 策略优化，属于传统模型式强化学习。'),
('A03',O,'no','yes','high','Using policy gradient methods','用策略梯度联合优化机器人形态与控制；图策略输出关节动作，没有 LLM。'),
('A04',O,'no','no','high','a model for predicting the behavior of all agents jointly','多交通参与者联合运动预测；借鉴语言建模不等于 LLM 驱动的行动闭环。'),
('A05',O,'no','yes','high','mode-switching, non-monolithic exploration for RL','研究 Atari 强化学习探索策略的模式切换，非 LLM 智能体。'),
('A06',O,'no','no','high','perform decentralized optimization, without directly exchanging any local data or parameters','agent 指去中心化学习节点；核心是核近似和通信复杂度，不是语言智能体。'),
('A07',O,'no','yes','high','decode and understand the representations that such agents develop','用问答探测视觉环境中预测式智能体的内部表征；语言是探针而非 LLM 控制器。'),
('A08',O,'no','yes','high','a graph neural network based model that is able to perform multi-agent routing','图神经网络与学习式价值迭代进行多主体协同路由，没有 LLM。'),
('A09',U,'yes','unclear','medium','decompose high-level tasks into mid-level plans without any further training','明确以 LLM 生成可执行计划，但摘要只说明计划转换和可执行性评估，未说明环境反馈驱动的反复行动闭环。'),
('A10',O,'no','yes','high','train an RL agent to align a Mach-Zehnder interferometer','基于图像观测的强化学习物理控制，非 LLM。'),
('A11',O,'no','yes','high','cooperative multi-agent reinforcement learning','研究多智能体强化学习的价值分解和可变子团队，不涉及 LLM。'),
('A12',O,'no','yes','high','train an explorer and an achiever policy via imagined rollouts','视觉世界模型学习探索和目标到达策略；有行动闭环但没有 LLM。'),
('A13',O,'no','yes','high','cooperative Multi-agent Reinforcement Learning (MARL)','核心是 MARL 消息聚合和局部策略增强，没有语言模型驱动决策。'),
('A14',O,'no','yes','high','asynchronous multi-agent actor-critic methods','非语言多智能体 actor-critic 异步策略学习。'),
('A15',U,'unclear','yes','medium','reinforcement learning, imitation learning, and pre-trained image and language models','交互网页基准和多步动作是核心，但摘要仅写预训练图像/语言模型，不能据此确认现代 LLM 控制器。属于重要边界案例。'),
('A16',O,'no','yes','high','In cooperative multi-agent reinforcement learning','研究 IGM 分解与 Bellman 迭代，属于协作 MARL。'),
('A17',O,'no','yes','high','model-based reinforcement learning (MBRL)','在线世界模型为模型式 RL 服务，以线性回归和随机特征建模，没有 LLM。'),
('A18',C,'yes','yes','high',"Evaluator's feedback to refine the Actor's subsequent outputs",'LLM 作为核心控制器，生成候选分子、调用化学评估工具、根据反馈反思并改进下一轮输出。'),
('A19',X,'unclear','no','high','14K single or multi-turn dialogues','核心是多模态角色扮演对话数据和评价；摘要没有环境/工具行动闭环，不能把角色对话直接算作行动型 LLM agent。'),
('A20',U,'yes','unclear','medium','understand GUI screenshots and generalize to unseen interfaces','VLM GUI 动作模型明确，但摘要重点是 grounding 数据和单步能力；仅凭摘要无法确认闭环控制在评价中的位置。'),
('A21',O,'no','yes','high','evaluate the building blocks in ablation studies, and demonstrate good performance through quantitative comparisons on the Atari 100k benchmark','Atari 世界模型与帧/动作堆叠属于非 LLM 模型式控制。'),
('A22',C,'yes','yes','high','stepwise retrieval and planning accuracy','MLLM 自适应多步检索与规划是基准和训练流程的核心；逐跳证据、中间答案和后续检索形成信息反馈链。'),
('A23',O,'no','yes','high','multiple agents are required to navigate to their respective goals without collisions','超图网络用于多主体路径规划；参数模型与主体协调均非 LLM agent。'),
('A24',C,'yes','yes','high','consecutive text observations in the interaction histories used to prompt LM policies','语言模型作为环境控制策略；用连续观测的差分组织交互历史，在长程游戏中循环决策。'),
('A25',X,'no','no','high','a non-parametric memory of seen concepts','视觉自监督表征学习的样本概念记忆，并非语言智能体长期记忆。'),
('A26',O,'auxiliary','yes','medium','translates it into a reward function to train a teammate policy','LLM 提议行为并生成奖励，主要行动者仍是训练出的 MARL 策略。标作混合边界：LLM 辅助训练，不直接等同 LLM 行动策略。'),
('A27',O,'no','yes','high','cooperative Multi-Agent Reinforcement Learning (MARL)','研究参数共享中的梯度冲突和神经元复制，非 LLM 控制器。'),
('A28',X,'no','unclear','high','physics-informed World Model (WM) framework for computational lithography','world model 指光刻物理过程和逆向规划模型；摘要未显示语言模型或 LLM 智能体。'),
('A29',C,'yes','yes','high','malicious manipulation of the tool-calling process','核心研究 LLM agent 多工具推理轨迹的安全性；攻击与评估对象都是工具调用行动流程，属于闭环 agent 的安全研究。'),
('A30',C,'yes','yes','high','a ReAct-style reasoning loop comprising five phases: THINK, PLAN, ACT, OBSERVE, and REFLECT','明确 LLM 自主蛋白设计控制器和 THINK–ACT–OBSERVE–REFLECT 闭环，结合检索及计算工具。'),
('A31',C,'yes','yes','high','agents to reflect on past failures to extract misaligned behavioral patterns','LLM 具身协作行动，结合环境状态、伙伴行为和过去失败反馈学习合作规律。'),
('A32',U,'yes','unclear','medium','an LLM-guided graph traversal featuring node exploration, node exploitation, and, most notably, memory replay','LLM 引导知识图谱遍历与记忆回放是核心，但摘要没有充分区分自适应行动反馈循环和预设检索算法。保守保留边界。'),
('A33',C,'yes','yes','high','open-ended language action environments (e.g., negotiation or question-asking games)','LLM 通过自然语言动作与开放环境交互，利用交互奖励训练策略；属于语言行动闭环。'),
('A34',X,'unclear','no','high','one cohesive conversational flow','研究开放域聊天技能融合与对话数据；没有工具/任务环境中的决策行动回路。'),
('A35',O,'no','yes','medium','train a model that seeks relevant information through sequential decision making','把阅读理解改造成部分可观测顺序信息搜索；摘要无 LLM 控制器，按非 LLM 信息寻求智能体归类。'),
('A36',X,'unclear','no','high','multi-tasking improves over a BERT pre-trained baseline','多任务开放域对话基准，含知识/图像对话；未展示工具或环境行动闭环。'),
('A37',X,'no','no','high','uses a memory module to augment the transformer architecture','记忆用于视频段落描述的连贯性与去重复，而非 LLM 智能体。'),
('A38',X,'no','no','high','storing a handful of historical relation examples in episodic memory','episodic memory 指持续关系学习的经验回放，非语言智能体任务记忆。'),
('A39',O,'no','yes','high','The method uses the actor-critic framework','用户与系统作为双智能体联合训练对话策略；actor-critic 为核心，没有 LLM。'),
('A40',U,'unclear','yes','medium','place this model in a multi-agent self-play environment','语言模型确实进入多主体自博弈和奖励反馈，但摘要未给出 LLM 身份/规模；不能只因年代早就否认，也不能自动视为现代 LLM agent。'),
('A41',X,'unclear','no','high','text-to-image retriever, visual concept detector and visual-knowledge-grounded response generator','固定检索–视觉概念–回答流水线用于聊天；没有明确的自适应工具/行动循环。'),
('A42',O,'no','no','medium','a two-step approach: extractive summarization followed by abstractive summarization','标题明确多智能体 actor-critic，摘要核心是拆分医学报告摘要任务；未显示 LLM 交互控制回路。'),
('A43',X,'yes','no','high','combines a source code retriever and an auto-regressive language model','检索增强代码补全，核心是下一个代码 token 预测；没有执行、观测和修正的编程 agent 回路。'),
('A44',O,'no','yes','high','one trained via imitation learning and another trained via reinforcement learning','用自然语言注释探测围棋策略网络的表征；语言是解释工具，不是控制器。'),
('A45',X,'yes','no','high','retrieval augmentation of long-context language modeling','研究长上下文检索嵌入和分块边界，非自适应智能体行动流程。'),
('A46',X,'yes','no','high','solving DST with LLMs through function calling','function calling 用于对话状态跟踪/结构化状态输出；摘要未展示真实工具执行和观测反馈循环。'),
('A47',X,'yes','no','high','question answering, event summarization, and multi-modal dialogue generation tasks','LLM agents 用于构造长对话；论文核心评估会话记忆与问答/总结，而非任务行动闭环。'),
('A48',U,'unclear','yes','medium',"integrate the personality profiles directly into the agent’s policy-learning pipeline",'文本游戏策略有动作轨迹和交互，但摘要没有确认 LLM 控制器；保留为模型身份不明。'),
('A49',X,'yes','no','high','The indexing-retrieval-generation paradigm','固定 RAG 流水线的安全基准；含 LLM 和外部知识并不自动构成 agent。'),
('A50',X,'yes','no','high','integrate retrieval evaluation and response generation into a single model','RAG 训练对齐与检索相关性奖励；没有环境/工具行动的反复执行闭环。'),
('A51',U,'yes','unclear','medium','constructing and simulating book-based multi-agent societies','LLM 社会模拟明确，但摘要主要介绍系统应用和故事质量，未说明角色如何观测、行动和获得环境反馈；严格口径保留不确定。'),
('A52',C,'yes','yes','high','layout verification, and iterative refinement','LLM 生成 C# 场景，进行布局验证和反复改进，反馈闭环直接服务生成任务。'),
('A53',C,'yes','yes','high','a planner for both high-level and low-level planning, and an executor to carry out tool usage','LLM 多步工具规划与执行是主要系统；跨工具推理及含噪工具环境评估支持行动反馈范式。'),
('A54',C,'yes','yes','high','closed-loop, interaction-driven training','明确 LLM agents 以 rollout 反馈驱动环境验证、任务生成和策略训练。'),
('A55',C,'yes','yes','high','end-to-end screenshot-to-action policies','VLM 计算机使用策略通过截图观测产生动作，环境交互轨迹与可验证奖励训练构成闭环。'),
('A56',C,'yes','yes','high','agents with varying moral dispositions perceive, remember, reason, and decide','明确 LLM 社会智能体进行感知、记忆、推理与决策，研究多轮主体互动的演化结果。'),
('A57',C,'yes','yes','high','a master LLM coordinates a grounding agent','主 LLM 规划调用定位/视觉子智能体并获得定向文本观测，形成有步数约束的交互推理轨迹。'),
('A58',C,'yes','yes','high','browses the internet, writes structured notes, and archives raw sources','LLM 长程研究流程执行浏览、写入及检索外部文件记忆，并迭代细化；属于明确工具行动系统。'),
('A59',C,'yes','yes','high','an expert agent interacts with the repository','研究 SWE 智能体的上下文验证器：专家 agent 交互采集代码库信息后生成评分标准，核心服务 LLM 编程行动工作流。'),
('A60',X,'yes','no','high','performs retrieval at both the cluster and document levels','个性化 RAG 的协同过滤与排序；分层检索不等同动态 agent 行动闭环。'),
]
assert len(L)==len(S)==60
assert {x[0] for x in L}=={x['audit_id'] for x in S}
lookup={r['audit_id']:r for r in S}; out=[]
for aid,cat,llm,loop,conf,quote,reason in L:
 r=lookup[aid]
 assert quote in r['abstract'],(aid,'quote is not an exact abstract substring')
 assert len(quote.split())<=25,(aid,'quote >25 words')
 d={k:v for k,v in r.items() if k!='abstract'}
 d.update(abstract_sha256=hashlib.sha256(r['abstract'].encode()).hexdigest(),abstract_word_count=len(r['abstract'].split()),category=cat,llm_or_vlm_core=llm,action_observation_loop=loop,classification_confidence=conf,evidence_quote=quote,evidence_field='abstract',rationale_zh=reason,reviewer_type='AI-assisted single-rater title-and-abstract reading',verified_scope='Quote matched against locally collected abstract; paper URL copied from official-source metadata. No new network/full-text verification.')
 out.append(d)
(P/'agent_abstract_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
with open(P/'agent_abstract_audit.csv','w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=out[0].keys());w.writeheader();w.writerows(out)
manifest=json.load(open(P/'sampling_manifest.json'))
def finite_population_interval(k,n,N,alpha=0.05):
    # Same exact integer Hypergeometric inversion as the source SciPy implementation.
    # n <= 17 in this frozen audit, so direct integer binomial arithmetic is practical.
    denom=math.comb(N,n)
    def probability(K, lower, upper):
        lo=max(0,n-(N-K),lower); hi=min(n,K,upper)
        return sum(math.comb(K,j)*math.comb(N-K,n-j) for j in range(lo,hi+1))/denom
    lower=next(K for K in range(N+1) if probability(K,k,n)>=alpha/2)
    upper=next(K for K in range(N,-1,-1) if probability(K,0,k)>=alpha/2)
    return dict(total_low=lower,total_high=upper,fraction_low=lower/N,fraction_high=upper/N)

summ=[]
for frame in manifest['strata']:
 r=[x for x in out if x['stratum']==frame['stratum']]; n=len(r);N=frame['eligible_abstract_papers'];c=Counter(x['category'] for x in r)
 k=c[C]; p=k/n; pu=(k+c[U])/n;f=n/N
 ci=finite_population_interval(k,n,N); ci_u=finite_population_interval(k+c[U],n,N)
 # Unbiased design variance estimator for sample proportion under SRS without replacement.
 v=(1-f)*p*(1-p)/(n-1) if n>1 else 0
 vu=(1-f)*pu*(1-pu)/(n-1) if n>1 else 0
 summ.append({**frame,**{f'n_{cat}':c[cat] for cat in [C,O,X,U]},'strict_central_sample_fraction':p,'finite_population_correction':1-f,'strict_proportion_design_variance_estimate':v,'strict_hypergeom95_fraction_low':ci['fraction_low'],'strict_hypergeom95_fraction_high':ci['fraction_high'],'strict_hypergeom95_total_low':ci['total_low'],'strict_hypergeom95_total_high':ci['total_high'],'strict_plus_unclear_sample_fraction':pu,'strict_plus_unclear_design_variance_estimate':vu,'strict_plus_unclear_hypergeom95_fraction_low':ci_u['fraction_low'],'strict_plus_unclear_hypergeom95_fraction_high':ci_u['fraction_high'],'estimated_strict_central_total_in_eligible_frame':N*p})
with open(P/'audit_stratum_summary.csv','w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=summ[0].keys());w.writeheader();w.writerows(summ)
N=sum(x['eligible_abstract_papers'] for x in manifest['strata']); weighted=Counter();unweighted=Counter()
for r in out:weighted[r['category']]+=r['inverse_probability_weight'];unweighted[r['category']]+=1
strict_se=math.sqrt(sum((h['eligible_abstract_papers']/N)**2*h['strict_proportion_design_variance_estimate'] for h in summ))
upper_se=math.sqrt(sum((h['eligible_abstract_papers']/N)**2*h['strict_plus_unclear_design_variance_estimate'] for h in summ))
agg={'sample_n':len(out),'eligible_frame_N':N,'unweighted_sample_counts':dict(unweighted),'weighted_frame_estimated_counts':dict(weighted),'weighted_frame_estimated_fractions':{k:v/N for k,v in weighted.items()},'unclear_descriptive_bounds':{'weighted_strict_lower':weighted[C]/N,'weighted_strict_plus_unclear_upper':(weighted[C]+weighted[U])/N,'meaning':'All unclear treated noncentral vs central; not a confidence interval or bound on other coding errors.'},'stratified_design_uncertainty':{'sampling':'Independent stratum SRS without replacement','finite_population_variance_formula':'Var(p_hat)=sum_h((N_h/N)^2 * (1-n_h/N_h) * s_h^2/n_h), s_h^2=n_h*p_h*(1-p_h)/(n_h-1)','weighted_strict_standard_error':strict_se,'weighted_strict_plus_unclear_standard_error':upper_se,'pooled_binomial_interval_used':False,'per_stratum_intervals':'Exact 95% equal-tailed hypergeometric inversion for unknown integer central total K; each interval marginal, not simultaneous. Finite population included exactly. Census stratum interval collapses to observed fraction.','caveat':'Variance plug-in is zero in observed zero-count strata; exact stratum intervals reveal nonzero uncertainty when n<N. These measure sampling uncertainty conditional on AI labels, not AI coding error, missing abstracts, lexical false negatives or source coverage.'},'strata':summ,'methods_warning':'Weighting represents only the title-positive/available-abstract/excluded-NeurIPS-2026 frame. Neither full-conference topic prevalence nor recall. Strict-plus-unclear is a classification-bound sensitivity, not a confidence interval. No pooled binomial CI is reported.'}
(P/'audit_summary.json').write_text(json.dumps(agg,ensure_ascii=False,indent=2))
print(json.dumps(agg,ensure_ascii=False,indent=2))
