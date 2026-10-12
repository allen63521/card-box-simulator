"""Product-specific parsers for the 2026 Topps Museum Collection PDFs."""
import re

COLUMNS = ("hobby",)
CATEGORIES = {"AUTOGRAPH", "AUTOGRAPH RELIC", "RELIC"}


def clean(value):
    return re.sub(r"\s+", " ", value.replace("\f", " ")).strip()


def parse_odds(text):
    row_re = re.compile(r"^(?P<name>.*?)\s{2,}(?P<hobby>1:[0-9,]+)\s*$")
    rows = []
    museum_memorabilia_seen = 0
    for line_no, raw in enumerate(text.splitlines(), 1):
        match = row_re.match(raw.replace("\f", ""))
        if not match:
            continue
        name = clean(match.group("name"))
        if not name or name == "Cards":
            continue
        occurrence = None
        if name.startswith("Museum Memorabilia"):
            if name == "Museum Memorabilia":
                museum_memorabilia_seen += 1
            occurrence = 1 if museum_memorabilia_seen <= 1 else 2
        rows.append({
            "name": name,
            "odds": {"hobby": int(match.group("hobby").split(":", 1)[1].replace(",", ""))},
            "sourceLine": line_no,
            "occurrence": occurrence,
        })
    return rows


def parse_checklist(text):
    sections, categories, skipped = {}, {}, []
    category = current = None
    heading_re = re.compile(r"^[A-Z0-9][A-Z0-9 &’'()/.,:+*-]+$")
    card_re = re.compile(r"^([A-Z0-9]+(?:-[A-Z0-9]+)*)\s+(.+)$")
    ignored = (
        "checklists provided", "that product", "odds may vary", "2026 topps museum",
        "*also look for",
    )
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = clean(raw)
        if not line or line.lower().startswith(ignored):
            continue
        if line in CATEGORIES:
            category, current = line, None
            continue
        if heading_re.fullmatch(line) and len(line) > 2 and not re.match(r"^\d+\s", line):
            current = line
            sections.setdefault(current, [])
            categories[current] = category
            continue
        match = card_re.match(raw.replace("\f", " ").strip())
        if match and current:
            code, remainder = match.groups()
            parts = [clean(part) for part in re.split(r"\s{2,}", remainder) if clean(part)]
            if not parts:
                skipped.append({"line": line_no, "text": line})
                continue
            rookie = parts[-1].upper() in {"ROOKIE", "RC"}
            if rookie:
                parts.pop()
            entry = {
                "code": code,
                "name": parts[0],
                "team": parts[1] if len(parts) > 1 else "",
                "rookie": rookie,
            }
            existing = next((item for item in sections[current] if item["code"] == code), None)
            if existing:
                if entry["name"] not in existing["name"].split(" / "):
                    existing["name"] += " / " + entry["name"]
                if entry["team"] and entry["team"] not in existing["team"].split(" / "):
                    existing["team"] = (existing["team"] + " / " + entry["team"]).strip(" / ")
                existing["rookie"] = existing["rookie"] or rookie
            else:
                sections[current].append(entry)
    sections = {name: cards for name, cards in sections.items() if cards}
    categories = {name: categories.get(name) for name in sections}
    return sections, categories, skipped


def section_for_odds(row):
    name = row["name"]
    if name.startswith("Base"):
        return "BASE CARDS"
    if name.startswith("Museum Memorabilia"):
        return "MUSEUM MEMORABILIA I" if (row["occurrence"] or 1) == 1 else "MUSEUM MEMORABILIA II"
    rules = (
        ("Meaningful Material Relics", "MEANINGFUL MATERIAL RELICS"),
        ("Momentous Material Jumbo Relics", "MOMENTOUS MATERIAL JUMBO RELICS"),
        ("Jumbo Bat Nameplate Relics", "JUMBO LUMBER BAT NAMEPLATE RELICS"),
        ("Dual-Player Primary Pieces Dual Relics", "DUAL PLAYER PRIMARY PIECES DUAL RELICS"),
        ("Single-Player Primary Pieces Dual Relics Legends", "SINGLE PLAYER PRIMARY PIECES DUAL RELICS LEGENDS"),
        ("Single-Player Primary Pieces Triple Relics", "SINGLE PLAYER PRIMARY PIECES TRIPLE RELICS"),
        ("Three-Player Primary Pieces Triple Relics", "THREE PLAYER PRIMARY PIECES TRIPLE RELICS"),
        ("Archival Autographs", "ARCHIVAL AUTOGRAPHS"),
        ("Retrospective Signatures", "RETROSPECTIVE SIGNATURES"),
        ("Atelier Autographed Book", "ATELIER AUTOGRAPHED BOOK CARDS"),
        ("Dual On-Card Autographs", "DUAL ON CARD AUTOGRAPHS"),
        ("Pastime Portraits", "PASTIME PORTRAITS"),
        ("Showpieces", "SHOWPIECES"),
        ("Framed Hall of Fame Autographs", "FRAMED HALL OF FAME AUTOGRAPHS"),
        ("Museum Framed Autographs", "MUSEUM FRAMED AUTOGRAPHS"),
        ("Museum Framed Autograph Relic", "MUSEUM FRAMED AUTOGRAPH RELICS"),
        ("Momentous Material Jumbo Patch Autographs", "MOMENTOUS MATERIAL JUMBO PATCH AUTOGRAPHS"),
        ("Momentous Material Dual Jumbo Patch Autograph Book", "MOMENTOUS MATERIAL DUAL JUMBO PATCH AUTOGRAPH BOOK"),
        ("Dual-Player Signature Swatches Dual Relic Autographs", "DUAL PLAYER SIGNATURE SWATCHES DUAL RELIC AUTOGRAPHS"),
        ("Single-Player Signature Swatches Dual Relic Autographs", "SINGLE PLAYER SIGNATURE SWATCHES DUAL RELIC AUTOGRAPHS"),
        ("Single-Player Signature Swatches Triple Relic Autographs", "SINGLE PLAYER SIGNATURE SWATCHES TRIPLE RELIC AUTOGRAPHS"),
        ("Autographed Jumbo Lumber Bat Relics", "AUTOGRAPHED JUMBO LUMBER BAT RELICS"),
        ("Lifetime Members Relic Autographs", "LIFETIME MEMBERS RELIC AUTOGRAPHS"),
        ("Written in History Relic Autographs", "WRITTEN IN HISTORY RELIC AUTOGRAPHS"),
        ("Dual Autographed Jumbo Lumber Bat Relics Book", "DUAL AUTOGRAPHED JUMBO LUMBER BAT RELIC BOOK"),
        ("Museum Framed Dual Autograph Relic Book", "MUSEUM FRAMED DUAL AUTOGRAPH RELIC BOOK"),
        ("Canvas Collection Originals Player Autographs", "CANVAS COLLECTION ORIGINAL PLAYER AUTOGRAPHS"),
    )
    for prefix, section in rules:
        if name.startswith(prefix):
            return section
    if name.startswith(("Canvas Collection Museum Murals", "Canvas Collection Originals", "Faces of Greatness")):
        return "BASE CARDS"
    raise ValueError("Unmapped odds family: " + name)
