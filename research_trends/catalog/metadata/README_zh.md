# 本地论文元数据审计与补充

**本仓库适配：** 五会冻结快照使用 `ml/raw/iclr_20??.json`、`icml_20??.html`、`neurips_20??.html` 及 `*_program.json`，提取器已仅调整这些本地文件名匹配。这里的最终覆盖率以 `../metadata_snapshot/coverage.json` 为准；另用仓库现有的 `conferences/build_author_enrichment.py` 从同一来源补齐 7,864 条有序作者名。下文关于转移环境原始文件名的示例仅描述原工具来源，不是本仓库的运行命令。

本工具只读取已保存的本地来源，不联网，不访问 arXiv，不调用 OpenAlex，也不发布任何文件。使用 Python 3.9+ 标准库。它负责元数据恢复和字段证据，不替代主 CSV 的三级多标签分类或 Explorer 实现。

## 输入与口径

三份会议主记录：
- ml/metadata_main.jsonl：57,957 条
- nlp_vision/papers_main.jsonl：25,380 条
- systems_ir/combined_papers.jsonl：6,193 条

总计 89,530 个“来源出现记录”，并非已经跨来源去重的论文数。保留全部既有记录，包括已标记为临时/不完整的 NeurIPS 2026。原始专题研究图 agent_evolution_map.json 另有 39 条，作为单独 Original39 来源；没有把视频评论、Tax AI 工程文章或其他附件自动扩进来。

输入的年份为会议届次。会议届次、arXiv 版本日期、会议日程日期、出版日期必须分列，不能混用。没有年份的原始专题论文不会根据 arXiv ID 或视频日期自动填入出版年份。

## 离线运行

示例命令（路径可自由调整，Windows 使用 py -3 -X utf8）：

    py -3 -X utf8 enrich_local_metadata.py --conferences-root "D:\repo\research_trends\conferences" --original39-root "D:\corpus\bilibili_papers" --original39-supplement original39_manual_supplement.json --output-dir "D:\repo\metadata_enrichment" --gzip

仅需要移交补充字段时，加 --patch-only：只生成压缩 patch、覆盖率、来源清单和示例，不重复输出大体积的完整 JSONL/CSV。

不包含原 39 篇时，省略两个 original39 参数。会议目录下须保留三份规范化输入；原始快照按原有 raw/ 和 systems/ 相对结构放置。原快照缺失时，字段恢复能力会下降；可用预计算 metadata_patch.jsonl.gz 作为已有快照的补充结果，不能声称在没有快照的电脑上重新验证了原始来源。

每个被消费文件均计算 SHA-256。source_manifest.json 的路径以 conferences/ 或 original39/ 开头，是逻辑根路径，不依赖原云端绝对路径。

## 输出

- metadata_enriched.jsonl.gz：逐来源完整元数据补充结果，含摘要、原始作者字符串、作者顺序、作者—机构链接、字段状态和证据。
- metadata_patch.jsonl.gz：适合移交主 CSV 构建器的补充结果，省去重复的题名、摘要和 authors_raw，其余元数据与证据保留。题名、摘要和原始作者字符串应继续取自原输入。字段证据使用 source_ref 引用 source_manifest.json 中唯一的 source_id；通过清单取得相对路径、SHA-256 和来源 URL，避免逐行重复大段证据。
- metadata_compact.csv：UTF-8 BOM CSV；authors 仅存按顺序排列的作者名，institutions、countries、dedup_identifiers 使用 JSON 字符串存入单元格；metadata_sidecar_ref 对应丰富 JSONL 中的 occurrence_id。多机构关联和完整字段证据只放侧车文件，避免 CSV 膨胀。
- coverage.json：总量、逐会议、逐会议年份、字段有值比例、字段状态、作者槽位层面的机构/国家覆盖、原规范化输入基线。
- source_manifest.json：源快照相对路径、SHA-256、字节数、已知来源 URL 和获取时间。
- examples.json：每个来源一个完整示例。
- original39_manual_supplement.json：原 39 篇本地一手来源的人工核对补充，保留版本和缺失原因；不把评论内容当作作者/机构证据。

主 CSV 合并键应为 venue + year + track + source_paper_id。source_paper_id 在不同会议/年份之间未必全局唯一，不能单独使用。occurrence_id 是上述出现记录的确定性标识。原 39 篇使用 Original39 + inventory_index。

## 作者与机构

1. ACL：用完整 Anthology paper ID 定位 XML paper 节点，恢复作者顺序、逐作者 affiliation 和 bibliographic 月份。XML 的会议 address 是举办地点，不是作者国家，完全不用于机构国家。
2. CVPR：用精确论文 URL 定位 CVF index 区块；从逐作者检索表单恢复顺序。2020 的字段名是 query，后续主要为 query_author。索引通常不含机构，因此机构为空。
3. ICML：PMLR 本身保留作者顺序。只有 PMLR 索引显式链接的 OpenReview ID 才能关联程序数据。出版 published 字段单独恢复为日精度。
4. ICLR / NeurIPS：优先使用精确 OpenReview ID，或 NeurIPS 源记录 UID 对照 proceedings hash。没有可靠 ID 桥接时，不用题名猜测所属程序记录。NeurIPS 作者可直接从 proceedings index 恢复。
5. ML 的 institution 字段嵌在 API user/profile 对象内；ICSE 的 prog-aff 来自程序/作者 profile 展示。两者都标为 publication_time_unverified。它们可以展示为“来源报告的机构”，但不能假装是出版当年的机构，也不用于历史国家推导。
6. KDD、SIGIR、SOSP 仅解析源内明确的分号、冒号、括号关系；复合机构名称按原文保留，不凭 and 或 / 拆成规范机构。SOSP 中只有后一个名字带括号的组，不把机构向前扩散给未明确标注的其他作者。
7. OSDI 已有作者—机构混合字符串，但姓名与机构均用逗号，且机构名本身也含逗号。当前版本保守保留 authors_raw，结构化作者和机构为空。Explorer 应能显示原文，并标注“待结构化”，不要将空列表显示成“无作者”。

institutions 是来源机构标签的去重列表，不是规范化机构实体库。authors[*].affiliations 保留作者关联和多重机构；author_affiliation_completeness 区分完整、部分、缺失。paper_scoped_institution_papers 指至少一位作者有论文级机构证据，不等于全体作者机构已完整。

## 国家/地区

只接受论文级 affiliation 中明确出现的完整地点字段，例如 “Example Lab, Beijing, China” 中的 China。词典只做明确国家/地区文本到代码的规范化，不根据机构总部、姓名、大学名称、会议举办城市、邮箱后缀或今天的 OpenAlex 机构数据猜测。

“University of Science and Technology of China” 不能因此得到 CN；“National University of Singapore” 不能因此得到 SG。ML/ICSE profile 机构即使文本带国家，也因历史有效性未证实而不能填历史国家。HK/TW 等作为来源报告的国家/地区代码保留，不把该字段解释为国籍或个人身份。

空值必须保留为空，并与 field_provenance.countries.missing_reason 一起展示。国家相关图表必须同时给出有国家记录数/总记录数，不能把未知当其他国家，更不能把很低覆盖的子样本当全球分布。

## 标识符与去重

每个 doi / arxiv_id / openreview_id 都有字段状态。只有 dedup_identifiers 中的键可用于跨来源连接；其他非空 ID 只是保留已有记录的报告值。

原始采集器曾在部分 ICML/NeurIPS 的程序补充、SIGIR 的 proceedings 补充、SOSP 的 accepted→final 链接中使用规范化题名匹配。本工具不会将这些继承字段自动提升为“已验证跨来源 ID”。不做新的题名模糊合并，也不按第一作者、题名 hash 或机构名跨来源合并。

paper_entity_id 是已验证精确标识符连接分量的 ID；它不是“所有真实重复均已消除”的保证。相同实体的来源出现记录全部保留。若 entity_identifier_conflict=true，应人工复核，不能直接汇总为一个唯一论文。未连接不证明两篇不同，只表示当前证据不足。

## 日期与摘要

- publication_date 配合 date_precision 和 date_type；年月精度不得补成当月 1 日。
- program_date 是程序 session 的 starttime，不是投稿/接收/出版日期。
- version_date 是原 39 篇 arXiv PDF 头部的版本日期，不是首次提交日期。
- 一部分 NeurIPS 旧摘要继承自上游题名对照，因此在无法用 ID 复核时保留 inherited_upstream_title_join_possible。
- 覆盖率里的“非空摘要”只表示该既有字段有内容，不证明其版本或链接逐条人工验证。

## 验证

    py -3 -X utf8 -m unittest discover -s . -p "test_*.py" -v

源内存在两个空姓名槽位：保留其位置并标记 name_status=missing_source_name，不创造姓名，不把其他人的名称移位。

回归测试覆盖精确 ID 解析、禁止按机构名推断国家、禁止用 profile 国家冒充历史国家、嵌套括号及多机构保留、禁止向前推断机构、OSDI 歧义不猜、显式冒号作者—机构关系。

随包验证命令：python verify_outputs.py output。它检查记录总数、唯一出现 ID、字段状态、覆盖率、证据路径/哈希、机构时间标记和去重 ID 一致性；不会假装已读取未移交的原始快照。

所有数字的分母和最终运行状态以随包 coverage.json 为准。补充文件和源快照是可重现材料；本审计没有取得新的在线来源。
