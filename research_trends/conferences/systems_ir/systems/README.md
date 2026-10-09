# OSDI/SOSP official-program metadata, 2020–2026

Snapshot date: 2026-10-09 UTC. Sources are official USENIX technical programs and proceedings tables of contents, and official SIGOPS/SOSP accepted-paper lists. No arXiv API calls, private accounts, or paid databases were used.

## Deliverables and exact scope

- `systems_papers.jsonl`: 715 papers from the main conference programs, including 19 explicitly tagged OSDI 2026 Operational Systems papers.
- `systems_research_papers.jsonl`: 696 papers, excluding those 19 Operational Systems papers.
- `collect_systems.py`: deterministic, standard-library-only parser. Run it with Python 3 to regenerate both JSONL files, the parse audit, the SHA-256 provenance manifest, and optional local marker summaries.
- `parse_audit.json`: title membership/count checks and excluded USENIX invited/keynote talks.
- `sources_manifest.json`: original URLs, snapshot names, collection methods, retrieval date and SHA-256 hashes.
- `summary_counts.{json,csv}`: a deliberately conservative example title-marker classifier, not the shared cross-venue classifier. Reclassify raw titles consistently with the parent corpus.

OSDI research counts by year 2020–2026: 70, 31, 49, 55, 53, 53, 117. All-main-program count in 2026 is 136 (117 research + 19 Operational Systems); earlier years are unchanged.

SOSP research/main-list counts: 2021 54; 2023 43; 2024 43; 2025 66; 2026 62. SOSP had no 2020 or 2022 edition: those cells are not zero-paper conferences and must not be treated as zero demand. SOSP changed to annual editions beginning in 2024. The 2026 conference occurred September 29–October 2, before this snapshot.

## Extraction and validation

### USENIX

Direct HTTP collection was unavailable (403 in the parent collection pass). Instead, official web-tool text snapshots were preserved verbatim as JSON strings named `osdiYYYY_sessions_LINE_web.json`; this is rendered text rather than raw server HTML. All line intervals covering all paper titles were collected. The collector reconstructs line-numbered pages and takes linked H2 paper headings, which preserve titles without PDF line-wrap errors. Each included title must appear, after whitespace/punctuation normalization, in the independently downloaded web-tool text of the official proceedings table of contents. Keynotes and invited talks absent from the proceedings TOC are excluded. The complete official TOC line ranges are present, including OSDI 2026's twelve-page TOC.

The title suffix `(Operational Systems)` in OSDI 2026 is preserved in `title_as_source`, stripped in `title`, and represented explicitly as track `operational_systems` and `main_research=false`.

### SOSP

HTML is retained as `sospYYYY.html`. Parse HTML comments out first. In 2026 the page contains a whole commented-out prior-year accepted list; retaining comments would falsely inflate the paper count. For 2024 onward, parse only active `ul.paperlist` sections, case-insensitively, and allow an optional line break between bold titles and italic author blocks. Assert one extracted record for every list item and bold title. For 2021/2023, parse the official bold-title `by` author paragraphs.

Important traps caught by the audit:
- SOSP 2024: one title/author block omits a line-break tag, so an overly strict pattern returns 42 instead of 43.
- SOSP 2025: five title/author blocks omit a line-break tag. One `li` opener is capitalized as `lI`, so a case-sensitive list counter returns 65 rather than the actual 66 visible titles. The final parser extracts all 66 and validates one row per active list item.
- SOSP 2026: the visible list has 62 titles; the 43-entry HTML-comment list is excluded.

The 2025 official accepted-paper list and main proceedings include “Analyzing and Enhancing ArckFS: An Anecdotal Example of Benefits of Artifact Evaluation.” The KAIST institutional record verifies DOI 10.1145/3731569.3768291 and pages 1149–1157 (9 pages). It remains included in the denominator of 66. No separate short-paper track designation has been established; its specific regular-review process was not verified. Page length alone is not grounds for exclusion. Source: https://pure.kaist.ac.kr/en/publications/analyzing-and-enhancing-arckfs-an-anecdotal-example-of-benefits-o/ .

## Metadata limitations and interpretation

`source_url` and initial `url` identify the exact official program/accepted-list page, with `url_kind` stating that level of specificity. They are not fabricated per-paper links. OSDI records also include the verified proceedings-TOC URL and original source line. DOIs are absent unless subsequently enriched from verified official program links. Author text is retained as published but not entity-resolved. Abstracts are deliberately null: consistent title-only measurement avoids unequal abstract coverage.

All these papers are in the traditional computer-systems field. An AI/LLM topic is an overlapping attribute, not a mutually exclusive competing domain. A title-marker count cannot distinguish systems that use AI as a method from systems built to support AI workloads. Marker-negative is not evidence that a paper has no AI component. The local demonstration lexicon excludes generic GPU, tensor, training, inference and agent words to limit false positives; it therefore materially undercounts broader AI relevance. Use one shared classifier for final cross-venue comparisons.

Raw bibliographic snapshots contain third-party titles and author facts for reproducibility. Do not treat internal web reference IDs embedded in snapshots as public citations; use the original URLs from the manifest.

## OSDI 2026 comparability warning (official evidence)

The program co-chairs' message (https://www.usenix.org/sites/default/files/osdi26-message.pdf; snapshot `osdi2026_chairs_web.json`) independently validates the extracted counts: 669 reviewable submissions; 134 newly accepted papers plus two revise-and-resubmit carryovers from OSDI 2025; 19 Operational Systems papers; hence 117 Research papers. The chairs report that submissions were more than double any earlier year and acceptances around 2.5 times earlier years. They pre-committed to an acceptance rate of at least 20%, and OSDI 2026 was the first multi-track OSDI.

The official CFP (https://www.usenix.org/conference/osdi26/call-for-papers) states that Research is comparable to prior OSDIs, while the new Operational Systems track explicitly welcomes work of a scope/novelty previously suited to USENIX ATC. Process changes include removing the author response period and replacing revise-and-resubmit with conditional acceptance. Thus even research-only year-to-year volume has a major selection/format/venue-ecosystem discontinuity. Keep 2026 visible as a distinct endpoint and report shares as well as counts. Do not attribute the expansion to topical substitution without further evidence. The chairs' exact evidence supports the format/acceptance changes; it does not prove which mechanism caused the increase in submissions.

## Paper-level link enrichment

All 268 SOSP rows have verified paper-level links. Official SIGOPS proceedings TOCs for 2021 and 2023 and official schedules for 2024–2026 supply 267 links; the KAIST institutional research record supplies the verified DOI for the ArckFS contribution. Its author-hosted PDF is also linked and independently verifies the nine-page length. The author PDF has a placeholder DOI, so the actual DOI comes from the institutional metadata rather than the PDF. SOSP 2024 links are official hosted PDFs; other SOSP years predominantly use DOI landing pages. Accepted-list titles remain in `title`; any final-program title variant is retained as `published_title`. Seven clear accepted-to-final title changes are explicitly enumerated in the collector, with no automatic fuzzy matching. OSDI links remain at the official program/TOC level.
