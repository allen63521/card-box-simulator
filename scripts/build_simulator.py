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
    sections, current = {}, None
    malformed = []
    for raw in text.splitlines():
        line = clean(raw)
        if not line or line.lower().startswith(("checklists provided", "actual contents")):
            continue
        if re.fullmatch(r"[A-Z0-9][A-Z0-9 ’'&.\-]+", line) and not re.match(r"^[A-Z0-9]+-?\d+\s", line):
            if line not in skip and len(line) > 2:
                current = line
                sections.setdefault(current, [])
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
    return {k:v for k,v in sections.items() if v}, malformed

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
    sections, checklist_bad = parse_checklist(checklist_text)
    odds, odds_bad = parse_odds(odds_text, cfg["oddsColumns"])
    if cfg["baseSection"] not in sections: raise SystemExit(f"base section {cfg['baseSection']!r} not found; found {list(sections)[:12]}")
    for key,item in cfg["formats"].items():
        count=sum(1 for r in odds if r["odds"].get(item["oddsColumn"]))
        if not count: raise SystemExit(f"no odds parsed for requested format {key}")
    template = Path(__file__).resolve().parents[1]/"assets"/"frontend"
    for name in ("index.html","style.css","interactive.css","app.js"):
        shutil.copy2(template/name,args.output/name)
    payload={"config":cfg,"sections":sections,"odds":odds}
    (args.output/"data.js").write_text("window.SIM_DATA="+json.dumps(payload,ensure_ascii=False,separators=(",",":"))+";",encoding="utf-8")
    report={"product":cfg["productName"],"oddsRows":len(odds),"checklistSections":len(sections),"subjects":sum(map(len,sections.values())),"malformedOdds":odds_bad,"malformedChecklist":checklist_bad,"formats":cfg["formats"]}
    (args.output/"extraction-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    shutil.rmtree(work)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == "__main__": main()
