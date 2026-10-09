# Supplement report source snapshot

This directory preserves the supplement HTML builder and the three parsed research-input snapshots used by it. These accompany the frozen conference addon so subsequent work can make report generation reproducible.

Status: source preserved; portability adaptation and a clean rebuild are still pending. This snapshot is not evidence that a fresh-machine rebuild has passed.

Files:
- `build_stage_report.py`: unchanged original builder, with its original cloud workspace ROOT path. Do not run it unmodified in an existing frozen data tree.
- `monthly_library_extract/arxiv_monthly_wide.csv.read.json`: complete parsed monthly research table, 81 rows.
- `monthly_library_extract/openalex_monthly_wide.csv.read.json`: complete parsed monthly research table, 81 rows.
- `monthly_library_extract/report_zh.md.read.json`: supporting research report text.
- `source_manifest.json`: published-file checksums, original-input snapshot checksums, content checksums, and transformation descriptions.

The three JSON files keep their research `content` values exactly. Private Library identifiers and unrelated service-wrapper fields were omitted. The `library_file_id` field is null to retain the original builder's expected schema. These are complete parsed text snapshots, not byte-for-byte originals of the originally uploaded CSV/Markdown files. Both monthly series cover January 2020 through September 2026.

## Portability work required

1. Replace the builder's absolute ROOT path with a CLI argument or project-relative location. Choose new output paths; preserve frozen files.
2. Map the builder's `conferences/` inputs to the merged baseline-plus-addon project. In particular, the addon keeps the specialized NLP/vision tables under `reports/conference_supplement_data/nlp_vision/`; the original builder looks under `conferences/nlp_vision/derived/`.
3. Place or map these three JSON inputs at ROOT/monthly_library_extract. Remove dependencies on private Library identifiers from newly emitted provenance.
4. Audit all source dependencies and confirm that missing optional copied sources are documented rather than silently claimed as present.
5. Rebuild into an empty output directory. Check every plotted number, embedded download, and source link against the frozen supplement; record intentional output/provenance differences. Run desktop and narrow-screen visual checks separately.

The addon archive and original frozen report are unchanged by this source-only supplement. Research limitations, source coverage gaps, and the incomplete visual-QA status remain in force until separately verified and documented.
