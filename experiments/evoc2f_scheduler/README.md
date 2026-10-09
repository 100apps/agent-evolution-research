# EvoC2F 约束调度：合成机制实验

复现等级：`机制示例`，不是 StableToolBench、ToolComp 或论文主结果复现。

本实验仅验证 EvoC2F 论文中的一个机制主张：只有数据依赖的并行调度会遗漏共享资源上的读写/写写冲突；在 Plan IR 中补充资源访问、重试策略和幂等键后，可以在保留无冲突并行性的同时获得与串行基准等价的最终状态。

三个调度器使用完全相同的任务 DAG、延迟、失败注入和重试预算：

- `serial`：确定性串行拓扑执行，作为结果等价基准。
- `dependency_only`：仅尊重显式数据依赖并行执行，故意忽略副作用冲突。
- `effect_aware`：在数据依赖上增加读写/写写冲突边，允许读读并行。

合成任务包含：两个无数据依赖但同时写 `account` 的操作、独立 `inventory` 分支、一次“提交后瞬态失败”和带幂等键的重试。运行脚本会断言 effect-aware 结果等价于串行结果、重试未重复扣减库存，并记录 dependency-only 的资源冲突与最终状态差异。

运行：

```powershell
python run.py
```

输出：`results.json`、`runs.csv`、`run.log`。
