"""Product-specific extraction for 2026 Topps Cosmic Chrome Baseball."""
import re

COLUMNS = ("hobby", "lunar")
CATEGORIES = {"BASE", "INSERT", "AUTOGRAPH", "RELIC"}


def clean(value):
    return re.sub(r"\s+", " ", value.replace("\f", " ")).strip()


def parse_odds(text):
    rows, malformed = [], []
    row_re = re.compile(r"^(.*?)\s+(1:[0-9,]+|-)\s+(1:[0-9,]+|-)\s*$")
    continuations = {
        "REFRACTOR", "DUST REFRACTOR", "INTERSTELLAR REFRACTOR",
    }
    ignored = (
        "2026 Topps Cosmic Chrome", "but actual contents", "Card ",
    )
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = clean(raw)
        if not line or line.startswith(ignored):
            continue
        match = row_re.match(line)
        if match:
            name, hobby, lunar = match.groups()
            rows.append({
                "name": clean(name),
                "odds": {
                    "hobby": None if hobby == "-" else int(hobby[2:].replace(",", "")),
                    "lunar": None if lunar == "-" else int(lunar[2:].replace(",", "")),
                },
                "sourceLine": line_number,
            })
        elif line in continuations and rows:
            rows[-1]["name"] = clean(rows[-1]["name"] + " " + line)
        elif "1:" in line:
            malformed.append({"line": line_number, "text": line})
    return rows, malformed


def parse_checklist(text):
    sections, categories, skipped = {}, {}, []
    category = current = None
    card_re = re.compile(r"^([A-Z0-9]+(?:-[A-Z0-9]+)*)\s+(.+)$")
    ignored = ("checklists provided", "the time of production")
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = clean(raw)
        if not line or line.lower().startswith(ignored):
            continue
        if line in CATEGORIES:
            category, current = line, None
            continue
        if line == line.upper() and re.search(r"[A-Z]", line) and not re.search(r"\s{2,}", raw.strip()):
            current = line
            sections.setdefault(current, [])
            categories[current] = category
            continue
        match = card_re.match(raw.replace("\f", " ").strip())
        if match and current:
            code, remainder = match.groups()
            parts = [clean(part) for part in re.split(r"\s{2,}", remainder) if clean(part)]
            if not parts:
                skipped.append({"line": line_number, "section": current, "text": line})
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
            existing = next((card for card in sections[current] if card["code"] == code), None)
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


def section_for_odds(name):
    rules = (
        ("COSMIC CHROME AUTOGRAPH VARIATION", "COSMIC CHROME AUTOGRAPH VARIATION"),
        ("COSMIC EXPLORERS CUT SIGNATURE", "COSMIC EXPLORERS CUT SIGNATURES"),
        ("EXTRATERRESTRIAL TALENT AUTOGRAPH VARIATION", "EXTRATERRESTRIAL TALENT AUTOGRAPH VARIATION"),
        ("LAUNCHED INTO ORBIT AUTOGRAPH VARIATION", "LAUNCHED INTO ORBIT AUTOGRAPH VARIATION"),
        ("STAR CLUSTERS DUAL AUTOGRAPH", "STAR CLUSTERS DUAL AUTOGRAPHS"),
        ("STELLAR STARS AUTOGRAPH VARIATION", "STELLAR STARS AUTOGRAPH VARIATION"),
        ("BASE CARD ANTI-GRAVITY VARIATION", "BASE CARDS ANTI GRAVITY VARIATION"),
        ("BASE CARD CONSTELLATION VARITION", "BASE CARDS CONSTELLATION VARIATION"),
        ("BASE CARDS", "BASE CARDS"),
        ("COSMIC DUST", "COSMIC DUST"),
        ("DUAL STAR CLUSTER", "DUAL STAR CLUSTERS"),
        ("EXTRATERRESTRIAL TALENT", "EXTRATERRESTRIAL TALENT"),
        ("FORCES OF THE DIAMOND", "FORCES OF THE DIAMOND"),
        ("LAUNCHED INTO ORBIT", "LAUNCHED INTO ORBIT"),
        ("MARS ATTACKS MLB", "MARS ATTACKS MLB"),
        ("PLANETARIUM", "PLANETARIUM"),
        ("PLANETARY PURSUIT", "PLANETARY PURSUIT"),
        ("STARFRACTOR", "STARFRACTOR"),
        ("STARS IN THE NIGHT", "STARS IN THE NIGHT"),
        ("STELLA NOVA", "STELLA NOVA"),
        ("STELLAR STARS", "STELLAR STARS"),
        ("SUPERNOVA", "SUPERNOVA"),
        ("TRIPLE STAR CLUSTERS", "TRIPLE STAR CLUSTERS"),
    )
    for prefix, section in rules:
        if name.startswith(prefix):
            return section
    raise ValueError("Unmapped odds family: " + name)
