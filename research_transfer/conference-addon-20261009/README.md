# Conference research addon transfer

This directory transfers the exact frozen research addon in 26 binary chunks. It is not the final website layout. The original archive is 3,393,511 bytes and has SHA-256 `aba5f03fa83244d3df564358557b51f10b1940ec7b8da3fce14ceb5a390c771b`.

Run from this directory using Python 3.10 or newer (standard library only):

```
python -X utf8 restore_addon.py --output research_trends_conference_addon.zip --extract-to restored_addon
```

On Windows, `py -3 -X utf8` can replace `python -X utf8`. The script verifies every chunk and the complete archive. It refuses to replace a differing ZIP or extract into an existing directory. The extracted `restored_addon/research_trends/` tree contains 82 files, including the supplement HTML, provenance, methodology, source data, manifests, and offline reproduction scripts.

Read `research_trends/CONFERENCE_ADDON_README.md` and `research_trends/CONFERENCE_ADDON_VALIDATION.json` after extraction. The addon preserves limitations and does not include the complete baseline five-conference corpora, which remain required for the full ten-conference comparison.

The publisher should merge the extracted `research_trends/` contents into the existing project carefully and run its supplied integrity and reproduction checks. This transfer commit deliberately makes no changes to `main` or GitHub Pages settings.
