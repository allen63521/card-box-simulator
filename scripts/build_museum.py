"""Build 2026 Topps Museum Collection from its preserved source PDFs."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from parse_museum import COLUMNS, parse_checklist, parse_odds, section_for_odds

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "products/2026-topps-museum-collection-baseball"


def audit(data):
    cfg = data["config"]["formats"]["hobby"]
    rows = data["odds"]
    return {"hobby": {
        "publishedRows": len(rows),
        "expectedNonBasePerPack": sum(1 / row["odds"]["hobby"] for row in rows),
        "expectedNonBasePerBox": sum(1 / row["odds"]["hobby"] for row in rows),
        "naturalExpectedAutosPerBox": sum(1 / row["odds"]["hobby"] for row in rows if row["auto"]),
        "naturalExpectedRelicsPerBox": sum(1 / row["odds"]["hobby"] for row in rows if row["relic"]),
        "naturalExpectedHitsPerBox": sum(1 / row["odds"]["hobby"] for row in rows if row["hit"]),
        "cardsPerBox": cfg["packs"] * cfg["cards"],
    }}


def build():
    pdftotext = os.environ.get("PDFTOTEXT") or shutil.which("pdftotext")
    if not pdftotext:
        raise SystemExit("Set PDFTOTEXT to the Poppler pdftotext executable.")
    source = PRODUCT / "source"
    checklist_pdf = source / "2026_Topps_Museum_Baseball_Checklist.pdf"
    odds_pdf = source / "2026_Topps_Museum_Baseball_Odds.pdf"
    checklist_txt, odds_txt = source / "checklist.txt", source / "odds.txt"
    subprocess.run([pdftotext, "-layout", str(checklist_pdf), str(checklist_txt)], check=True)
    subprocess.run([pdftotext, "-layout", str(odds_pdf), str(odds_txt)], check=True)
    sections, categories, skipped = parse_checklist(checklist_txt.read_text())
    raw_rows = parse_odds(odds_txt.read_text())
    rows, fallback_rows = [], []
    for index, raw in enumerate(raw_rows, 1):
        section = section_for_odds(raw)
        if section not in sections:
            raise ValueError(f"Missing checklist section {section!r} for {raw['name']!r}")
        category = categories.get(section)
        auto = category in {"AUTOGRAPH", "AUTOGRAPH RELIC"} or "Player Autographs" in raw["name"]
        relic = category in {"RELIC", "AUTOGRAPH RELIC"}
        if section == "BASE CARDS" and not raw["name"].startswith("Base"):
            fallback_rows.append(raw["name"])
        rows.append({
            "id": f"museum26-{index:03d}", "name": raw["name"], "section": section,
            "odds": raw["odds"], "auto": auto, "relic": relic,
            "hit": auto or relic, "onCardAuto": auto and not relic,
            "autoRelic": auto and relic, "relicOnly": relic and not auto,
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
        "documentedBaseFallbacks": fallback_rows, "malformedChecklist": skipped,
        "formats": config["formats"], "probabilityAudit": data["audit"], "notes": config["notes"],
        "sourceSha256": {
            checklist_pdf.name: hashlib.sha256(checklist_pdf.read_bytes()).hexdigest(),
            odds_pdf.name: hashlib.sha256(odds_pdf.read_bytes()).hexdigest(),
        },
    }
    assert len(sections["BASE CARDS"]) == 100
    assert len(rows) == 180
    assert not skipped
    (PRODUCT / "product.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    (PRODUCT / "extraction-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(config["productName"], len(rows), len(sections), report["cardEntries"])


if __name__ == "__main__":
    build()
