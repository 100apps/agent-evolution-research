# 论文影响与可读性元数据：来源核验与追加方案

核验时间：2026-10-09 UTC。适用对象：现有约 8.9 万篇 master CSV 与 Explorer。本文不估计总体指标覆盖率。

## 先交付什么

第一版应立即追加：引用数及来源/观测时间/状态、出版年龄、已缓存的 OpenAlex 归一化指标、官方录用/展示类别、OpenReview 链接、作者提供的代码/数据/附件链接及来源证据。浏览/下载没有可靠来源时留空并注明原因；不要等全覆盖才发布首份 CSV。

引用体现可观测的学术使用与注意力，浏览/下载体现平台使用；它们都不能直接判定方法是否成立、实验是否可靠或论文是否值得读。提供多维筛选和原始证据，不自动贴“垃圾论文”标签，不建立综合质量分。少引用也可能是论文新、领域小、数据库遗漏或版本尚未合并。

## 1. OpenAlex：第一优先，复用主采集器缓存

官方 work 字段可映射：cited_by_count、counts_by_year、publication_date、publication_year、updated_date、fwci、citation_normalized_percentile、cited_by_percentile_year、is_retracted。引用数来自其图谱成功匹配的引用；不是全球全部引用。counts_by_year 仅近十年，省略零值年份，不能相加代替 lifetime count。updated_date 是记录任何字段的最后更新，不是引文统计截止日。is_retracted=false 只表示该来源没有标记，不是“无问题认证”。[Work 字段定义](https://help.openalex.org/data/works/attributes/)

FWCI 使用出版年及随后三年的引用窗口，对同年、同类型、同子领域归一化，1 表示该基准平均值；新论文窗口尚未完整。citation_normalized_percentile 是相应百分位。仅接收来源提供的值；不能用不完整的 8.9 万篇重算后冒称官方指标。cited_by_percentile_year 只按年份比较，不得标成领域归一化。[引用与 FWCI 口径](https://help.openalex.org/data/works/citations/)

归一化百分位原始值的官方示例为 0.999948，显示为百分比之前先验证字段及量纲；保留原始值和字段路径。年百分位保留原始 min/max 对象，兼容旧缓存异形字段时隔离并标记，不猜测缩放。[官方旧字段文档中的数值示例](https://github.com/ourresearch/openalex-docs/blob/main/api-entities/works/work-object/README.md#citation_normalized_percentile)

截至本次核验，官方支持 per_page≤100、OR≤100。200 为弃用兼容行为，不宜依赖。大集合使用 cursor，记录 next_cursor 与完成状态；不能只拿第一页。按 ID 批量补字段，不重跑题名搜索。[分页](https://help.openalex.org/api/paging/)、[批量查找示例](https://help.openalex.org/how-to/api-recipes/)

匿名访问与浏览共用无 key 预算；预算按响应头和 credits 记录，不能把请求次数等同信用额度。本任务所有新增 OpenAlex 请求仍由 Windows 主采集器管理；本次研究没有调用 OpenAlex API、没有注册或申请 key。[认证与用量头](https://help.openalex.org/api/authentication/)

## 2. Semantic Scholar：精确 ID 的可选补充

官方 Graph schema 提供 citationCount、influentialCitationCount、externalIds、publicationDate/year、paperId/corpusId。influentialCitationCount 是其模型判定的引用子集，依赖可见全文，不是审稿质量分。FullPaper schema 没有通用文章 views/downloads 字段，也没有上述 OpenAlex 式领域/年归一化指标；本次不把网页上的其他概念假定为可用 API 字段。[Graph API](https://api.semanticscholar.org/api-docs/graph)、[机器可读官方 schema](https://api.semanticscholar.org/graph/v1/swagger.json)、[影响性引用解释](https://www.semanticscholar.org/faq#influential-citations)

本次仅执行 1 次匿名论文读取，ARXIV:1706.03762 返回 HTTP 200，externalIds.ArXiv 精确一致，返回 citationCount=196008、influentialCitationCount=20896、publicationDate=2017-06-12。响应 Date 为 2026-10-09T06:05:47Z；原始 JSON、SHA-256 与请求元数据已保存。这是一个字段/可用性探针，不是对本 master CSV 的覆盖验证，也尚未将其自动并入主表。

批量 /paper/batch 是读取性质的 POST，每次最多 500 ID/10 MB；fields 放 query 参数。缺失项逐项标记，禁止按不经核验的位置或题名拼接。匿名服务为共享限额且可进一步节流，不能据本次 200 承诺 8.9 万篇稳定吞吐。此任务没有申请凭证、付费或做大批量补抓。[API 概览](https://webflow.semanticscholar.org/product/api)、[官方请求建议](https://webflow.semanticscholar.org/product/api/tutorial)

## 3. arXiv：年龄、版本与链接，不能充当文章浏览来源

标准 Atom API 包含 ID、标题、作者、摘要、published、updated、分类、DOI/journal_ref/comment/链接等。published 是首版处理日期，updated 是所取版本日期；不要把更新日期当论文年龄起点。该标准字段集没有文章引用数/浏览数/下载数。[API 手册](https://info.arxiv.org/help/api/user-manual.html)

公开 usage 页面链接全站月下载、当日用量和机构下载统计。月下载只统计主站 web 使用并尝试去掉机器与快速重复下载；这种汇总不能分摊到单篇，也不能当文章浏览数。本次未找到可支持逐篇浏览/下载字段的标准公开 API，填 null + not_exposed，不能填 0。[usage 索引](https://info.arxiv.org/help/stats/index.html)、[月下载定义](https://arxiv.org/stats/monthly_downloads)

本次没有调用 arXiv API。将来需要时由单一调度器控制全部机器合计，每次间隔至少三秒、单连接，缓存相同查询；本轮不用它补不存在的 metrics。[官方速率条款](https://info.arxiv.org/help/api/tou.html)

## 4. OpenReview 与会议缓存：决定可先加，评分需真实载荷和量表

便利样本核对了 4 份会议 JSON 各前 20 条和 1 个 CVPR 页面。ICLR 2024/2025、ICML 2025、NeurIPS 2025 对象确有 decision、paper_url、eventmedia、可空 url；样本未有 rating/confidence/review 字段。ICLR 2025 的官方目录明确给出 dcpt GitHub 链接；另有只在摘要出现的代码链接。NeurIPS 的代码+数据 DOI 例子属于 Datasets and Benchmarks track，不能混进 main。目录活动有重复，decision=oral 与 eventtype=Poster 可并存。这里只证明字段可抽取，不估计总体覆盖。[ICLR 2025 原始目录](https://iclr.cc/static/virtual/data/iclr-2025-orals-posters.json)、[NeurIPS 2025 原始目录](https://neurips.cc/static/virtual/data/neurips-2025-orals-posters.json)

正式 review/decision 应按已有 forum ID 获取公开 note，保留 note.id、forum、replyto、invitations、content 原值；实际 invitation 决定哪个字段是 rating/confidence/decision，并提供 rubric。只可在同 venue、year、track、round、rating field 和相同量表的组内比较。不要把评审质量 rating 当论文 rating，不推断匿名评审真实身份。[Notes 获取](https://docs.openreview.net/how-to-guides/data-retrieval-and-modification/how-to-get-all-notes-for-submissions-reviews-rebuttals-etc)、[邀请模板](https://docs.openreview.net/reference/api-v2/entities/invitation/types-and-structure)、[评审质量评分](https://docs.openreview.net/how-to-guides/data-retrieval-and-modification/how-to-get-reviewer-ratings)

本环境对一个论坛的读取返回 HTTP 403 后已停止，尚无真实 review/rubric 载荷。它不能证明论坛不公开或 API 全面不可用，记录 access_denied。可见 note 的个别字段也能有独立访问权限。[字段权限](https://docs.openreview.net/reference/api-v2/entities/note/fields)

## 5. 可复现性与完整性：证据链接优先

代码/数据/模型链接分别记录 kind、作者/会议提供或第三方关系、linked_from、原字段、证据文字、采集时间。仅见链接填 link_observed；未访问不能填 reachable，更不能填“复现成功”。PDF/supplement、GitHub star、视频播放都不能等同代码可复现性或文章浏览。

OpenAlex is_retracted 可先保留。撤稿、修正、关注声明、withdrawal、reinstatement 要分事件和时间，并保留原 DOI、notice DOI/URL、来源；不要把修正等同撤稿。Crossref 的 update-to 与 Retraction Watch 官方公开数据可做以后 DOI 精确补充，注意原文 DOI 和通知 DOI 的方向；不是本轮新增采集依赖。未发现记录不证明没有事件。[Crossref Retraction Watch](https://www.crossref.org/documentation/retrieve-metadata/retraction-watch/)、[更新关系过滤器](https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/)

## 交付与范围

metrics_schema.json 是可验证的 JSON Schema（draft 2020-12），附 6 个首版追加列及 2 个仅真实可用时才启用的可选使用量列；完整逐来源观测放 impact_metrics_json。collector_plan_zh.md 定义离线优先、精确 ID join、缓存/配额/分页/回归验证。openreview_sample.* 保存实际小样本证据；semantic_scholar_probe.* 保存实际单条探针。首版零新增网络即可发行带 missing 状态的完整主表；后续按 paper_id 增量回填，不变更既有分类、行数或 track 口径。
