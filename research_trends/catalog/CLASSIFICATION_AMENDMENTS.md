# 标题规则修订与负面证据

五层分类树 `taxonomy.json` SHA-256 为 `e3289464ff67fd7cf470c1525a880eaa7d3a6e8a44837dc5acd75844aa2248eb`。首轮 v1.0 规则 SHA-256 `a1de4cf5d8bddbf861b4d8ce9a404e924d19f5ebf24e4621dc924963ab1d252c`，保留在 `pilot_title_rules_v1.0.json`；初始输出 15,594 条候选。抽检显示通用 LLM 词项会把仅使用 LLM 的论文误作“模型构建”贡献，也把宽泛 agent 提及误作 Agent 应用。没有删除这次不利运行，原计数见 `pilot_v1.0_receipt.json`。

v1.1 收紧 M.01.01、M.01.02 与 A.01.01 的条件词，规则 SHA-256 `825294f2e5e5e64d4fe6f6f941f9015e629c12616c6f72aa08cad5d5fb5232ec`。全量使用同一 v1.1 规则，7,656 条标题命中，81,874 条证据不足。`classify_titles.py` 的最终运行在**原样存储的标题**上确定 Unicode 字符位置，避免 NFKC 规范化导致证据 span 与原文不一致；最终赋值 CSV SHA-256 `f250deda72e63eabacef0afa8cda9e36fb6219b790e6445c68fb27cb58923a0f`。

规则命中只标 `classification_label_status=candidate` 和 `review_status=automated`；单人或 AI 辅助审阅不能被描述成独立专家金标准。未命中为证据不足，不能当作否定分类。一级/二级仅由命中三级叶节点的祖先闭包计算，不因引用词或背景使用自动添加标签。能源与芯片等层在所选会议中可能几乎无候选，不能推导行业活动为零。

后续审核发现两类尚未解决的标题规则边界，未修改已发布分类或抹去这些例子：`A.02.04` 的 text-to-image 触发词可能把一般生成任务误归入该细类；ReAct、Reflexion 等名称若标题未明确展示本规则要求的机制词，仍会弃权为“证据不足”。因此细类命中是候选，不是确认论文贡献；弃权也不是否定。做细类比较前须按同一规则补充独立人工语义审阅，并记录误报与漏报。
