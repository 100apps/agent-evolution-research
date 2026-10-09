# Official research-paper corpus: SIGIR, KDD, ICSE, OSDI and SOSP

Retrieved 2026-10-09 UTC. Files are an empirical accepted-paper/proceedings metadata panel, not a census of researchers, research employment, field-wide publications, or budgets.

## Files and rebuild

- `combined_papers.jsonl` / `.csv`: normalized metadata, 6,193 main research papers. `papers.jsonl` / `.csv` are the 5,497-paper ICSE/KDD/SIGIR component.
- `papers_labeled.jsonl`: all 6,193 records with title-only dictionary flags and exact matched strings.
- `title_topic_counts.json` / `.csv`: counts, shares, and traditional-topic/AI intersections. `title_lexicon.json` specifies every regex.
- `coverage.json`: abstract/DOI coverage for the three large venues. `combined_coverage.json` covers all five.
- `sources_manifest.json`, `fetch_log.jsonl`, `raw/`: original source URLs, timestamps, raw bytes and SHA-256 hashes. The `.html` extension is a snapshot filename and some contents are JSON, JSONL or JavaScript.
- `systems/`: independently parsed OSDI/SOSP snapshots, manifests, provenance memo and all-main-program vs research-only cohorts. Its 19 OSDI2026 Operational Systems papers are retained separately.
- Rebuild in order: `python parse_conferences.py`, `python systems/collect_systems.py`, `python merge_systems.py`, `python classify_titles.py`. Python 3.10+ and `lxml` are required for the first script. The systems parser is standard-library only. No network is required to rebuild frozen inputs.
- `download_sources.py`: optional standard-library Windows-compatible public-source refresh. It preserves original snapshots and stops at authentication/anti-bot denials rather than bypassing them. It does not call arXiv APIs. OSDI frozen input is web-tool-rendered text, so use the saved source snapshots for exact reproduction.

## Cohort and count boundaries

| Venue | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ICSE research/technical |129|138|197|207|234|245|321|
| KDD research |217|239|253|313|411|552|785|
| SIGIR full/long research |147|151|161|165|160|239|233*|
| OSDI research |70|31|49|55|53|53|117**|
| SOSP main research |no edition|54|no edition|43|43|66|62|

* SIGIR2026 official preliminary accepted page declares 234 full papers but actually contains 233 full-paper entries. Count 233 is captured, 234 is stated, coverage 99.57%. No missing title was invented. The source explicitly says it is the acceptance-notification snapshot and not updated for camera-ready title/author corrections. URL: https://sigir2026.org/en-AU/pages/program/accepted-papers . The site loads it through the public `/api/events` endpoint found in its frontend JavaScript.

** OSDI2026 is a structural break. It is the first multi-track edition; its CFP welcomes former USENIX ATC-scope work, adds Operational Systems, changes reviewing and precommits to at least 20% acceptance. Co-chairs report 669 reviewable submissions, 134 acceptances plus two 2025 revise/resubmit carryovers, totaling 136; 19 are Operational Systems, leaving 117 research. Compare with caution even after removing the new track. Sources: https://www.usenix.org/sites/default/files/osdi26-message.pdf and https://www.usenix.org/conference/osdi26/call-for-papers .

KDD2026 official arrays contain 604 research entries in cycle2 and 183 in cycle1. Two exact duplicate title/DOI entries occur in cycle2. After deduplication, 602+183=785. The excluded 2026 tracks contain ADS186, datasets/benchmarks182, AI-for-science243, blue-sky17 raw entries. Do not fold these new tracks into the research trend.

SIGIR only full/long papers are included. Short papers, perspectives, resources/reproducibility, demos, industry/SIRIP, workshops, doctoral consortium and journal-first/TOIS entries are excluded. KDD only the research track is included; industrial/applied, tutorials, workshops and other tracks are excluded. ICSE uses the accepted research/technical table, not mixed scheduled sessions or journal-first/artifact tracks. OSDI/SOSP exclude keynotes, posters, breaks, workshops and other nonpapers. SOSP2026 commented-out stale HTML content is not counted. Malformed list markup in SOSP2024/25 is handled rather than counting literal `<li>` strings.

These are complete captures of the selected official list sections except the documented SIGIR2026 stated/listed mismatch. They are not uniformly cross-validated against final publisher volumes. Accepted-list vs final proceedings title, withdrawal and publication differences can persist; records retain their source type and link.

## Sources and stable identifiers

All included cohorts come from official conference/proceedings sites. No DBLP fallback was required. Direct DBLP presented an anti-bot challenge and direct USENIX access was denied; neither was bypassed. USENIX official technical-program and proceedings-TOC content was obtained through the supported web tool instead. Source hashes for those records are in `systems/sources_manifest.json` and retained as `source_hashes` in the normalized JSONL.

ICSE's public accepted tables expose event UUIDs and some publisher links. UUIDs are retained as stable source IDs; DOI is populated only where present. KDD2021–23 official proceedings TOCs supply DOI and abstracts. KDD2025–26 official lists supply DOI. KDD2020 individual accepted-paper URLs serve as source IDs. SIGIR2022/24 proceedings enrich exact normalized-title matches; SIGIR2025's official proceedings page supplied only a subset of the accepted-list metadata, so it does not determine the denominator. SIGIR2024 submission IDs are preserved. Otherwise a clearly labeled normalized-title SHA-256 key is used; such a derived ID is not represented as an official DOI.

## Title-only method and interpretation

Every primary comparison uses the title alone, even if abstracts happen to be available. This prevents uneven abstract availability from changing the measurement basis by year. Whole main-research counts represent venue membership in a traditional field; AI adoption is an overlapping label within that field, never a mutually exclusive replacement category.

- `ai_any`: union of explicit language-model, generative-LLM and AI/ML vocabularies. It is a conservative dictionary signal, not an estimate of all AI research.
- `llm_generative_explicit`: explicit large-language-model/LLM, named modern chat/generative models, foundation models, generative AI and retrieval-augmented-generation/RAG vocabulary. BERT/T5 and generic language models remain in the wider language-model vocabulary, not automatically in this stricter count.
- `ai_learning_extended`: sensitivity check adding generic learning/learned/embedding words. It captures more conventional ML but can introduce human-learning false positives.
- `no_ai_marker_n`: denominator minus `ai_any`. This means no dictionary marker detected, not proven non-AI.
- Topic vocabularies cover retrieval/recommendation/ranking; data-mining tasks; software testing/analysis; code generation/repair; and GPU/tensor/AI training, inference and serving infrastructure. Topic and AI labels can overlap.
- Plain `agent`, `model`, `training`, `inference`, `generation` and `intelligent` are not sufficient on their own for the conservative AI union. Agent vocabulary is separately available.

Title-only markers systematically miss papers whose title uses a system name or abbreviated method without AI vocabulary. Conversely prompts, transformers, diffusion and learning can be ambiguous. GPU/tensor infrastructure is reported separately and is not automatically all AI. The sample file is a reproducible review aid, not a completed human-labeled benchmark. Broad-claim validation would require a stratified manual abstract/full-text audit; do not claim dictionary shares are validated AI prevalence.

The panel supports describing growth and reorientation of these conference cohorts. It does not establish migration of people, extinction of a field, or causal crowd-out by AI. Venue scope, acceptance policy, submission cycles, capacity and accepted-vs-published differences can move denominators independently of research activity.
