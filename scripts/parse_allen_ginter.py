"""Product-specific parsers for the 2026 Topps Allen & Ginter PDFs."""
import re

COLUMNS = ("fat", "hobby", "value")
CATEGORIES = {"BASE", "INSERT", "RELIC", "AUTOGRAPH", "AUTOGRAPH RELIC"}


def clean(value):
    return re.sub(r"\s+", " ", value.replace("\f", " ")).strip()


def parse_odds(text):
    row_re = re.compile(
        r"^(?P<name>.*?)\s{2,}(?P<fat>1:[0-9,]+|-)\s+"
        r"(?P<hobby>1:[0-9,]+|-)\s+(?P<value>1:[0-9,]+|-)\s*$"
    )
    rows = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        match = row_re.match(raw.replace("\f", ""))
        if not match:
            continue
        name = clean(match.group("name"))
        if not name or name == "Card":
            continue
        odds = {
            column: None if match.group(column) == "-" else int(match.group(column).split(":", 1)[1].replace(",", ""))
            for column in COLUMNS
        }
        rows.append({"name": name, "odds": odds, "sourceLine": line_no})
    return rows


def parse_checklist(text):
    sections, categories, skipped = {}, {}, []
    category = current = None
    heading_re = re.compile(r"^[A-Z0-9][A-Z0-9 &’'()/.,:+-]+$")
    card_re = re.compile(r"^([A-Z0-9]+(?:-[A-Z0-9]+)*)\s+(.+)$")
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = clean(raw)
        if not line or line.lower().startswith(("checklists provided", "that product", "odds may vary")):
            continue
        if line in CATEGORIES:
            category, current = line, None
            continue
        if (heading_re.fullmatch(line) and len(line) > 2
                and not re.match(r"^(?:\d+|[A-Z0-9]+-\d+)\s", line)):
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
            name = parts[0]
            team = parts[1] if len(parts) > 1 else ""
            entry = {"code": code, "name": name, "team": team, "rookie": rookie}
            existing = next((item for item in sections[current] if item["code"] == code), None)
            if existing:
                if name not in existing["name"].split(" / "):
                    existing["name"] += " / " + name
                if team and team not in existing["team"].split(" / "):
                    existing["team"] = (existing["team"] + " / " + team).strip(" / ")
                existing["rookie"] = existing["rookie"] or rookie
            else:
                sections[current].append(entry)
            continue
    sections = {name: cards for name, cards in sections.items() if cards}
    categories = {name: categories.get(name) for name in sections}
    return sections, categories, skipped


def section_for_odds(name):
    rules = (
        ("BASE CARD CHROME VARIATION", "BASE CARDS CHROME VARIATION"),
        ("BASE CARD MINI SIZED METALS", "BASE CARDS I MINI METAL VARIATION"),
        ("BASE CARD MINI SIZED", "BASE CARDS I MINI VARIATION"),
        ("BASE CARDS ", "BASE CARDS"),
        ("BASE CARD DAGUERREOTYPE", "DAGUERREOTYPE BASE CARD VARIATIONS"),
        ("BASE CARD MINI STAINED GLASS", "BASE CARDS I MINI STAINED GLASS VARIATION"),
        ("BASE MINI CARD CHROME", "BASE CARDS MINI CHROME VARIATION"),
        ("TIN TYPE", "TIN TYPE BASE CARD VARIATION"),
        ("50 WAYS TO SAY HELLO", "MINI 50 WAYS TO SAY HELLO"),
        ("ALLEN & GINTER DOUBLE RIP", "DOUBLE RIP CARDS"),
        ("ALLEN & GINTER RIP", "RIP CARDS I"),
        ("MUSICAL METHODS", "MINI MUSICAL METHODS"),
        ("N34", "N34"),
        ("N43", "N43"),
        ("ROOKIE DESIGN", "ROOKIE DESIGN VARIATIONS"),
        ("UNIFORM COUNTDOWN", "UNIFORM COUNTDOWN"),
        ("WICKED POWER", "WICKED POWER"),
        ("ALLEN & GINTER FRAMED RELICS MINI", "ALLEN AND GINTER FRAMED RELICS MINI SIZE"),
        ("ALLEN & GINTER DUAL AUTOGRAPH FULL SIZE", "DUAL AUTOGRAPHS"),
        ("ALLEN & GINTER QUINTUPLE AUTOGRAPH", "QUINTUPLE AUTOGRAPHS"),
        ("ALLEN & GINTER AUTOGRAPHS FULL SIZE", "FULL SIZE AUTOGRAPH CARDS"),
        ("ALLEN & GINTER AUTOGRAPHED LINEUP", "ALLEN AND GINTER AUTOGRAPHED LINEUP CARD RELICS"),
        ("ALLEN & GINTER DUAL AUTOGRAPHED RELIC", "DUAL AUTOGRAPH RELIC CARDS"),
        ("ALLEN & GINTER AUTOGRAPHED RELIC", "AUTOGRAPH RELIC CARDS"),
        ("ALLEN & GINTER EMPLOYEE AUTOGRAPH", "MINI EMPLOYEE AUTOGRAPHS"),
        ("CARTE DE VISITE", "CARTE DE VISITE AUTOGRAPHS"),
        ("RELIC CUT SIGNATURES", "RELIC CUT SIGNATURES"),
        ("CUT SIGNATURES", "CUT SIGNATURES"),
        ("DYNASTY AUTOGRAPHED PATCH", "DYNASTY AUTOGRAPHED PATCH CARDS"),
        ("MINI BASEBALL AUTOGRAPH", "MINI BASEBALL AUTOGRAPHS I"),
        ("MINI NON BASEBALL AUTOGRAPH", "MINI NON BASEBALL AUTOGRAPHS"),
        ("ALLEN & GINTER LINEUP CARD RELICS", "ALLEN AND GINTER LINEUP CARD RELICS"),
        ("ALLEN & GINTER RELICS FULL SIZE A", "ALLEN AND GINTER RELICS FULL SIZE A"),
        ("ALLEN & GINTER RELICS FULL SIZE B", "ALLEN AND GINTER RELICS FULL SIZE B"),
    )
    for prefix, section in rules:
        if name.startswith(prefix):
            return section
    raise ValueError("Unmapped odds family: " + name)
