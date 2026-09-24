# Card Box Simulator Skill

A Codex skill that turns a trading-card product's odds list and checklist into an offline, interactive box-opening simulator.

## What it does

- Parses manufacturer odds and checklist PDFs.
- Models published `1:X` pack odds by box format.
- Preserves packs per box, cards per pack, and documented guaranteed hits.
- Maps parallels, inserts, and autographs to checklist subject pools.
- Generates a self-contained browser app with pack-by-pack and open-all flows.
- Produces an extraction report for malformed or unmapped source data.

## Install

Copy this repository to your Codex skills directory:

```bash
cp -R card-box-simulator "${CODEX_HOME:-$HOME/.codex}/skills/card-box-simulator"
```

Then invoke `$card-box-simulator` and provide an odds PDF and checklist PDF.

## Contents

- `SKILL.md` — workflow and probability invariants.
- `scripts/build_simulator.py` — deterministic PDF-to-simulator builder.
- `references/input-schema.md` — product configuration schema.
- `assets/frontend/` — offline simulator template.

## Requirements

- Python 3.9+
- Poppler's `pdftotext`
- A modern web browser

## Privacy

Input PDFs and generated product data remain local. The skill repository contains no source checklists, source odds files, generated card data, credentials, personal paths, or analytics code.

## Accuracy note

Published odds generally do not describe factory collation correlations. Unless a product supplies additional collation rules, the simulator treats each published odds row as an independent per-pack event and applies documented box guarantees only to the natural shortfall.
