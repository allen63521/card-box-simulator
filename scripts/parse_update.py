"""Product-specific extraction for 2026 Topps Update Series."""
import re

COLUMNS = ("hobby", "jumbo", "value", "fat", "hanger", "super", "fanatics", "club_super", "japan")
CATEGORIES = {"INSERT", "AUTOGRAPH", "AUTOGRAPH RELIC", "RELIC"}


def clean(value):
    return re.sub(r"\s+", " ", value.replace("\f", " ")).strip()


def parse_odds_pdf(path):
    import pdfplumber
    rows, malformed = [], []
    with pdfplumber.open(path) as pdf:
        first = pdf.pages[0]
        first_row = sorted(
            [r for r in first.rects if r["x1"] - r["x0"] > 1100 and r["top"] >= 107],
            key=lambda r: r["top"],
        )[0]
        words = first.extract_words(x_tolerance=.1)
        ends = [
            w["x1"] + .06 for w in words
            if first_row["top"] <= w["top"] < first_row["bottom"]
            and (w["text"].startswith("1:") or w["text"] == "-")
        ]
        assert len(ends) == len(COLUMNS), ends
        bounds = [200] + ends
        for page_number, page in enumerate(pdf.pages, 1):
            rects = sorted(
                [r for r in page.rects if r["x1"] - r["x0"] > 1100 and r["top"] >= 107],
                key=lambda r: r["top"],
            )
            for rect in rects:
                chars = [c for c in page.chars if rect["top"] <= c["top"] < rect["bottom"]]

                def cell(left, right):
                    selected = [c for c in chars if left <= c["x0"] + .05 and c["x1"] <= right + .05]
                    lines = {}
                    for char in selected:
                        lines.setdefault(round(char["top"], 1), []).append(char)
                    return " ".join(
                        "".join(c["text"] for c in sorted(line, key=lambda c: c["x0"])).strip()
                        for _, line in sorted(lines.items())
                    ).strip()

                name = clean(cell(0, 200))
                tokens = [cell(bounds[i], bounds[i + 1]).replace(" ", "") for i in range(len(COLUMNS))]
                if not name or name == "Card":
                    continue
                if all(not token for token in tokens):
                    if rows:
                        rows[-1]["name"] = clean(rows[-1]["name"] + " " + name)
                    continue
                if not all(token == "-" or re.fullmatch(r"1:[0-9,]+", token) for token in tokens):
                    malformed.append({"page": page_number, "name": name, "tokens": tokens})
                    continue
                odds = {
                    column: None if token == "-" else int(token.split(":", 1)[1].replace(",", ""))
                    for column, token in zip(COLUMNS, tokens)
                }
                rows.append({"name": name, "odds": odds, "sourcePage": page_number})
    return rows, malformed


def parse_checklist(text):
    sections, categories, skipped = {}, {}, []
    category = current = None
    card_re = re.compile(r"^([A-Z0-9]+(?:-[A-Z0-9]+)*)\s+(.+)$")
    ignored = ("checklists provided", "that product", "odds may vary", "2026 topps update")
    for line_number, raw in enumerate(text.splitlines(), 1):
        line = clean(raw)
        if not line or line.lower().startswith(ignored) or line.startswith("*"):
            continue
        if line in CATEGORIES:
            category, current = line, None
            continue
        # Headings are all-caps and have no column gap; this also preserves numeric headings.
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
            entry = {"code": code, "name": parts[0], "team": parts[1] if len(parts) > 1 else "", "rookie": rookie}
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
        ("VALUE BOX HOLIDAY BASE CARD VARIATION", "VALUE BOX HOLIDAY VARIATION"),
        ("BASE CARD CLEAR VARIATION", "CLEAR VARIATION"),
        ("BASE CARD VINTAGE STOCK VARIATION", "VINTAGE STOCK VARIATION"),
        ("BASE CARD GOLDEN MIRROR", "GOLDEN MIRROR VARIATION"),
        ("GOLDEN MIRROR LEGEND VARIATIONS", "GOLDEN MIRROR LEGEND VARIATIONS"),
        ("TRUE PHOTO VARIATIONS", "TRUE PHOTO VARIATION"),
        ("TEAM COLOR BORDER VARIATIONS", "TEAM COLOR BORDER VARIATION"),
        ("BASE CARD PLAYER NUMBER VARIATIONS", "BASE CARDS PLAYER NUMBER VARIATION"),
        ("BASE CARD TRADED PLAYER SP", "TRADED PLAYERS SHORT PRINT VARIATION"),
        ("BASE CARDS ", "BASE SET"),
        ("STAT STARS", "STAT STARS"),
        ("AUTUMN ASCENSIONS", "AUTUMN ASCENSIONS"),
        ("2026 ALL STAR GAME AUTOGRAPH", "2026 ALL STAR GAME AUTOGRAPH PARALLEL"),
        ("2026 ALL STAR GAME", "2026 ALL STAR GAME"),
        ("TOPPS BLACK GOLD", "TOPPS BLACK GOLD"),
        ("MYSTICAL", "MYSTICAL"),
        ("FIRST PITCH AUTOGRAPH", "FIRST PITCH AUTOGRAPH PARALLEL"),
        ("FIRST PITCH", "FIRST PITCH"),
        ("HEAVY LUMBER AUTOGRAPH RELIC", "HEAVY LUMBER AUTOGRAPH RELICS"),
        ("HEAVY LUMBER", "HEAVY LUMBER"),
        ("HOME FIELD", "HOME FIELD"),
        ("1991 TOPPS BASEBALL ALL-STAR AUTOS", "1991 TOPPS BASEBALL ALL STAR AUTOGRAPH CARDS"),
        ("1991 TOPPS BASEBALL AUTOGRAPH CARDS", "1991 TOPPS BASEBALL AUTOGRAPH CARDS"),
        ("1991 TOPPS BASEBALL RELIC CARD", "1991 TOPPS BASEBALL RELIC CARDS"),
        ("1991 TOPPS BASEBALL", "1991 TOPPS BASEBALL"),
        ("STARS OF MLB", "STARS OF MLB"),
        ("ALL ACES", "ALL ACES"),
        ("ALL KINGS", "ALL KINGS"),
        ("MATT SZCZUR ART CARDS", "MATT SZCZUR ART CARDS"),
        ("BASE CARD ROOKIE 1952 AUTOGRAPH VARIATION", "BASE CARD ROOKIE 1952 AUTOGRAPH VARIATION"),
        ("BASE CARD ROOKIE 1952 VARIATION", "BASE CARD ROOKIE 1952 VARIATION"),
        ("COVER ATHLETES AUTOGRAPHS CARDS", "COVER ATHLETES AUTOGRAPH CARDS"),
        ("COVER ATHLETES CARDS", "COVER ATHLETES CARDS"),
        ("TOPPS FLAGSHIP AUTOGRAPH PATCH CARDS", "TOPPS FLAGSHIP AUTOGRAPH PATCH CARDS"),
        ("BASEBALL STARS AUTOGRAPHS", "BASEBALL STARS AUTOGRAPHS"),
        ("FLAGSHIP REAL ONE GOLDEN MIRROR AUTOGRAPH CARDS", "FLAGSHIP REAL ONE GOLDEN MIRROR AUTOGRAPH CARDS"),
        ("FLAGSHIP REAL ONE AUTOGRAPH CARDS", "FLAGSHIP REAL ONE AUTOGRAPH CARDS"),
        ("MAJOR LEAGUE MATERIAL DUAL AUTO", "MAJOR LEAGUE MATERIAL DUAL AUTOGRAPH CARDS"),
        ("MAJOR LEAGUE MATERIAL CARDS AUTOGRAPH", "MAJOR LEAGUE MATERIAL CARDS AUTOGRAPH PARALLEL"),
        ("MAJOR LEAGUE MATERIAL CARDS", "MAJOR LEAGUE MATERIAL CARDS"),
        ("RISING ROOKIE RELIC CARDS AUTOGRAPH", "RISING ROOKIE RELIC CARDS AUTOGRAPH PARALLEL"),
        ("RISING ROOKIE RELIC CARDS", "RISING ROOKIE RELIC CARDS"),
        ("REAL ONE RELICS", "REAL ONE RELICS"),
        ("ALL STAR STITCHES CARDS AUTOGRAPH", "ALL STAR STITCHES CARDS AUTOGRAPH PARALLEL"),
        ("ALL STAR STITCHES CARDS", "ALL STAR STITCHES CARDS"),
        ("FANATICS AUTHENTIC REDEMPTION CARDS", "FANATICS AUTHENTIC REDEMPTION CARDS"),
        ("OVERSIZED 2026 BASE CARD", "OVERSIZED 2026 BASE CARD"),
        ("OVERSIZED 1991 TOPPS BASEBALL CARD", "OVERSIZED 1991 TOPPS BASEBALL CARD"),
        ("COMPANION CARD", "COMPANION CARD"),
        ("WORLD CHAMPION AUTOGRAPHS", "WORLD CHAMPION AUTOGRAPH CARDS"),
        ("POSTSEASON PERFORMANCE AUTOGRAPHS", "POSTSEASON PERFORMANCE AUTOGRAPH CARDS"),
        ("75 YEARS OF TOPPS DIE CUT AUTOGRAPHS", "75 YEARS OF TOPPS DIE CUT AUTOGRAPHS"),
        ("75 YEARS OF TOPPS BASEBALL AUTOGRAPHS", "75 YEARS OF TOPPS BASEBALL AUTOGRAPHS"),
        ("ROUNDING THE BASES AUTO RELIC", "ROUNDING THE BASES RELIC AUTOGRAPH"),
        ("CITY CONNECT SWATCH AUTO RELIC", "CITY CONNECT AUTOGRAPH RELIC"),
        ("ICONIC BUYBACK REDEMPTION CARDS", "ICONIC BUYBACK REDEMPTIONS"),
    )
    for prefix, section in rules:
        if name.startswith(prefix):
            return section
    raise ValueError("Unmapped odds family: " + name)
