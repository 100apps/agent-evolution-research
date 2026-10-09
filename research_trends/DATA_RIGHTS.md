# 来源权利与再利用边界

本目录为核验 2026-10-09 UTC 的研究快照保存公开查询响应、会场目录、来源 URL 和哈希。**公开可读不等于本仓库拥有上游内容版权，也不构成本仓库对第三方内容的再许可。** 研究脚本、解释文字、第三方数据和原论文各自的权利应分开判断；本仓库不设置覆盖它们的统一许可证。

| 来源 | 本目录保存的内容 | 已核对的来源说明与边界 |
|---|---|---|
| [OpenAlex](https://help.openalex.org/data/how-its-built/) | API 计数和少量元数据响应、查询审计 | OpenAlex 将其数据声明为 CC0；这不改变其索引的论文全文或单篇开放获取副本可能另有许可证。 |
| [arXiv API](https://info.arxiv.org/help/api/tou.html) | 计数查询的 Atom 响应和少量候选元数据；**不含论文 PDF/源文件** | arXiv 允许按 CC0 使用描述性元数据，但论文正文各有权利。重新采集须遵守同页的单连接与至少三秒间隔等限制，不得绕过限流。感谢 arXiv 提供开放互操作数据。 |
| ACL Anthology、CVF、PMLR、NeurIPS、ICLR 官方目录 | 各会场公开题录页/XML/JSON 的时间戳快照，标准化标题和部分摘要 | 这些来源及各论文的权利不由本仓库授予；逐文件官方 URL 在采集 manifest 和 coverage 中。下游转载全文、图片或摘要应查看对应来源与论文的权利声明。 |
| NSF、LinkedIn、Stanford HAI 等辅助来源 | 引用、来源 URL 与少量转录数字 | 原报告/PDF 的权利保留给发布者；本目录没有把它们当成全球月度研究者普查。 |

若只需核对数字，先运行 `tools/research.py trends-validate` 与 `trends-rebuild`；无需重新下载第三方内容。引用结果时请同时写明来源、快照日、分类规则 SHA、查询时间与所用分母。新抓取会形成**另一份快照**，不能悄悄替换此目录中的 expected/actual。
