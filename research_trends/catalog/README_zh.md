# 十会议论文主 CSV 与 Explorer

本目录以 **89,530 条会议来源出现记录**为输入，输出 69 列论文目录。前 61 列遵循冻结的 `paper-master-v1.1.0-proposed`，后八列为引文与使用量扩展。当前每条来源出现记录对应一个暂定 work ID；跨来源重复尚未完全判清，`dedup_status=unresolved`，不得称 89,530 篇已彻底去重的论文。`paper_occurrences.csv` 保留 venue/year/track；`source_coverage_manifest.csv` 的 70 个会议年份格明确区分未采集、未知及 NeurIPS 2026 会前暂定。

## 下载与浏览

- [交互 Explorer](https://100apps.github.io/agent-evolution-research/research-trends/explorer/)：按五层、二三级、会议、年份、国家与候选状态筛选，查看原始证据和分页记录；可导出经过 Excel 公式转义的筛选 CSV。
- 完整 **原始 CSV** 在 GitHub Release `trends-catalog-2026-10-09`；仓库保存逐字节相同内容的 `data/master_papers.csv.gz` 与 `data/master_receipt.json`。原始 CSV 不能直接用 Excel 全量打开；适合数据库或流式脚本。
- `papers_index.jsonl.gz` 是轻量浏览视图，完整字段和作者—机构关系在主 CSV；`index_manifest.json` 有行数、列位置和 SHA-256。

## 实际覆盖与解释

| 字段 | 有值的来源记录 / 89,530 | 解释 |
|---|---:|---|
| 有序作者名 | 89,071 | 是署名槽位，不是全球唯一研究者；OSDI 428 条等保留未拆分原文。 |
| 来源报告机构 | 38,213 | 含 29,947 条时间未核实的会议用户资料机构。 |
| 论文期机构 | 8,266 | 仅按论文级 affiliation；部分作者有机构不表示全部作者齐全。 |
| 明确论文机构国家/地区 | 172 | 0.192%；不能用于全球国家排名或作者国籍推断。 |
| 五层三级标题规则候选 | 7,656 | 8.55%；未经独立专家语义审查。其余 81,874 为“证据不足”，不是“非 AI”。 |
| OpenAlex 精确 DOI 引用值 | 10,451 | 20 条精确 DOI 歧义、19 条可能分页截断、14 条查无结果；其余 79,026 条无可用已核验 DOI。 |
| 文章级查看/下载量 | 0 | 当前来源没有可比的逐篇计数，列空值；绝不把缺失当 0。 |

引用值来自 [OpenAlex 官方 DOI 批量查询](https://help.openalex.org/how-to/api-recipes/) 的 106 次匿名免费请求，每批至多 100 个 DOI。全部请求、时间、响应头额度、原始 JSON 和 SHA-256 存于 `citation_cache/`。最后一次响应余 176 免费额度。每行引用数保留 provider、观察时间、精确 DOI 依据与可解析到审计文件的请求哈希。**高引用不是论文质量证明**；数据库覆盖、领域与发表年份不同，近期论文有引文滞后。没有公开可核验评审分数时不填分数，也不自动判断“水文”。

五个一级层名与顺序来自 [NVIDIA 的五层表述](https://blogs.nvidia.com/blog/ai-5-layer-cake/)；17 个二级、59 个三级节点与标题规则由本项目提出，不是 NVIDIA 的官方分类。`taxonomy.json`、`title_rules.json`、`data/title_assignments.csv`、规则/字段说明与修订记录可逐条复核。多标签可以重叠；同层各分类计数不可相加。能源、芯片等层在十会议样本中稀疏，不能把空格当行业零活动。

## 离线验证和重建

从仓库根目录使用仓库虚拟环境解释器（Windows：`.\.venv\Scripts\python.exe`；Linux/macOS：`./.venv/bin/python`）。原 39 篇报告和月度趋势的入口仍是 `tools/research.py trends-validate` 与 `trends-rebuild`。

```powershell
$py = '.\.venv\Scripts\python.exe'
& $py research_trends\catalog\validate_master_csv.py --master run_outputs\catalog\master_papers.csv --coverage-manifest research_trends\catalog\data\source_coverage_manifest.csv --citation-audit research_trends\catalog\citation_cache\query_audit.jsonl
& $py research_trends\catalog\metadata\verify_outputs.py research_trends\catalog\metadata_snapshot
& $py -m unittest discover -s research_trends\catalog -p 'test_schema_validation.py' -v
```

先用标准库 `gzip` 将 `data/master_papers.csv.gz` 解到新的 `run_outputs/catalog/master_papers.csv`，再运行上面的逐行验收。重建流程见 `rebuild.py`：从保存的三份题录及原始快照重新提取作者与元数据、按同一冻结标题规则分类、从已存 OpenAlex 响应精确 DOI 连接、压缩影响字段并重建 Explorer 索引。它不会联网或修改归档输入；完整输出 SHA 必须与 `data/master_receipt.json`、`index_manifest.json` 匹配。若缓存/快照不同则保留差异，不覆写已发布哈希。

## 边界

作者、机构与国家缺失率、会议选择、年度会场覆盖、暂定 NeurIPS 2026、标题候选误报/漏报、OpenAlex 回填与数据库映射误差均会影响解读。原 39 篇 Agent 进化论文是独立研究背景，未并入这份十会议目录；月度 arXiv/OpenAlex 汇总也没有伪造为逐篇记录。浏览器仅呈现来源代理变量，不推断全球研究者人数或 Agent 项目价值。
