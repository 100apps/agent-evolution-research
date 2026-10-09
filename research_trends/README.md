# AI 与相邻研究方向的活动趋势

本目录保留[采集前本地计划的历史快照](PREREGISTRATION.md)、[协议](protocol.md) 和采集后修订的可重跑研究输入。该计划随结果一并公开，没有独立公开时间戳，不能称外部预注册。研究测量**来源所覆盖的作品与其他代理变量**，不提供世界研究人员人数普查；仓库原有 39 篇 Agent 进化论文也没有被当作行业样本。

## 先看结果

- [十会议论文主 CSV 与 Explorer](catalog/README_zh.md)：89,530 条来源记录、五层三级候选分类、精确 DOI 引用快照和完整字段证据。此目录与月度宏观统计分母不同。
- [中文分析报告](report_zh.md)：结论、反证、不能回答的问题和项目含义。
- [交互面板](reports/dashboard.html)：分开查看 OpenAlex、arXiv 月线，以及五会场共享标题规则热图；离线打开即可。
- `data/processed/openalex_monthly_wide.csv`、`openalex_annual.csv`、`openalex_fields_monthly.csv`：月度与完整日历年度输出。
- `data/processed/arxiv_monthly_wide.csv`、`arxiv_annual.csv`：arXiv 首次提交月份，独立于 OpenAlex；不能相加。
- `data/query_audit.jsonl`、`arxiv_query_audit.jsonl`：每次联网尝试、URL、UTC 时间、响应 SHA-256、失败及缓存命中；原始响应在 `data/raw/`。
- [来源权利说明](DATA_RIGHTS.md)：OpenAlex、arXiv 与会场资料分别适用的来源声明；本仓库不对第三方内容统一再许可。

## 离线验证与重建

从仓库根目录运行，始终使用**当前检出**的虚拟环境解释器。这两个入口仅读取已保存的公开来源快照，不发网络请求；重建写入新目录，不覆盖归档：

```powershell
.\.venv\Scripts\python.exe tools\research.py trends-validate
.\.venv\Scripts\python.exe tools\research.py trends-rebuild --output-dir run_outputs\trends-rebuild
```

Linux/macOS 将解释器替换为 `./.venv/bin/python`。验证逐一比对 OpenAlex/arXiv 查询 URL、查询哈希、原始响应 SHA-256、顶会来源 manifest 与源文件哈希、月格、缺失状态、会场记录、标题规则 SHA。重建从快照恢复五会场标准化题录和分析表，再生成离线交互 HTML；十个关键输出与归档逐字节 SHA-256 对照，结果、完整命令和日志写入指定目录。中文解释报告由研究者撰写，表格和图可重建，不能把文字解释误称自动生成。当前已保存的核验结果见 [报告](report_zh.md)。

可选的本地 Edge 桌面/手机宽度验收使用仓库的 `requirements-qa.txt`：安装到**当前**虚拟环境后，运行 `research_trends/visual_qa.py --report .pages-build/dist/research-trends/index.html --output-dir run_outputs/trends-visual`；截图与断言只写入忽略的输出目录。缺少 Playwright 时不把静态 HTML 构建通过冒充浏览器视觉验收。

## 重新采集公开来源（需要联网）

以下命令仅供来源快照更新，**不是**离线重建入口。运行前先阅读 [协议](protocol.md)、[修订记录](protocol_amendments.md) 和各源限制。从仓库根目录运行：

```powershell
$py = '.\.venv\Scripts\python.exe'
& $py research_trends\collect_openalex.py --output-dir research_trends\data --scope full --max-calls 800
& $py research_trends\collect_openalex.py --output-dir research_trends\data --scope first-day --max-calls 800
& $py research_trends\collect_openalex.py --output-dir research_trends\data --scope marketing --max-calls 800
& $py research_trends\analyze_openalex.py
& $py research_trends\collect_arxiv.py --output-dir research_trends\data --scope full --max-calls 600
& $py research_trends\analyze_arxiv.py
& $py research_trends\collect_openalex_topics.py
& $py research_trends\collect_openalex_type_sensitivity.py
& $py research_trends\sample_openalex.py
& $py research_trends\audit_openalex_sample.py
& $py research_trends\conferences\nlp_vision\collect.py
& $py research_trends\conferences\nlp_vision\normalize.py
& $py research_trends\conferences\ml\collect.py
& $py research_trends\conferences\ml\normalize.py
& $py research_trends\conferences\analyze_shared_titles.py
& $py research_trends\build_dashboard.py
```

原始缓存使同一 URL 不再联网；新的查询和失败重试受本地物理请求上限约束。arXiv 串行，所有进程从同一审计文件恢复至少 3.5 秒请求间隔；**不要同时运行两个 arXiv 采集进程**。六细分 pilot 已遇 HTTP 429，停止了 internal-full；现有缺失保留，不能把上面的宏观重跑命令误读成批准继续长词串批量请求。OpenAlex 匿名 API 也可能设置自己的每日限额，不要删除审计文件绕过本地预算。顶会脚本从已列明的官方公开目录读取题录，运行前应静态核查来源清单。

## 字段与口径

| 字段/前缀 | 单位与定义 |
|---|---|
| `global_eligible_works` | OpenAlex 当前默认 core 语料中，`article|preprint|conference-paper|review` 且非已知撤稿的 work ID 数；按当前 `publication_date` 归月。 |
| `cs_primary_field_works` | 上述作品中 OpenAlex 当前**主**领域为计算机科学 field 17 的数量。 |
| `ai_primary_1702_works` | 主子领域为 AI 1702；不能覆盖所有应用 AI 的作品。 |
| `ai_vision_primary_1702_1707_works` | AI 1702 或计算机视觉 1707 的敏感性扩展；两者用 OR 去重。 |
| `marketing_primary_1406_works` | 主子领域 Marketing 1406；与 AI 方法轴可以重叠。 |
| `marketing_ai_vision_cotag_works` | Marketing 主分类且当前前三主题至少一个具有 1702/1707 子领域；仅为数据库共标签。 |
| `first_day_*` | 每月 1 日同口径计数，用来诊断发表日堆积。`excl_first_day` 仅为敏感性，不是修复值。 |
| `all_arxiv_submissions` | arXiv API 以首次提交日 `submittedDate` UTC 查询的记录数。 |
| `cs_plus_stat_ml_submissions` | arXiv `cs.* OR stat.ML` 范围。 |
| `core_ai_5_submissions` | arXiv `cs.AI|cs.LG|cs.CL|cs.CV|stat.ML` 类别并集。类别是来源代理，不是全文语义标签。 |
| `*_candidate_hits` | 预先冻结的标题/摘要词串查询命中，词串之间可以交叠。没有人工校正前不可称为 Agent 等细分论文真实总量。 |
| `status=missing` | 查询失败、未执行或口径无法验证；留空，绝不作零。 |

`2026-09` 是最近完整**日历**月，但数据库回填未必结束；`2026` 非完整年度。年度输出只有 12 个月都齐全才给总计。完整条件、两轴分类与偏差见 [协议](protocol.md)，实际采集失败在审计中保留。
