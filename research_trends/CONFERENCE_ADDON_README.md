# 会议研究增量包：离线恢复与续接

快照日期：2026-10-09 UTC。此包补充既有 research_trends 项目，不是八个基础 ZIP 的替代品，也不是分卷 ZIP。无需联网即可阅读报告、恢复新增元数据、检查校验和及重现 60 篇摘要审计。

## 先怎样放置文件

1. 保留原来的八个基础 ZIP，各自独立解压到同一个上级目录，让它们合并成唯一的 research_trends/。
2. 将本 ZIP 也解压到该上级目录。ZIP 内已经包含 research_trends/，不要再解压到 research_trends 内造成双层嵌套。
3. 本包不含根目录 README.md、AGENTS.md 或原 HTML，因此不会主动替换它们。若你的目录已有同名增量文件且你改过它们，先解压到临时目录比较；不要盲目覆盖。
4. 打开 research_trends/reports/conference_supplement.html。页面本体、9 幅 SVG 图与 14 个内嵌下载均可离线使用；点击外部论文/来源链接才需要网络。

## Windows 最短操作

以下命令都在 research_trends 目录内执行。需要 Python 3.10+，推荐 3.12；便携命令只用标准库。-X utf8 用于避免 Windows 默认编码差异。macOS/Linux 可把 py -3 -X utf8 换成 python3 -X utf8。

```powershell
py -3 -X utf8 verify_conference_addon.py
py -3 -X utf8 conferences/systems_ir/restore_metadata.py
py -3 -X utf8 conferences/audit/reproduce_audit_offline.py
py -3 -X utf8 conferences/comparison/test_compare_titles.py
```

恢复脚本把压缩包内的原始字节还原为 conferences/systems_ir/combined_papers.jsonl：6,193 行、7,399,299 字节。它核对 SHA-256；目标已存在且相同则不重复写入，目标不同则拒绝覆盖。

如八个基础包已完整合并，再运行十会统一统计：

```powershell
py -3 -X utf8 verify_conference_addon.py --check-base
py -3 -X utf8 conferences/comparison/reproduce_comparison.py
```

统计重跑在 comparison/reproduced/ 写入新结果，审计重跑在 audit/reproduced/ 写入新结果；不覆盖冻结快照。再次执行时，请用 --output 指定新的空目录。统一统计会重新产生约 55 MB 的标准化标题语料；原始约 41 MB 命中明细默认跳过。需详细命中位置时，直接使用 compare_titles.py，选择新输出目录并不加 --skip-paper-audit。

## 这个包实际增加了什么

- comparison/：一套统一标题规则、十个会议逐年统计、2020–2025 固定九会篮子、会议等权与论文加权结果、会内/权重变化分解、2025→2026 合法同会配对、规则敏感性、来源哈希与复现脚本。
- systems_ir/combined_papers.jsonl.gz：新增 ICSE 1,471、KDD 2,770、SIGIR 1,256、OSDI 428、SOSP 268 篇，共 6,193 篇实际元数据。不是只有标题的占位文件：完整保留原有作者、摘要、DOI、轨道、稳定 ID、来源链接、抓取时间及来源哈希等所有字段。缺失字段仍按原数据缺失，不补造。
- audit/：60 篇逐篇标签、完整已收集摘要、短证据与理由、冻结标签脚本、分层统计、抽样总体说明，以及完整 2,557 篇标题阳性抽样框（其中 2,543 篇有摘要，14 篇缺摘要）。离线版无需基础语料，也无需 NumPy/SciPy。
- reports/：补充 HTML、原报告检查记录、同一批月度解析表及其来源说明、HTML 中使用的旧 ACL/CVPR 专用词表和派生表副本。
- CONFERENCE_ADDON_MANIFEST.json：包内文件 SHA-256 和字节数；不把清单自身纳入自身哈希。ZIP 旁另提供整个 ZIP 的 SHA-256。CONFERENCE_ADDON_SOURCE_MAP.json 记录拷贝来源及为便携性做的两项文本调整。

## 与基础项目、原 HTML 的关系

基础项目的会议报告覆盖 ICLR、ICML、NeurIPS、ACL、CVPR 五会；补充页扩展到十会。补充页共含 89,530 条会议年份记录，其中 NeurIPS 2026 的 5,522 条会前暂定记录从所有趋势差分中排除；84,008 是剔除它们后的记录数。2020–2025 年度总曲线只用每年都有数据的固定九会篮子，SOSP 单列，不得把无届年份补零。

本包的月度宏观表与基础报告来自同一批既有数据：2020-01 至 2026-09，81 个月。它不是又采集了一套独立月度证据，也不是细分 agent/后训练月度序列。文件是 Library 表格文本的完整解析导出，保留生成的索引列；其哈希针对解析文本，不是原上传 CSV 的字节哈希。

以下三套口径必须分开命名和展示：

1. comparison/common_topic_rules.json：十会共同标题词汇规则。
2. 原 ML、ACL/CVPR、systems_ir 采集组词表：各组自己的历史规则。相同显示名称也不保证分子相同。
3. audit/sampling_manifest.json 内的 agent/tool/memory 正则：沿用原 ML 宽口径，包含部分 RAG、memory 等；不是 comparison 的 agents_broad 或 agents_language_action_strict。

补充 HTML 的 ACL/CVPR 专题图明确使用其原专用规则，不能与统一规则同名主题拼接。60 篇审计的标签是冻结的单一 AI 阅读者判断，既非人工金标准、也非重新运行模型判读。加权 39.5% 只代表所限定的标题阳性且有摘要总体中的估计，不能说全会 39.5% 都是 agent，也不能估计召回率。

## 完整统一统计的输入条件

需要以下文件与 source_corpus_manifest.json 中记录的 SHA-256 完全一致：

- conferences/ml/metadata_main.jsonl：57,957 条，由基础包提供
- conferences/nlp_vision/papers_main.jsonl：25,380 条，由基础包提供
- conferences/systems_ir/combined_papers.jsonl：6,193 条，由本包恢复

只把新增 6,193 条交给 compare_titles.py 不足以重跑九会篮子。--input 也不是任意子集分析接口：它仍要求既定会议、年份和固定篮子完整性。缺文件先检查基础包合并位置；哈希不一致则说明快照不同，应建立新的版本，不要强行声称重现冻结数字。

比较的源清单含原脚本哈希和源数据哈希。本包仅将清单里的机器绝对路径改成项目相对路径。重跑时新清单的生成时间与路径自然变化，不纳入统计字节一致性比较；17 个可重现结果文件（含重建标准化语料）由重跑脚本逐一核对。

## 依赖、原始快照和已知限制

- 本包不包含体积大的原始网页抓取快照，也不包含基础五会的完整语料。保留了官方来源 URL、快照名与 SHA-256；能精确恢复既有 6,193 条元数据，不等于能仅凭本包从原网页重新解析整个元数据集。
- 696 条 OSDI/SOSP 元数据使用 source_hashes 多快照映射，而非单一 source_sha256。本包保留原始映射及 systems/sources_manifest.json。标准化标题输出会丢掉多哈希映射，所以不能代替原元数据作全部来源追溯。
- 原采集/解析脚本作为来源方法一并保留；有些还需要遗漏的原始快照、lxml 或网络。未获必要输入前不要运行。默认便携命令不调用它们。
- 原 audit/sample_agent_abstracts.py 从基础 ML/ACL 全语料重抽样；原 label_agent_abstracts.py 需要 NumPy/SciPy；原 validate_audit.py 会改写文件、调用字面 python，并比较包含 Python 版本的清单。跨机器应优先使用新增 reproduce_audit_offline.py，它对同一冻结结果做标准库复现。原脚本保留供方法追溯，不建议在冻结目录直接运行原验证器。
- NeurIPS 2026 暂定且不完整；OSDI 2026 有轨道/范围结构断点，单列。SIGIR 2026 为 233 条实际列出、234 条页面声称；CVPR 2026 为 4,042 条索引、4,089 条录用公告，差额未核实。
- 标签是非互斥标题词汇指标，不能直接推断研究者迁移、领域死亡、工时/经费分配或因果挤出。没有命中不等于没有相关研究。
- HTML 数值、结构、内嵌下载已检查；此前浏览器因 socket 创建限制未能完成截图目视 QA。本包未宣称已通过桌面/手机视觉检查。
- HTML 已交付为可独立阅读的冻结文件。非便携的原报告构建器未包含；需要编辑/重建时使用随包数据并另存新版本。

继续工作请读 AGENT_HANDOFF_CONFERENCE_ADDON.md。包内没有账户凭据，也不需要发布到网站。
