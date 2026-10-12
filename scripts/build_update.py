"""Build 2026 Topps Update Series from its preserved source PDFs."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from parse_update import COLUMNS, parse_checklist, parse_odds_pdf, section_for_odds

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "products/2026-topps-update-series-baseball"


def combine(sections, target, names):
    sections[target] = [card for name in names for card in sections[name]]


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
    checklist_pdf = source / "2026_Topps_Update_Series_Baseball_Checklist_9-4.pdf"
    odds_pdf = source / "2026_Topps_Baseball_Updates_Series_Odds.pdf"
    checklist_txt, odds_txt = source / "checklist.txt", source / "odds.txt"
    subprocess.run([pdftotext, "-layout", str(checklist_pdf), str(checklist_txt)], check=True)
    subprocess.run([pdftotext, "-layout", str(odds_pdf), str(odds_txt)], check=True)
    sections, categories, skipped = parse_checklist(checklist_txt.read_text())
    base_groups = ["VETERAN I", "VETERANS II", "ROOKIES", "ROOKIE DEBUT", "VETERAN COMBOS", "SEASON HIGHLIGHTS"]
    combine(sections, "BASE SET", base_groups)
    combine(sections, "GOLDEN MIRROR VARIATION", ["VETERANS I GOLDEN MIRROR VARIATION", "VETERANS II GOLDEN MIRROR VARIATION", "ROOKIE GOLDEN MIRROR VARIATION", "ROOKIE DEBUT GOLDEN MIRROR VARIATION", "VETERANS COMBOS GOLDEN MIRROR VARIATION", "SEASON HIGHLIGHTS GOLDEN MIRROR VARIATION"])
    combine(sections, "CLEAR VARIATION", ["VETERAN PLAYERS CLEAR VARIATION", "ROOKIE CLEAR VARIATION", "ROOKIE DEBUT CLEAR VARIATION", "VETERAN COMBOS CLEAR VARIATION", "SEASON HIGHLIGHTS CLEAR VARIATION"])
    combine(sections, "TRUE PHOTO VARIATION", ["VETERAN PLAYERS TRUE PHOTO VARIATION", "ROOKIES TRUE PHOTO VARIATION", "ROOKIE DEBUT TRUE PHOTO VARIATION", "VETERAN COMBOS TRUE PHOTO VARIATION", "SEASON HIGHLIGHTS TRUE PHOTO VARIATION"])
    combine(sections, "TEAM COLOR BORDER VARIATION", ["VETERAN PLAYERS TEAM COLOR BORDER VARIATION", "ROOKIES TEAM COLOR BORDER VARIATION", "ROOKIE DEBUT TEAM COLOR BORDER VARIATION", "VETERAN COMBOS TEAM COLOR BORDER VARIATION", "SEASON HIGHLIGHTS TEAM COLOR BORDER VARIATION"])
    combine(sections, "VINTAGE STOCK VARIATION", ["VETERAN PLAYERS VINTAGE STOCK VARIATION", "ROOKIES VINTAGE STOCK VARIATION", "ROOKIE DEBUT VINTAGE STOCK VARIATION", "VETERAN COMBOS VINTAGE STOCK VARIATION", "SEASON HIGHLIGHTS VINTAGE STOCK VARIATION"])
    combine(sections, "VALUE BOX HOLIDAY VARIATION", ["VETERAN PLAYERS VALUE BOX HOLIDAY VARIATION", "ROOKIES VALUE BOX HOLIDAY VARIATION", "ROOKIE DEBUT VALUE BOX HOLIDAY VARIATION", "VETERAN COMBOS VALUE BOX HOLIDAY VARIATION", "SEASON HIGHLIGHTS VALUE BOX HOLIDAY VARIATION"])
    combine(sections, "FLAGSHIP REAL ONE GOLDEN MIRROR AUTOGRAPH CARDS", ["FLAGSHIP REAL ONE GOLDEN MIRROR AUTOGRAPH CARDS", "FLAGSHIP REAL ONE GOLDEN MIRROR AUTOGRAPH CARDS II"])
    raw_rows, malformed_odds = parse_odds_pdf(odds_pdf)
    rows = []
    for index, raw in enumerate(raw_rows, 1):
        section = section_for_odds(raw["name"])
        if section not in sections:
            raise ValueError(f"Missing checklist section {section!r} for {raw['name']!r}")
        category = categories.get(section)
        if section.startswith("FLAGSHIP REAL ONE GOLDEN MIRROR"):
            category = "AUTOGRAPH"
        auto = category in {"AUTOGRAPH", "AUTOGRAPH RELIC"}
        relic = category in {"RELIC", "AUTOGRAPH RELIC"}
        holiday = raw["name"].startswith("VALUE BOX HOLIDAY BASE CARD VARIATION")
        rows.append({
            "id": f"update26-{index:03d}", "name": raw["name"], "section": section,
            "odds": raw["odds"], "auto": auto, "relic": relic, "hit": auto or relic,
            "holiday": holiday,
        })
    config = json.loads((PRODUCT / "config.json").read_text())
    data = {"id": PRODUCT.name, "config": config, "sections": sections, "odds": rows,
            "autographSections": [name for name, category in categories.items() if category in {"AUTOGRAPH", "AUTOGRAPH RELIC"}]}
    data["audit"] = audit(data)
    report = {
        "product": config["productName"], "oddsRows": len(rows), "oddsColumns": len(COLUMNS),
        "checklistSections": len(sections), "cardEntries": sum(map(len, sections.values())),
        "baseCards": len(sections["BASE SET"]), "unmappedOddsFamilies": [],
        "malformedOdds": malformed_odds, "malformedChecklist": skipped,
        "formats": config["formats"], "probabilityAudit": data["audit"], "notes": config["notes"],
        "sourceSha256": {checklist_pdf.name: hashlib.sha256(checklist_pdf.read_bytes()).hexdigest(), odds_pdf.name: hashlib.sha256(odds_pdf.read_bytes()).hexdigest()},
    }
    assert len(sections["BASE SET"]) == 350
    assert len(rows) == 274
    assert len(malformed_odds) == 1 and malformed_odds[0]["name"] == "TOPPS 75TH ANNIVERSARY GIFTS REDEMPTION CARDS"
    assert not skipped
    (PRODUCT / "product.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    (PRODUCT / "extraction-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(config["productName"], len(rows), len(sections), report["cardEntries"])


if __name__ == "__main__":
    build()
