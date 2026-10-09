# 十会议增量与本仓库基础快照的兼容性

本仓库已发布的 ML/NLP 五会议 JSONL 与转移增量包 `conferences/comparison/source_corpus_manifest.json` 的输入 SHA-256 不同，虽然 ML 57,957、NLP/CV 25,380 和新增 6,193 条的记录数一致。因此 `verify_conference_addon.py --check-base` 在此工作树会失败；不修改清单或评分脚本来掩盖差异。独立的 `verify_conference_addon.py`（不加该选项）通过 81 个增量文件的哈希和结构检查。

在已发布基础快照上运行相同共同标题规则后，10 个数值 CSV 与增量包冻结输出逐字节相同，5 个 JSON 输出语义相等；来源 URL 清单和规范化语料字节不同。由此只主张本仓库输入上的聚合标题结果与增量数值一致，不主张原始标准化题录逐字节重放。增量包 60 篇摘要审计为单一 AI 阅读者冻结标签，不是独立专家真值或全会 Agent 比例。

新的逐篇目录从**本仓库实际五会快照**和新增 6,193 条元数据构建，保存自己独立的来源哈希、作者补充、分类与引用审计，见 [catalog/README_zh.md](catalog/README_zh.md) 和 `catalog/data/rebuild_receipt.json`。
