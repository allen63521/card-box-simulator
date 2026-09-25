#!/usr/bin/env python3
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

def text_from_pdf(path, destination):
    proc = subprocess.run(["pdftotext", "-layout", str(path), str(destination)], capture_output=True, text=True)
    if proc.returncode:
        raise SystemExit(f"pdftotext failed for {path}: {proc.stderr.strip()}")
    return destination.read_text(encoding="utf-8", errors="replace")

def clean(value):
    return re.sub(r"\s+", " ", value.replace("\f", " ")).strip()

def parse_checklist(text):
    skip = {"BASE", "INSERT", "AUTOGRAPH", "RELIC", "AUTOGRAPH RELIC"}
    sections, current, category = {}, None, None
    section_categories = {}
    malformed = []
    for raw in text.splitlines():
        line = clean(raw)
        if not line or line.lower().startswith(("checklists provided", "actual contents")):
            continue
        if line in skip:
            category, current = line, None
            continue
        if re.fullmatch(r"[A-Z0-9][A-Z0-9 ’'&.\-]+", line):
            if len(line) > 2:
                current = line
                sections.setdefault(current, [])
                section_categories[current] = category
            continue
        if not current:
            continue
        parts = [clean(p) for p in re.split(r"\s{2,}", raw.replace("\f", " ").strip()) if clean(p)]
        if len(parts) < 2 or not re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*|\d+", parts[0]):
            continue
        code, name = parts[0], parts[1]
        if name.lower() in {"rookie", "production"}:
            continue
        remainder = parts[2:]
        rookie = any(re.fullmatch(r"(?:ROOKIE|RC)", part, re.IGNORECASE) for part in remainder)
        team = next((part for part in remainder if not re.fullmatch(r"(?:ROOKIE|RC)", part, re.IGNORECASE)), "")
        sections[current].append({"code": code, "name": name, "team": team, "rookie": rookie})
    rookie_names = {
        entry["name"].casefold()
        for section, entries in sections.items()
        if "ROOKIE" in section.upper()
        for entry in entries
    }
    rookie_names.update(
        entry["name"].casefold()
        for entries in sections.values()
        for entry in entries
        if entry.get("rookie")
    )
    for entries in sections.values():
        for entry in entries:
            entry["rookie"] = entry.get("rookie", False) or entry["name"].casefold() in rookie_names
    populated = {k:v for k,v in sections.items() if v}
    return populated, malformed, {k:section_categories.get(k) for k in populated}

def parse_odds(text, columns):
    token_re = re.compile(r"1:[0-9,]+|0\.\d+|-")
    rows, malformed = [], []
    for number, raw in enumerate(text.splitlines(), 1):
        line = clean(raw)
        tokens = token_re.findall(line)
        if len(tokens) < len(columns):
            continue
        tokens = tokens[-len(columns):]
        match = re.search(r"\s{2,}(?=(?:1:[0-9,]+|0\.\d+|-)(?:\s|$))", raw)
        if not match:
            continue
        name = clean(raw[:match.start()])
        if not name or name.upper() in {x.upper() for x in columns} or name.startswith("Card "):
            continue
        parsed, bad = {}, False
        for column, token in zip(columns, tokens):
            if token == "-": parsed[column] = None
            elif token.startswith("0."):
                parsed[column] = None; bad = True
            else: parsed[column] = int(token.split(":",1)[1].replace(",",""))
        if bad: malformed.append({"line": number, "text": line, "reason": "decimal extraction artifact"})
        if any(parsed.values()): rows.append({"name": name, "odds": parsed})
    unique = {(r["name"], tuple(r["odds"].items())):r for r in rows}
    return list(unique.values()), malformed

def main():
    ap = argparse.ArgumentParser(description="Build an offline trading-card box simulator")
    ap.add_argument("--odds", required=True, type=Path)
    ap.add_argument("--checklist", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    for key in ("productName","formats","oddsColumns","baseSection"):
        if key not in cfg: raise SystemExit(f"config missing required key: {key}")
    for key, item in cfg["formats"].items():
        if item.get("oddsColumn") not in cfg["oddsColumns"]: raise SystemExit(f"{key}.oddsColumn is not in oddsColumns")
        if int(item.get("packs",0)) < 1 or int(item.get("cards",0)) < 1: raise SystemExit(f"{key} needs positive packs/cards")
    args.output.mkdir(parents=True, exist_ok=True)
    work = args.output / ".extract"
    work.mkdir(exist_ok=True)
    odds_text = text_from_pdf(args.odds, work/"odds.txt")
    checklist_text = text_from_pdf(args.checklist, work/"checklist.txt")
    sections, checklist_bad, section_categories = parse_checklist(checklist_text)
    odds, odds_bad = parse_odds(odds_text, cfg["oddsColumns"])
    if cfg["baseSection"] not in sections: raise SystemExit(f"base section {cfg['baseSection']!r} not found; found {list(sections)[:12]}")
    for key,item in cfg["formats"].items():
        count=sum(1 for r in odds if r["odds"].get(item["oddsColumn"]))
        if not count: raise SystemExit(f"no odds parsed for requested format {key}")
    template = Path(__file__).resolve().parents[1]/"assets"/"frontend"
    for name in ("index.html","style.css","interactive.css","app.js"):
        shutil.copy2(template/name,args.output/name)
    autograph_sections = [name for name, category in section_categories.items() if category in {"AUTOGRAPH", "AUTOGRAPH RELIC"}]
    payload={"config":cfg,"sections":sections,"odds":odds,"autographSections":autograph_sections}
    data_path = args.output/"data.js"
    data_path.write_text("window.SIM_DATA="+json.dumps(payload,ensure_ascii=False,separators=(",",":"))+";",encoding="utf-8")
    required_output = [args.output/name for name in ("index.html", "style.css", "interactive.css", "app.js", "data.js")]
    missing_output = [path.name for path in required_output if not path.is_file() or path.stat().st_size == 0]
    if missing_output:
        raise SystemExit(f"incomplete simulator output; missing or empty: {', '.join(missing_output)}")
    auto_re = re.compile(cfg.get("autographPattern", "AUTOGRAPH|AUTOGRAPHS|AUTOGRAPHED"), re.I)
    autograph_names = tuple(clean(name).upper() for name in autograph_sections)
    def is_autograph_row(name):
        normalized = clean(name).upper()
        return bool(auto_re.search(name)) or any(section in normalized for section in autograph_names)
    probability_audit = {}
    for key, item in cfg["formats"].items():
        column = item["oddsColumn"]
        rows = [row for row in odds if row["odds"].get(column)]
        expected_hits = sum(1 / row["odds"][column] for row in rows)
        expected_autos = sum(1 / row["odds"][column] for row in rows if is_autograph_row(row["name"]))
        probability_audit[key] = {
            "publishedRows": len(rows),
            "expectedNonBasePerPack": round(expected_hits, 6),
            "expectedNonBasePerBox": round(expected_hits * item["packs"], 6),
            "naturalExpectedAutosPerBox": round(expected_autos * item["packs"], 6),
            "guaranteedAutosPerBox": int(item.get("guaranteedAutos", 0)),
        }
    report={"product":cfg["productName"],"oddsRows":len(odds),"checklistSections":len(sections),"subjects":sum(map(len,sections.values())),"autographSections":autograph_sections,"malformedOdds":odds_bad,"malformedChecklist":checklist_bad,"formats":cfg["formats"],"probabilityAudit":probability_audit}
    (args.output/"extraction-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.rmtree(work)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == "__main__": main()
