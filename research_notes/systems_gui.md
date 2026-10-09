# 系统与 GUI 论文分析

核验日期：2026-10-08。以下明确区分论文报告值、资料质量问题和建议实验。本次研究没有执行基准复现、模型训练或基础设施实验。

## 29. SE-GA: Memory-Augmented Self-Evolution for GUI Agents

论文：https://arxiv.org/abs/2605.16883
全文：https://arxiv.org/html/2605.16883
代码：https://github.com/jinshilong-dev/SE-GA

### 已核验的方法与证据

TTME 结合近期动作转移、通用规则和成功轨迹摘要，按指令及截图相似度检索。MASE 先做记忆感知 SFT，再使用改造后的 GRPO。Hindsight Goal-Shifting 将失败轨迹中已验证成功的前缀重新标注为子目标样本。实验底座为 Qwen2.5-VL-7B，使用 4,007 条轨迹及四张 A800。主要报告值为：ScreenSpot 89.0，AndroidControl-High 75.8，GUIOdyssey 步成功率 83.9，AndroidWorld 任务成功率 39.0。部分基线引用已有论文结果，没有统一重跑。论文给出的 RL 配置包括 LoRA rank 32/alpha 64、ZeRO-3，以及 6,144/1,024 的提示/输出长度上限。

原文存在内部不一致：表 2 的 AndroidControl-High 为 75.8，表 4 和第 5.4 节却为 73.8；附录表 7 的列标签也与主表中相同数值所对应的列不一致。这些问题同样出现在 PDF 印刷页码 7、8、21，并非仅为 HTML 转换错误。因此，不能将各表消融值直接拼接为同一实验设置。记忆持续增长、任务覆盖有限也是边界；未核实完整训练耗时与金额。[论文第 4–5 节及附录 A–C](https://arxiv.org/html/2605.16883)

### 代码与可复现性审查

官方仓库按 Grounding SFT → Planning SFT → RL 组织实际运行，比论文“两阶段”表述更细。仓库给出了 TTME 示例和分阶段训练入口，依赖 Python 3.11+、CUDA PyTorch、DeepSpeed、vLLM。[官方仓库](https://github.com/jinshilong-dev/SE-GA)

当前默认配置不是论文精确复现配置：SFT 学习率为 1e-6，RL 为 3e-6，RL 训练/评估数据上限为 200/20，gpu_num 为 2；论文报告的对应学习率为 2e-6、2e-5，并使用四张 A800。LoRA rank/alpha 与论文一致。应固定代码提交并逐项记录修改，不能直接运行默认配置后称为“完整复现”。[默认配置](https://github.com/jinshilong-dev/SE-GA/blob/main/configs/default.yaml)

### 建议的有限复现方案：尚未执行

首先在确定性的小型 GUI 轨迹集上独立验证检索。覆盖“相同指令、不同截图”“不同指令、相似截图”、陈旧上下文、干扰规则和失败前缀。固定 token 预算，对比仅近期历史、仅文本检索、文本与视觉混合检索。断言记忆中不含未来观察或留出任务答案，记录检索准确性与上下文长度。

确认数据和指标定义后，再评测小规模留出 Android 任务。严格区分定位准确率、步准确率、完整任务成功率；使用配对种子和 bootstrap 置信区间；固定模型、提示、步数限制与记忆容量。分别消融各记忆层和 Goal-Shifting。CPU 轨迹模拟只能展示机制，不能验证 7B 训练收益或论文分数。完整复现需要多 GPU 和 Android 模拟器；金额必须在实际试运行和当时报价确定后计算。

## 30. EvoC2F: Compiling Tool Orchestration for Efficient and Evolvable LLM Agents

正式出版页：https://proceedings.mlr.press/v306/wei26q.html
官方 PDF：https://raw.githubusercontent.com/mlresearch/v306/main/assets/wei26q/wei26q.pdf
视频原始链接：https://openreview.net/pdf?id=ZSGB91kMOG

### 已核验的方法与证据

Plan IR 显式声明数据依赖、效应、资源访问范围、重试策略和幂等键。语义编译器补充冲突顺序，使用改造后的 HEFT 调度，并结合限流及故障处理。成功轨迹生成候选技能，功能、契约和回归验证决定是否入库。正确并行的前提是效应和资源标注保守且有效。

五次运行的平均结果中，Claude-4-Sonnet 在 StableToolBench 上的 SoPR 为 72.2，ReAct 为 62.3；延迟为 5.5 秒与 16.9 秒。更接近的并行基线 LLMCompiler 为 67.0、6.1 秒。SoPR 对“Unsure”给半分，仅在 765 个可解问题上计算，因此不是普通二元成功率。ShortcutsBench 使用真实历史动作作为输入、缓存响应和模拟工具延迟。ToolSeq-500 中 356 个候选放行 134 个，成功率由 68.2 升至 75.0；取消验证门后回归率达 7.2%。跨域负迁移影响 12.3% 的任务。分布式扩展和 IR 开销仍有局限；本次未找到完整费用/训练预算或核实的官方实现。[论文第 3–6 节、表 1–7、附录 H](https://raw.githubusercontent.com/mlresearch/v306/main/assets/wei26q/wei26q.pdf)

### 建议的有限复现方案：尚未执行

三篇中，它最适合先做 CPU 机制实验。构造固定种子的模拟工具环境，包含读写资源、已知延迟、可重试错误和不可逆操作桩。对相同 DAG 比较串行、仅数据依赖并行、数据依赖加效应约束并行。将串行执行作为最终状态对照，检查无禁止的并发冲突、重试幂等、限流预算符合要求，并扫描并发度与资源竞争强度。标注不完整时应保守串行，不能伪造正确性保证。

候选宏技能使用独立留出验证器。故意加入过拟合、格式错误或改变副作用的候选，验证能否拒绝。同时记录入库后的收益与错误放行率。既与串行比较，也与最接近的并行基线比较。结果应标为“合成环境机制级复现”，不能声称复现了 72.2 SoPR、学习式规划或真实生产可靠性。完整复现还需要匹配模型/API 版本、基准缓存、评估器、数据划分、DPO/路由器配置和调用预算。理解伪代码不等于已经复现完整系统。

### 证据可用性

OpenReview 在云端要求浏览器验证，但正式 PMLR 页面提供的 PDF 可直接读取，已从 Download PDF 链接下载，无需解决验证。研究目录保存 evoc2f.pdf 与 evoc2f.txt。检索发现第三方玩具级复现，但本次没有核实官方源码仓库，也未将第三方结果用作论文有效性的证据。

## 40. DeepSeek Elastic Compute (DSec): A Sandbox Infrastructure for Effective Agentic Training at Scale

论文：https://arxiv.org/abs/2609.22978
全文：https://arxiv.org/html/2609.22978
已公开存储组件：https://github.com/kvcache-ai/AgentENV/tree/main/storage/overlaybd

### 已核验的方法与证据

DSec 是执行基础设施，并非智能体学习算法。它统一 FnCall、容器、microVM 与完整 VM；拆分环境层，按需加载镜像，并管理资源回收、CPU QoS 和持久 rollout 状态。十节点评测中，8,192 个容器任务约 35 分钟完成，冷 Docker 拉取超过 60 分钟，磁盘写入约减少 57%。环境层挂载耗时为 45 分钟，tar 解包为 79 分钟。Virtio-pmem/DAX 将主机峰值内存减少 40.2%；在 50% 后台负载下，CPU QoS 将延迟增幅由 45.2% 限制到 17.3%。

生产规模数字与受控实验必须分开。评测明确不包括与 RL 框架集成，因此不能推导出任务智能或端到端训练质量提升。实验 CPU、内存和存储条件明显超出普通笔记本。论文公开部分存储组件，但未证明整套生产编排器全部开源。访问控制仅缓解部分奖励投机，不是对内核故障或破坏行为的通用防御。[论文第 5–8 节](https://arxiv.org/html/2609.22978)

### 建议的有限复现方案：尚未执行

不建议在用户 Windows 电脑上模仿生产规模。无特权、可移植的模拟可以控制工作集比例和缓存复用，比较全量加载与按需加载的传输字节及物化工作量。模型应计入元数据、缓存未命中和写放大，并扫描镜像复用度与工作集比例。必须明确报告模拟量，不能包装为基础设施实测加速。

真实实验应放在授权的隔离 Linux 测试环境，固定内核、镜像、工具调用回放，区分冷/热缓存，分别测量启动延迟、获取字节、CPU 时间、内存积分与任务完成。性能测量旁必须保留正确性检查。安全策略、内核、网络和虚拟化变更需要单独授权。生产编排、容错和极高并发需要更大规模实验；单节点演示无法验证这些主张。硬件、存储和运行时间未确定前，无法可信估算费用。

## 补充论文：SkVM，位于合集之外

合集第 31 个视频在 06:15 明确引用 SkVM，链接为 https://www.bilibili.com/video/BV1qJZcBrE3p ，其简介给出 https://arxiv.org/pdf/2604.03088v3 。[arXiv 记录](https://arxiv.org/abs/2604.03088)确认标题为 SkVM: Revisiting Language VM for Skills across Heterogenous LLMs and Harnesses，作者为 Le Chen、Erhu Feng、Yubin Xia、Haibo Chen。它是补充下载文献，不是合集第 42 个视频。完整论文分析、官方代码审查和无付费复现方案见同目录 skvm_supplemental.md；没有运行实验。

## 跨论文判断

三篇优化层级不同：SE-GA 改变检索经验和学习策略；EvoC2F 改变可执行计划与入库技能；DSec 改变执行容量及状态生命周期，不能放在一个排行榜直接比较。

合理的组合系统应分别验证策略质量、动作语义正确性和基础设施正确性。某一层提速也可能放大另一层问题：更快并行会放大错误效应标注；更大经验库会增加泄漏风险；更多沙盒吞吐量也可能加快奖励漏洞利用。这些是值得验证的集成假设，并非三篇论文已经证明的结果。
