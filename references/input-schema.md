# Input configuration

Create one JSON file per product:

```json
{
  "productName": "2026 Chrome Baseball",
  "language": "zh-Hant",
  "formats": {
    "hobby": {
      "label": "HOBBY",
      "oddsColumn": "hobby",
      "packs": 20,
      "cards": 4,
      "guaranteedAutos": 1
    },
    "jumbo": {
      "label": "JUMBO",
      "oddsColumn": "jumbo",
      "packs": 12,
      "cards": 11,
      "guaranteedAutos": 2
    }
  },
  "oddsColumns": ["hobby", "jumbo", "value", "mega", "delight", "fanatics"],
  "autographPattern": "AUTOGRAPH|AUTOGRAPHS|AUTOGRAPHED",
  "baseSection": "BASE CARDS"
}
```

## Rules

- `formats` lists only the formats exposed in the UI.
- `oddsColumn` must match one entry in `oddsColumns`.
- `oddsColumns` must follow the left-to-right order of product columns in the odds PDF.
- `packs` and `cards` are positive integers.
- `guaranteedAutos` defaults to zero. Use a guarantee only when supported by a source.
- `autographPattern` is a case-insensitive regular expression used to classify autograph odds rows.
- `baseSection` must match the base checklist section heading after whitespace normalization.

The parser expects each odds row to contain a card-family label followed by one token per configured odds column. Supported tokens are `1:123`, `1:1,234`, and `-`. Decimal artifacts are reported and skipped rather than silently interpreted.

Checklist extraction expects standalone uppercase section headings followed by rows containing a card number/code, subject name, and optional team or affiliation. If a source uses a materially different layout, adapt the parser narrowly for that source and retain the extraction report.
