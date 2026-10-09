"""Build concise Chinese methods/results memo from the verified common tables."""
from pathlib import Path
import csv,json,hashlib,zipfile
P=Path(__file__).resolve().parent
read=lambda f:list(csv.DictReader((P/f).open(encoding='utf-8-sig')))
h={r['topic']:r for r in read('fixed_basket_headline_deltas.csv')}
v={(r['venue'],int(r['year']),r['topic']):r for r in read('venue_year_topic_counts.csv')}
c={(r['venue'],int(r['year'])):r for r in read('coverage_common.csv')}
d={r['topic']:r for r in read('change_decomposition.csv') if r['from_year']=='2020' and r['to_year']=='2025'}
lines=['# 十个会议的统一标题词汇趋势：方法与结果（2020–2026）',
'\n快照：2026-10-09 UTC。规则版本 common-title-v1.0。仅分析已采集的实际本地元数据；本次未联网、未重采集、未访问 arXiv。先前各采集组的结果完全保留。本文件使用一套新统一规则，数字不能与旧规则的分子拼接。',
'\n## 最重要的结论',
'1. 2020–2025 固定九会议篮子由 6,476 篇增至 17,907 篇。语言模型相关词汇、生成、多模态、推理/测试时计算、智能体词汇的标题占比上升；这一结论在论文加权与会议等权两种权重下均成立。',
'2. 2026 应逐会议配对，不能追加到九会议总曲线上。ACL 大模型明确词汇的篇数继续增加、占比却下降；CVPR diffusion 词汇篇数与占比均低于 2025。不存在所有热点都单调上升的统一故事。',
'3. 广义 agent 词汇不等于现代 LLM agent。2025 九会议中广义词汇为 597 篇，而要求同时具有语言模型上下文的较严格词汇交集只有 194 篇。这两个数字都不是经过语义验证的自治智能体数量。',
'4. 理论/优化词汇的篇数 667→1,735，论文加权占比 10.30%→9.69%，会议等权占比却 7.15%→7.49%。不能把一个加权占比下降写成研究者离开理论领域。',
'\n## 1. 样本与比较边界',
'共有 89,530 个 venue-year-ID 唯一记录，含仅供审计的 NeurIPS 2026 暂定不完整项目 5,522 篇。统计单位是会议年份中的论文记录，不是独立作者、研究者人数或全计算机科学。原会议轨道边界沿用经过检查的采集结果：ML 主轨、ACL main long+short、CVPR 主会、KDD research、SIGIR full/long、ICSE technical/research、OSDI research、SOSP main research。各会主轨不完全等同，比较的是这些明确限定的文献集合。',
'\n|会议|2020|2021|2022|2023|2024|2025|2026|\n|---|---:|---:|---:|---:|---:|---:|---:|']
for venue in sorted(set(k[0] for k in c)):
 vals=[str(c[venue,y]['n_records']) or '无届' for y in range(2020,2027)]
 if venue=='NeurIPS':vals[-1]+='（暂定，排除）'
 if venue=='OSDI':vals[-1]+='（结构断点）'
 lines.append('|'+venue+'|'+'|'.join(vals)+'|')
lines.extend(['\n固定篮子为 ACL、CVPR、ICLR、ICML、ICSE、KDD、NeurIPS、OSDI、SIGIR，2020–2025 每年均有样本。SOSP 在 2020/2022 无届，不能填零；仅列各有效届数据，2026 可与 2025 配对。',
'- NeurIPS 2026 的 5,522 是去重后的不完整会前项目，不能作为完整发表/录用分母。它仅出现在分会年审计表，所有趋势差分均排除。',
'- OSDI 2026 已排除 19 篇新 Operational Systems，保留 117 篇 research；但首次多轨、接收政策及原 ATC 范围变化仍构成结构断点，单列，不能归因于主题挤出。',
'- CVPR 2026 索引 4,042 篇，官方公布接收 4,089 篇，差 47；SIGIR 2026 逐项列出 233 篇，页面声称 234，差 1。采用实际可见记录，不补造题目。前者原因未明；后者是初始接收通知快照。',
'- ACL 2020/2021 各两篇有撤稿标记，主分析按历史目录保留；每条标准化记录保留 publication_status。原 ACL 数据另有排除撤稿的敏感性结果。',
'\n## 2. 共同测量方法',
'所有年份与会议一律只用 title，绝不把有摘要的年份和没有摘要的年份混算。标题先 NFKC、casefold，再把非 ASCII 字母/数字转为空格并压缩空白。此规则对英文题目透明，但会丢失非拉丁字符。正则表达式两端加词边界。每个标签通常是多个规则的 OR；并集和交集另以 any_of/all_of 声明。标签非互斥，合计可以超过 100%，也没有声称穷尽所有研究方向。',
'分会年占比 = 命中标题数 / 该会年全部入组标题数。论文加权汇总 = 九会命中数之和 / 九会论文数之和；会议等权汇总 = 九个分会占比的算术平均。等权会让 53 篇的 OSDI 和 5,286 篇的 NeurIPS 拥有相同权重，因此这是另一种描述视角，不是天然更准确。',
'变化分解采用对称 Kitagawa 恒等式：总占比变化 = Σ[平均会议权重 × 会内占比变化] + Σ[平均会内占比 × 会议权重变化]。前者称会内成分，后者称权重成分。它是描述性算术分解，没有因果或人员迁移含义；所有主题的残差绝对值均 < 1e-10 个百分点。',
'完整规则见 common_topic_rules.json。paper_topic_matches.jsonl 保留每个命中的文本、开始/结束坐标和组合标签的组成标签；坐标是标准化标题中的 0-based 半开区间，原始题目同时保留。source_corpus_manifest.json 对三份输入、覆盖说明及脚本记录 SHA-256；可据此识别不同重采集快照。',
'\n## 3. 最容易混淆的定义',
'- modern_foundation_llm：明确的 large language/foundation/large multimodal/LLM/VLM 等及少量模型家族词汇。这是现代命名词汇，不是所有预训练或大模型研究。2020 该严格规则恰为 0，甚至《Language Models are Few-Shot Learners》也不会命中，因为题目没有所列明确词汇。这种 0 绝不能解释为当年没有大模型。',
'- historical_pretrained 单列 BERT、RoBERTa、T5、XLNet、GPT-2、pretrained language model 等。modern_or_historical 为二者并集。更宽的 language_model_context 还纳入通用 language model 措辞，提供另一种基线敏感性。历史名字减少可能反映命名替换，不能证明方法被抛弃。',
'- agents_broad 纳入 agent/agentic/multi-agent/tool-use/tool-calling/web-navigation/computer-use；不把单独 memory、planning 或 inference 当成智能体。agents_language_action_strict 必须同时命中 language_model_context 与 agents_broad。交集仍无法验证观察—行动反馈、工具真实使用、自治性或实验环境。',
'- pretraining_explicit 是 pretraining/pre-train 过程措辞；pretrained_usage_cue 是 pretrained/pre-trained 形容词措辞。后者不能证明仅仅使用现成模型，前者也不能证明作者实际从头训练。两类避免把“预训练模型应用”全部记成“预训练研究”。',
'- posttraining_named_broad 含 post-training、RLHF/RLAIF/DPO/GRPO/RLVR、偏好优化、reward model 等；posttraining_model_context 额外要求语言模型或明确生成模型上下文。泛化 fine-tuning/instruction-tuning/LoRA/adapters 另列 finetuning_adaptation，不自动等同后训练。严格规则会漏掉标题省略模型上下文的真实后训练论文。',
'- 推理标签含非 LLM 的空间/因果/符号 reasoning。testtime_compute 单独识别测试时计算/搜索/扩展与 test-time training，不把所有 inference 或 test-time adaptation 混入。',
'- 效率词汇不自动意味着 AI；推理服务/GPU标签不纳入单独的统计 inference。安全标签含传统稳健性、公平、隐私和安全；已排除单独 bias/alignment，避免把归纳偏置或几何对齐误称为 AI 安全。diffusion 仍可能含图传播，coding 可能含编码理论，不能在未审阅题目时作更窄解释。',
'\n## 4. 2020→2025 同篮子结果',
'以下分子均由共同规则重算；每行分母依次为 6,476 和 17,907。',
'\n|词汇主题|2020 命中数 / 占比|2025 命中数 / 占比|论文加权变化 pp|会议等权 2020→2025|\n|---|---:|---:|---:|---:|'])
keys=['modern_foundation_llm','modern_or_historical','language_model_context','reasoning_testtime','agents_broad','agents_language_action_strict','pretraining_explicit','pretrained_usage_cue','posttraining_named_broad','posttraining_model_context','retrieval_recommendation','coding_software','generative','diffusion','multimodal','efficiency','inference_serving_gpu','theory_optimization','traditional_statistics','evaluation','safety_security']
for t in keys:
 r=h[t];f=lambda k:f"{float(r[k]):.2f}"
 lines.append(f"|{r['label_zh']}|{r['count_2020']} / {f('pooled_2020_pct')}%|{r['count_2025']} / {f('pooled_2025_pct')}%|{float(r['pooled_delta_pp']):+.2f}|{f('equal_venue_2020_pct')}%→{f('equal_venue_2025_pct')}%|")
lines.extend(['\n现代明确词汇 +15.63pp 中，会内成分 +15.65pp，会议权重成分 −0.02pp；因此不是只因 ML 大会扩容而造成的汇总假象。推理/测试时 +3.35pp 中，会内 +3.32pp，权重 +0.02pp。理论/优化 −0.61pp 则是会内 −1.58pp 与权重 +0.97pp 的合成；会议等权又略升，正说明解释必须声明权重。',
'统计/概率词汇的占比 5.37%→3.95%，但篇数 348→707。生成词汇由 305→2,028，多模态由 89→1,302。这里能讨论的是标题关注点和产出结构变化，而不是单凭分母扩张证明某一方法“死亡”。',
'\n## 5. 2026 只作有效同会配对',
'下表均为 2025→2026 占比；完整分子、分母在 paired_2025_2026.csv。SOSP 单届规模较小，几个题目即可移动多个百分点。',
'\n|会议|现代明确词汇|推理/测试时|广义智能体|严格语言上下文+行动|\n|---|---:|---:|---:|---:|'])
for venue in ['ACL','CVPR','ICLR','ICML','ICSE','KDD','SIGIR','SOSP']:
 vals=[]
 for t in ['modern_foundation_llm','reasoning_testtime','agents_broad','agents_language_action_strict']:
  x=v[venue,2025,t];y=v[venue,2026,t];vals.append(f"{float(x['share_pct']):.2f}%→{float(y['share_pct']):.2f}%")
 lines.append('|'+venue+'|'+'|'.join(vals)+'|')
lines.extend(['\n- ACL：现代明确词汇 654/1,699→828/2,296，篇数增加、占比 38.49%→36.06%；推理/测试时 137→392，广义智能体 114→294。更精确的描述是其内部重点重排，不能写成所有大模型指标同步上升。',
'- CVPR：diffusion 342/2,871（11.91%）→337/4,042（8.34%）。这与原 CVPR 词典的 343→338 不同，原因是本共同规则只匹配完整 diffusion 词，而旧规则还含 score-based 等措辞；两年分别有一篇只以 score-based 命中旧规则；两套结果应独立展示，不能混接。',
'- ICSE：现代明确词汇 57/245→88/321（23.27%→27.41%）；广义智能体 7→30。仍然是软件工程会议中的重叠主题，不是这些论文从软件工程领域“消失”。',
'- SOSP：推理服务/GPU标题 9/66→14/62（13.64%→22.58%），现代明确词汇反为 12/66→10/62（18.18%→16.13%）。两个不同词典捕捉的是不同角度，不能互相代替。',
'- OSDI 另表：research 53→117，现代明确词汇 4→13（7.55%→11.11%），推理服务/GPU 5→19（9.43%→16.24%）。制度/范围断点已知，保留结果但不纳入可比 2026 汇总。',
'\n## 6. 传统方向按会议单列，不能与 AI 划为互斥阵营',
'\n|会议与标题词汇|2020|2025|2026|\n|---|---:|---:|---:|'])
for venue,t in [('ACL','nlp_translation_syntax'),('CVPR','vision_recognition_detection'),('CVPR','vision_geometry_rendering'),('ICSE','software_testing_analysis'),('KDD','mining_temporal_anomaly'),('SIGIR','retrieval_recommendation'),('OSDI','systems_storage_networking'),('SOSP','systems_storage_networking')]:
 vals=[]
 for year in [2020,2025,2026]:
  r=v.get((venue,year,t));vals.append(f"{r['count']}/{r['denominator']} ({float(r['share_pct']):.2f}%)" if r else '无届')
 lines.append('|'+venue+' '+h[t]['label_zh']+'|'+'|'.join(vals)+'|')
lines.extend(['\nACL 传统翻译/句法标题下降，同时旧任务可能被合并到通用模型框架且不再出现在题目中。ICSE 测试/分析/修复、SIGIR 检索/推荐的绝对数没有随 LLM 词汇上升而消失。OSDI/SOSP 标题常只有系统名，词典漏检尤其可能；“没有命中”不等于“没有 AI”或“没有传统研究”。',
'\n## 7. 来源、复现与验证',
'三份输入：ml/metadata_main.jsonl、nlp_vision/papers_main.jsonl、systems_ir/combined_papers.jsonl。标准化层共 89,530 条，无 venue-year-ID 重复。全部标签命中数不超过分母；严格 agent/后训练标签均为其广义标签的子集。test_compare_titles.py 的 6 项回归测试通过，覆盖旧/新模型词汇、预训练措辞、agent 交集、后训练上下文、歧义排除及命中坐标。它验证程序行为，不是人工标注的准确率/召回率评估。',
'Python 3.9+，仅标准库，无网络请求，无密钥；Windows 命令：',
'\n    py -3 -X utf8 compare_titles.py --root C:\\path\\to\\conferences',
'\n输出默认写入 root/comparison。可使用 --output 指定新目录，--input FILE 重复传入同结构 JSONL，--rules 指定替代规则，--skip-paper-audit 跳过大型命中明细。重采集会改变语料，必须保留新旧源哈希，不可把旧统计冒充新快照。',
'关键小文件：fixed_basket_headline_deltas.csv、fixed_basket_2020_2025.csv、coverage_common.csv、paired_2025_2026.csv、osdi_2026_scopebreak_separate.csv、change_decomposition.csv；全部分会年结果见 venue_year_topic_counts.csv；公开来源逐会年列在 source_urls_by_venue_year.csv。大型 normalized_title_corpus.jsonl 和 paper_topic_matches.jsonl 用于逐标题审计，不必随小包转移。',
'主要一手来源：ICML [PMLR](https://proceedings.mlr.press/)，[NeurIPS proceedings](https://papers.nips.cc/)，[ICLR 官方项目](https://iclr.cc/virtual/2026/papers.html)，[ACL Anthology XML](https://github.com/acl-org/acl-anthology/tree/master/data/xml)，[CVF CVPR](https://openaccess.thecvf.com/CVPR2026?day=all)，[SIGIR 2026 accepted papers](https://sigir2026.org/en-AU/pages/program/accepted-papers)，[KDD 2026 papers](https://kdd2026.kdd.org/papers/)，[ICSE 2026](https://conf.researchr.org/track/icse-2026/icse-2026-research-track)，[OSDI chairs message](https://www.usenix.org/sites/default/files/osdi26-message.pdf) 与 [CFP](https://www.usenix.org/conference/osdi26/call-for-papers)，[SOSP 2026 accepted list](https://sigops.org/s/conferences/sosp/2026/accepted.html)。精确实际请求地址以来源表为准。',
'\n## 8. 结论的外推边界',
'这是选定会议正式/接收目录的标题词汇调查。不能直接代表研究者在社交平台讨论什么、研究工时/资金/影响力、整个计算机科学、个人转向、产业采用或因果替代。标题命名习惯、轨道定义、会议容量、接收政策、接收与出版时间差均可影响结果。没有做分层人工摘要/全文标注，因此不宣称词典的语义精度已经验证，也不提供会造成虚假精确感的语义置信区间。继续研究应先做分层人工审计，再扩大到引文、作者/机构、摘要及项目层面的证据。'])
(P/'README_zh.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('README bytes', (P/'README_zh.md').stat().st_size)
