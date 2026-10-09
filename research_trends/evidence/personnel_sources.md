# 人员与招聘：来源分离记录

截至 2026-10-09。以下各项来自公开机构报告的不同总体与时间粒度，不能拼接成全球月度研究人员人数。原报告链接和页码保留；本目录 CSV 是表内数字的转录及明确计算，须与原 XLSX 再核验。

| 来源 | 真正测量的量 | 已核验数字 | 截止与限制 |
|---|---|---|---|
| [NSF NCSES SED 2025 Table 3-1](https://www.ncses.nsf.gov/pubs/nsf26326/assets/data-tables/tables/nsf26326-tab003-001.pdf)；[XLSX](https://www.ncses.nsf.gov/pubs/nsf26326/assets/data-tables/tables/nsf26326-tab003-001.xlsx) | 美国机构新获研究博士，年度人流入 | AI 标签 2021 年 167、2025 年 368；计算机与信息科学总体 2,194→3,002，差额非 AI 标签 2,027→2,634 | 2025 学年；非在职存量，也不追踪个人转行。2021 详细学科分类有断点；ML 是另列，2021 缺失。见 `nsf_doctorates_annual.csv`。 |
| [LinkedIn SWE Talent Landscape 2026](https://delivery-p143253-e1476319.adobeaemcloud.com/adobe/assets/urn:aaid:aem:0e5ab70a-edfd-4bdb-b68f-787fd3ba1a51/original/as/us-software-engineer-talent-landscape-2026.pdf)，第 3–5 页 | 美国 LinkedIn SWE 跨公司岗位转移 | 2021–25 SWE→生成式 AI 工程师转移近 9 倍，2025 年仍小于 SWE 工作转换的 1%；SWE→SWE 71.4%→69.0% | 年度端点、平台样本；未公开月度原始转移表，内部转岗不计。 |
| [LinkedIn Global Data Center Workforce 2026](https://delivery-p143253-e1476319.adobeaemcloud.com/adobe/assets/urn:aaid:aem:9aa78135-a7c3-4e4f-8dc7-f455b8fb9f0f/original/as/powering-ai-a-deep-dive-into-the-global-data-center-workforce.pdf)，第 2–3、9–11、14–16 页 | LinkedIn 数据中心岗位及外部流入 | 当前岗位 2017–25 增 107%；外部流入/流出比约 1→2.2；2016–25 外部入职者先前为网络工程师 9.0%、系统工程师 8.7%、SWE 5.8% | 不是 GPU 专属，也不能归因于 AI；55% 的所有入职为数据中心内部移动。 |
| [LinkedIn AI Labor Market Update 2026-08](https://delivery-p143253-e1476319.adobeaemcloud.com/adobe/assets/urn:aaid:aem:ef153078-1061-4817-82e7-a1c027d7a7d7/original/as/AI-Labor-Market-Update-August-2026-v2.pdf)，第 1–3 页 | 平台季度招聘变化 | 2026 Q2 美国 AI Engineer 招聘同比 +64%，印度 +68%；德国初级 SWE -32%，印度初级前端 -39% | 不给岗位总存量，也不识别同一人的起源岗位；宏观招聘环境可解释反向变化。 |
| [OECD Employment Outlook 2026 图 1.23A](https://www.oecd.org/en/publications/oecd-employment-outlook-2026_7e710f54-en/full-report/component-5.html)；[原 XLSX](https://stat.link/files/7e710f54-en/ls1u0b.xlsx) | AI 招聘同比增长减总体招聘同比增长，12 月移动平均的季度公布点 | 美国 2023 Q3 -3.478 个百分点，2025 Q1 +25.809 个百分点 | 原 AI 招聘单元格仅至 2025 Q1；不可插成月度。不同于 LinkedIn 新版比率口径。 |
| [UNESCO UIS 2026 R&D release](https://www.uis.unesco.org/en/2026-rd-data-release) | 全球研发人员 FTE/百万人口，年度密度 | 2020 约 1,340，2023 约 1,486 | 最新全球点 2023；非 AI 人员分子，且 FTE 不等于 headcount。 |

这些数据支持 AI 相关技能与部分岗位增长、从邻近 IT 进入数据中心，但不能证明搜索、推荐、营销、算法或一般工程的全球在职人数下降。NSF 的计算机非 AI 标签博士绝对人数上升，同时占比下降，正好展示“份额稀释 ≠ 绝对减少”。
