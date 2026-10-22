"""Build 2026 Topps Cosmic Chrome Baseball from its preserved source PDFs."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from parse_cosmic import COLUMNS, parse_checklist, parse_odds, section_for_odds

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "products/2026-topps-cosmic-chrome-baseball"


def audit(data):
    result = {}
    for key, cfg in data["config"]["formats"].items():
        column = cfg["oddsColumn"]
        rows = [row for row in data["odds"] if row["odds"].get(column)]
        result[key] = {
            "publishedRows": len(rows),
            "expectedNonBasePerPack": sum(1 / row["odds"][column] for row in rows),
            "expectedNonBasePerBox": cfg["packs"] * sum(1 / row["odds"][column] for row in rows),
            "naturalExpectedAutosPerBox": cfg["packs"] * sum(1 / row["odds"][column] for row in rows if row["auto"]),
        }
    return result


def build():
    pdftotext = os.environ.get("PDFTOTEXT") or shutil.which("pdftotext")
    if not pdftotext:
        raise SystemExit("Set PDFTOTEXT to the Poppler pdftotext executable.")
    source = PRODUCT / "source"
    checklist_pdf = source / "2026_Cosmic_Chrome_Baseball_-_Checklist.pdf"
    odds_pdf = source / "2026-09-28_2026-Topps-Cosmic-Chrome-Baseball_Odds.pdf"
    checklist_txt, odds_txt = source / "checklist.txt", source / "odds.txt"
    subprocess.run([pdftotext, "-layout", str(checklist_pdf), str(checklist_txt)], check=True)
    subprocess.run([pdftotext, "-layout", str(odds_pdf), str(odds_txt)], check=True)
    sections, categories, skipped = parse_checklist(checklist_txt.read_text())
    raw_rows, malformed = parse_odds(odds_txt.read_text())
    rows = []
    for index, raw in enumerate(raw_rows, 1):
        section = section_for_odds(raw["name"])
        if section not in sections:
            raise ValueError(f"Missing checklist section {section!r} for {raw['name']!r}")
        category = categories.get(section)
        auto = category == "AUTOGRAPH" or section == "COSMIC EXPLORERS CUT SIGNATURES"
        rows.append({
            "id": f"cosmic26-{index:03d}", "name": raw["name"], "section": section,
            "odds": raw["odds"], "auto": auto, "relic": False, "hit": auto,
        })
    config = json.loads((PRODUCT / "config.json").read_text())
    data = {
        "id": PRODUCT.name, "config": config, "sections": sections, "odds": rows,
        "autographSections": sorted({row["section"] for row in rows if row["auto"]}),
    }
    data["audit"] = audit(data)
    report = {
        "product": config["productName"], "oddsRows": len(rows), "oddsColumns": len(COLUMNS),
        "checklistSections": len(sections), "cardEntries": sum(map(len, sections.values())),
        "baseCards": len(sections[config["baseSection"]]), "unmappedOddsFamilies": [],
        "malformedOdds": malformed, "malformedChecklist": skipped,
        "formats": config["formats"], "probabilityAudit": data["audit"], "notes": config["notes"],
        "sourceSha256": {
            checklist_pdf.name: hashlib.sha256(checklist_pdf.read_bytes()).hexdigest(),
            odds_pdf.name: hashlib.sha256(odds_pdf.read_bytes()).hexdigest(),
        },
    }
    assert len(sections["BASE CARDS"]) == 200
    assert len(rows) == 138
    assert not malformed
    assert not skipped
    (PRODUCT / "product.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    (PRODUCT / "extraction-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(config["productName"], len(rows), len(sections), report["cardEntries"])


if __name__ == "__main__":
    build()
