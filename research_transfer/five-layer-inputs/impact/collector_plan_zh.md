# 最小可行 enrichment 计划

## 0. 第一版不等待新 API

1. 输入已经生成的 master CSV、原始响应缓存和 manifests；不重新抓取、不重建主表。
2. 以 master.paper_id 为唯一行键，建立 DOI、arXiv base ID、OpenAlex ID、S2 paperId、OpenReview forum ID、official_url/occurrence source ID 到 paper_id 的索引。
3. 离线从已存在的 Work JSON 读 citation 字段。当前缓存没有某字段时填 field_missing（从未请求可填 not_requested），不能等新采集完成。复用原 manifest 的 retrieved_at，不能用当前转换时间或文件 mtime 冒充观测时间。
4. 用现有会议目录的精确 occurrence source ID/已核验 official_url/forum ID 关联 program decision、项目链接、摘要中明确的代码/数据链接。只有题名相似时留入待核对表，不自动 join。先保持原来的 main/附属 track 和规范 work 去重口径。
5. 在原 CSV 右侧追加 metrics_csv_columns.json 的首版 6 列（views/downloads 只有取得真实文章级数值时才增加），未知数值为真正空单元格，JSON 使用 RFC4180 编码；新增独立 impact_metrics.jsonl 便于以后更新。每条现有行都要保留。
6. 输出 coverage.json：实际完整主表分母、尝试的唯一 paper_id 数、exact matched、present、not_requested、missing_identifier、not_found、rate_limited 等，按 provider/venue/year 分层。便利样本不得外推。先交付此版。

## 1. 精确匹配与不可丢失的 provenance

- DOI：去掉明确的 doi: 或 https://doi.org/ 前缀、首尾空白，按 DOI 不区分大小写比较。保留原始值；不要随意去尾标点或截断 DOI。
- arXiv：仅对已验证 arxiv.org/abs|pdf URL 或 arXiv 字段解析官方 ID；保留 vN 版本，在 source matched_identifier 中说明用 base ID 匹配。不能仅凭数字形状从任意 URL 猜 arXiv ID。
- OpenAlex W ID/S2 SHA/CorpusId/forum ID 都保留 namespace。Provider 回应要回验 requested ID 与 externalIds；已有 ID 映射/合并要存 crosswalk 证据。题名和年份只用于异常告警，不能作为自动补足 join 的凭据。
- 多个 canonical paper_id 指向同一 provider record 或某 DOI 对应多个 work 时隔离为 identifier_conflict；不要拆分/合并主表或把同一引文总数重复累计。预印本与正式版本的合并必须来自已核验 crosswalk。
- 每条 observation 保存 provider、record_id、source_url、raw_field、retrieved_at、provider_updated_at、raw_sha256、request_fingerprint、matched_identifier、identifier_match、adapter_version。
- as_of 指本次观察到数值的响应/缓存采集时间，不能声称是源库内部精确统计截止时间。历史缓存缺时间则 null + asof_unknown caveat；不以今天补齐。
- 同论文每个 provider 分开保存。显示列用配置化固定优先级（建议 OpenAlex，其次 S2），不取最大值、不相加。统计/排序时必须明确 provider 与时间窗；缺失排最后。

## 2. 可选的最小在线队列，主 Windows 进程独占调度

此研究包不运行网络 collector。下面是实施协议，不是已完成采集。

OpenAlex：
- 先列出“有精确 ID、字段确缺失且本批需要”的去重请求；优先用户筛选/收藏的候选集，再谈全量。
- select 建议 id,doi,ids,publication_date,publication_year,type,primary_topic,cited_by_count,counts_by_year,fwci,citation_normalized_percentile,cited_by_percentile_year,is_retracted,updated_date。
- 将已经核验的 W ID 放入 filter=openalex:W1|W2|...，每组≤100，per_page=100；DOI 同理按官方 filter 批量。不要按标题搜索后自动合并。筛选新增字段不改变原主体研究范围。
- 若分页才可完整取得结果，从 cursor=* 开始，持久化 meta.next_cursor，按返回游标续查，终止条件与完成状态记录在 manifest；不能把 count 当已经取回行数。
- 本日剩余预算与新增请求只由原 Windows collector 管理；约800请求是父任务的操作约束，不代表 API 固定日限。响应的 X-RateLimit-Remaining、Credits-Used、Reset 与 meta 成本入账，预计成本不足时停队列并输出部分结果。

Semantic Scholar：
- 缺 OpenAlex 值时可选精确 ID batch，POST /graph/v1/paper/batch?fields=paperId,corpusId,externalIds,citationCount,influentialCitationCount,publicationDate,year,url。
- json body 为 ids 列表（最多500），响应10MB限制；初始建议100 ID小批，按真实错误与延迟调整，不并发刷匿名池。本研究单记录成功不保证 batch 在当前环境成功。
- batch 返回 null/缺失逐个记录；返回 record 的 externalIds 与请求ID必须一致。只用 citationCount，不下载全部 citations 再数。若确需引用图，以 /citations 返回的 next/offset 连续分页并标注完整性；bulk search token 不能混用于精确 ID lookup。

OpenReview：
- 已有 forum ID → 公开 /notes?forum=...；按文档分页并持久化 after/id（当前客户端 get_all_notes 迭代），按 note.id 去重。不要以第一页为完整。
- 实际 venue/invitation 定位 review/decision；读取对应 invitation 的字段模板保存 rubric hash 与版本。API v1/v2 从响应/入口确认，不能按年猜。
- 403/401 不自动登录、不换身份绕过；本次失败可以先复用 program decision，review 值留 null + access_denied。字段 readers 限制单独记录。
- review 汇总仅限同 venue-year-track-round-field-rubric_hash；保留原始分值/标签、有效n和未解析n。rubric 未核验时可展示原话，不产生跨组均值/排名。

arXiv：
- 本轮不用 API；标准字段不提供所需 article usage。现有 Atom 中 published/updated/DOI 只作年龄/版本证据。

## 3. 缓存与配额

- 请求键 = provider + endpoint + 规范参数/fields + body IDs（保留对应顺序）+ schema/adapter版本；公开数据不记录任何 token。
- 先查缓存；响应原文写临时文件，计算 SHA-256，原子重命名后更新 manifest。保留第一次取得时间、响应时间、HTTP状态、内容类型、ETag/Last-Modified（如果有）。同内容反复转换不刷新 as_of。
- 启动时从持久化 checkpoint 恢复；成功页与下一游标一起提交。每个 batch 幂等，避免重新消费已完成页。
- 429：读取 Retry-After（秒或HTTP日期），暂停该 provider 队列；若是日预算耗尽，等待 Reset 而不是热循环。临时5xx可有限指数退避加抖动；持续失败保留 queue，下游照常输出partial。401/403停止受限请求，不自动获取凭证。
- 缓存有效期是本项目建议而非来源保证：首版优先任何有证据的缓存；交互显示距观测天数。后续 citation 可按需要7–30天刷新，近期完整性告警可优先，但不默设后台定时采集。
- 新批次完成即回填，不为全量100%覆盖阻塞现有交付。请求数、credits、命中率、失败原因均是真实计数。

## 4. Explorer 最小改动

- 列：引用数（provider/观测时间）、出版年龄、OpenAlex归一化影响、代码/数据链接、官方决定/公开评审、完整性提示。默认保留原分类检索，不默认以引用数淘汰论文。
- views/downloads 若未提供显示“未提供”，不要绘制零柱。视频播放与star独立命名，不能塞进浏览/下载列。
- citation、FWCI、公开rating分开排序；按同领域/年份辅助筛选但不捏造局部归一化。2026部分年度和新论文显示窗口未成熟提示。
- 每个数值可以点到原始来源，显示 status、口径与日期。完整性提示链接原通知；只有 provider flag 的，明确是来源标记。

## 5. 回归验收

必须通过：
1. 输出行数/顺序/paper_id 集与原表完全相同，原列逐值或稳定序列化哈希不变。
2. unknown、429、403、missing_identifier 从不转换为0；显式0仍保留。
3. DOI大小写/合法前缀可以匹配；相似题名、不同 DOI、同 provider ID 对应多 master row 不能静默 join。
4. 两个 provider 的引文不相加，不取最大数；公开评分不同量表不平均。
5. 缓存命中不联网；读取旧缓存不把 as_of 改成今天；中断恢复不重复已提交页面。
6. DOI notice与original方向正确；is_retracted=false不输出“无撤稿”；withdrawal不等于正式撤稿。
7. 年份-only日期不造1月1日，不计算伪精确days；日期在as_of之后标invalid_value。
8. JSONschema及格式校验通过；不包含quality_score、junk_flag等自动判断列。
9. coverage分母来自实际master；首批partial/未采集明确可见。
