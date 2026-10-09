# Windows 接入路径与最小输入

命令中的 --conferences-root 指向同时含 ml、nlp_vision、systems_ir 三个目录的父目录。脚本没有固定 cwd，也没有 Linux 绝对路径依赖。

必须有：
- ml/metadata_main.jsonl
- nlp_vision/papers_main.jsonl
- systems_ir/combined_papers.jsonl

可恢复字段所需的已有原始快照：
- ml/raw/iclr_2020_papers.json：ICLR 2020 原始作者、OpenReview ID
- ml/raw/*_orals-posters.json：实际文件为 iclr_2021_iclr-2021-orals-posters.json 等双年份命名；脚本匹配 *orals-posters.json。恢复作者 profile 机构、精确 ID、程序日期
- ml/raw/icml_*_index.html：PMLR 论文 URL→OpenReview 明确链接
- ml/raw/icml_*_citeproc.yaml：PMLR published 出版日期
- ml/raw/neurips_*_index.html：NeurIPS proceedings 作者顺序
- nlp_vision/raw/acl_2020.xml 至 acl_2026.xml：作者、逐作者机构、日期
- nlp_vision/raw/cvpr_2020_day16.html、cvpr_2020_day17.html、cvpr_2020_day18.html；cvpr_2021.html 至 cvpr_2026.html：作者、arXiv 链接、书目信息月份
- systems_ir/raw/icse2020.html 至 icse2026.html：7 份，用精确 event UUID 恢复 prog-aff 机构。机构时间有效性标记未验证，不推导国家
- systems_ir/raw/sigir2024_data.html：1 份，用精确 submission ID 恢复逐作者 affiliation

已有五会原始快照足以支持 ML+ACL+CVPR 主要恢复。只有额外 6,193 条规范化元数据、没有 systems_ir/raw 的电脑仍可运行：KDD/SIGIR/SOSP 中已保存的明确作者/机构原文继续可解析；ICSE 和 SIGIR2024 额外机构恢复会少于本次云端覆盖率。缺少 raw 文件不允许报成同样的本地覆盖率，应以重跑输出的 coverage.json 为准。

OSDI 的 428 条作者/机构混合原文已在 combined_papers.jsonl 中，不需要另一个 raw 源即可保留。但本脚本不猜逗号边界，结构化作者/机构仍为空，UI 可显示 authors_raw。

运行（假设三个目录就在 research_trends/conferences/）：

    py -3 -X utf8 enrich_local_metadata.py --conferences-root research_trends/conferences --output-dir metadata_enrichment --patch-only
    py -3 -X utf8 verify_outputs.py metadata_enrichment

--patch-only 会输出 metadata_patch.jsonl.gz、coverage.json、source_manifest.json、examples.json。主 CSV 构建器可从 gzip JSONL 读取字段补丁，按 venue + year + track + source_paper_id 连接。不要按题名连接。补丁中的 institutions / countries / authors 为数组，写 CSV 时 JSON 序列化；完整作者—机构多对多信息在侧车 authors[*].affiliations；CSV 的 authors 只存名字数组，metadata_sidecar_ref 存 occurrence_id。field_provenance[*].evidence[*].source_ref 可解析到 source_manifest.json 的 source_id，得到字段证据路径与完整 SHA-256。

如需另外生成完整 JSONL 和便于检查的 CSV，省略 --patch-only，并加 --gzip。

原39补充可选，不要阻塞会议主CSV：

    py -3 -X utf8 enrich_local_metadata.py --conferences-root research_trends/conferences --original39-root PATH_TO_BILIBILI_PAPERS --original39-supplement original39_manual_supplement.json --output-dir metadata_enrichment --patch-only

原39补充需要 agent_evolution_map.json 和补充记录引用的本地原文/桥接来源。每条均校验哈希，不存在的源不会冒充已经复核。已核对的 original39_manual_supplement.json 只有约 388 KB，可单独移交；35/39 条可自动整合，缺失保留。
