"""Build 2026 Topps Allen & Ginter from its preserved source PDFs."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from parse_allen_ginter import COLUMNS, parse_checklist, parse_odds, section_for_odds

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "products/2026-topps-allen-ginter-baseball"


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
            "naturalExpectedRelicsPerBox": cfg["packs"] * sum(1 / row["odds"][column] for row in rows if row["relic"]),
            "naturalExpectedHitsPerBox": cfg["packs"] * sum(1 / row["odds"][column] for row in rows if row["hit"]),
        }
    return result


def build():
    pdftotext = os.environ.get("PDFTOTEXT") or shutil.which("pdftotext")
    if not pdftotext:
        raise SystemExit("Set PDFTOTEXT to the Poppler pdftotext executable.")
    source = PRODUCT / "source"
    checklist_pdf = source / "2026_Allen_and_Ginter.pdf"
    odds_pdf = source / "2026-09-29_MLB-ALLEN-_-GINTER-2026_Odds.pdf"
    checklist_txt, odds_txt = source / "checklist.txt", source / "odds.txt"
    subprocess.run([pdftotext, "-layout", str(checklist_pdf), str(checklist_txt)], check=True)
    subprocess.run([pdftotext, "-layout", str(odds_pdf), str(odds_txt)], check=True)
    sections, categories, skipped = parse_checklist(checklist_txt.read_text())
    sections["ALLEN AND GINTER FRAMED RELICS MINI SIZE"] = (
        sections["ALLEN AND GINTER FRAMED RELICS MINI SIZE I"]
        + sections["ALLEN AND GINTER FRAMED RELICS MINI SIZE II"]
    )
    categories["ALLEN AND GINTER FRAMED RELICS MINI SIZE"] = "RELIC"
    raw_rows = parse_odds(odds_txt.read_text())
    rows = []
    for index, raw in enumerate(raw_rows, 1):
        section = section_for_odds(raw["name"])
        if section not in sections:
            raise ValueError(f"Missing checklist section {section!r} for {raw['name']!r}")
        category = categories.get(section)
        auto = category in {"AUTOGRAPH", "AUTOGRAPH RELIC"}
        relic = category in {"RELIC", "AUTOGRAPH RELIC"}
        rip = "RIP CARD" in raw["name"]
        printing_plate = "PRINTING PLATE" in raw["name"]
        rows.append({
            "id": f"ag26-{index:03d}", "name": raw["name"], "section": section,
            "odds": raw["odds"], "auto": auto, "relic": relic,
            "hit": auto or relic or rip or printing_plate,
        })
    config = json.loads((PRODUCT / "config.json").read_text())
    data = {
        "id": PRODUCT.name, "config": config, "sections": sections, "odds": rows,
        "autographSections": [name for name, category in categories.items() if category in {"AUTOGRAPH", "AUTOGRAPH RELIC"}],
    }
    data["audit"] = audit(data)
    report = {
        "product": config["productName"], "oddsRows": len(rows), "oddsColumns": len(COLUMNS),
        "checklistSections": len(sections), "cardEntries": sum(map(len, sections.values())),
        "baseCards": len(sections[config["baseSection"]]), "unmappedOddsFamilies": [],
        "malformedChecklist": skipped, "formats": config["formats"],
        "probabilityAudit": data["audit"], "notes": config["notes"],
        "sourceSha256": {
            checklist_pdf.name: hashlib.sha256(checklist_pdf.read_bytes()).hexdigest(),
            odds_pdf.name: hashlib.sha256(odds_pdf.read_bytes()).hexdigest(),
        },
    }
    assert len(sections["BASE CARDS"]) == 300
    assert len(rows) == 97
    assert not skipped
    (PRODUCT / "product.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    (PRODUCT / "extraction-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(config["productName"], len(rows), len(sections), report["cardEntries"])


if __name__ == "__main__":
    build()
