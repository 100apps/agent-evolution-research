# ACRouter：公开 OOD 矩阵的离线制品回放

## 定位

这是**公开历史矩阵的制品回放**，不是实时 Agent rollout，也不是论文端到端训练复现。脚本只读取固定提交中的 JSON 单元格，用独立的 Python 标准库实现策略；没有执行作者仓库代码、没有调用任何模型 API，也没有产生 API 费用。

## 固定输入

- 仓库：<https://github.com/LanceZPF/agent-as-a-router>
- 提交：`e43839edb0d5d0a9feec2f7078019406ab4d64bd`
- 制品：`data/matrices/phase2_ood/unified/matrix_acrouter_ood176.json`
- SHA-256：`f0fe49db24cf2c1d5552a1dd512544676825e0e4f34e136f194fecd9c022c15a`
- 规模：176 个任务、8 个模型。

## 回放规则

廉价链按 `MiniMax-M2.7 → kimi-k2.5 → gpt-5.4 → glm-5` 顺序读取；每次尝试都累加 JSON 中的 `cost_usd`，一旦 `resolved=true` 即停止。四者都失败且 `apply_ok` 计数不少于 2 时，再读取 `claude-opus-4-6`；若升级仍失败，最终 `chosen_model` 保留 `glm-5`。逐任务 oracle 是 `max_model(resolved - 0.1 × cost)`，策略效用中的成本为**所有已尝试模型的成本之和**。

## 运行

```powershell
py -3.12 run.py
```

脚本生成：

- `results.json`：原策略、单模型、无升级廉价链、无门控升级等汇总；
- `decisions.csv`：每个策略 × 每个任务的完整尝试、成本和 regret 审计轨迹；
- `run.log`：真实控制台日志。

## 解释边界

1. `cost_usd` 是制品中保存的历史估计，不是本次运行的收费。
2. 176 行由 `old112` 与 `new64` 合并；后者把若干新版本标签映射到旧标签，不能据此建立“当前模型排名”。
3. 该 JSON 的默认实现按任务 ID / 来源 / 维度映射回放，不等于论文描述的在线 0.8B embedding + k-NN 记忆投票全路径。
4. 制品参考值 `AvgPerf=73.30` 与 arXiv v3 Table 3 中的 `OOD=62.50` 是不同口径，报告中分开陈述。
