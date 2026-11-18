"""Step 1b: split the downloaded laws into recitals, articles and annexes.

Run:  python -m src.parse_laws

Input:  data/raw/*.html        (from src.download_laws)
Output: data/processed/laws.jsonl   (one piece of law per line, with labels)

How it works, in 3 steps:
1. Clean the HTML: remove footnotes and the little change markers (like ▼M1).
2. Turn the page into simple text lines, one line per paragraph.
3. Read the lines from top to bottom. Lines like "Article 6" start a new
   article, "(12)" starts a new recital, "ANNEX III" starts a new annex.
"""
import json
import re
import warnings
from collections import Counter

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# EUR-Lex pages are XHTML; the HTML reader handles them fine, so hide this warning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from src.config import PROCESSED_DIR, RAW_DIR
from src.sources import EXPECTED, SOURCES

# ---------- Patterns for English and German ----------
ARTICLE = re.compile(r"^(?:Article|Artikel)\s+(\d+[a-z]*)$")
ANNEX = re.compile(r"^(?:ANNEX|ANHANG)\s+([IVXLC]+[a-z]*)$")
CHAPTER = re.compile(r"^(?:CHAPTER|KAPITEL)\s+([IVXLC]+[a-z]*)$")
SECTION = re.compile(r"^(?:SECTION|ABSCHNITT)\s+(\d+[a-z]*)$", re.I)  # GDPR writes "Section 1"
RECITAL = re.compile(r"^\((\d+)\)\s*(.*)$")
WHEREAS = re.compile(r"^(?:Whereas|in Erwägung nachstehender Gründe)\s*:?$", re.I)
ADOPTED = re.compile(r"^(?:HAVE ADOPTED THIS REGULATION|HABEN FOLGENDE VERORDNUNG ERLASSEN)\s*:?$", re.I)
SIGNATURE = re.compile(r"^(?:Done at|Geschehen zu)\b")
FOOTNOTE = re.compile(r"^\(\*?\d+\)\s+(?:OJ|ABl\.)\s")
MARKER = re.compile(r"[▼►◄]\s*(?:[BMACR]\d*)?")  # change markers in consolidated texts
ONLY_DASHES = re.compile(r"^[—\-–\s]+$")  # a deleted provision shows as "—————"


# ---------- 1. Clean the HTML ----------
def clean_html(html: str) -> BeautifulSoup:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "head", "nav"]):
        tag.decompose()
    # footnote texts (at the end of the page)
    for tag in soup.select(".note, .oj-note, [id^=ntc]"):
        tag.decompose()
    # footnote numbers inside the text, like "(3)" linking to a footnote
    for a in soup.find_all("a", href=True):
        if a["href"].startswith("#") and re.fullmatch(r"\(\*?\d+\)", a.get_text(strip=True)):
            a.decompose()
    for tag in soup.select(".oj-note-tag, .note-tag"):
        tag.decompose()
    return soup


# ---------- 2. Turn the page into text lines ----------
def is_line_element(tag) -> bool:
    if tag.name in ("p", "tr"):
        return True
    # consolidated texts put numbered paragraphs in <div class="norm">
    # and points like "(a) ..." in <div class="grid-container">
    classes = tag.get("class") or []
    return tag.name == "div" and ("norm" in classes or "grid-container" in classes)


def to_lines(soup: BeautifulSoup) -> list[str]:
    lines, taken = [], set()
    for tag in soup.find_all(is_line_element):
        # skip a tag that sits inside one we already used (its text is already in)
        if any(id(parent) in taken for parent in tag.parents):
            continue
        taken.add(id(tag))
        if tag.name == "tr":
            text = " ".join(cell.get_text(" ", strip=True) for cell in tag.find_all(["td", "th"], recursive=False))
        else:
            text = tag.get_text(" ", strip=True)
        text = MARKER.sub("", text.replace("\xa0", " "))
        text = re.sub(r"\s+", " ", text).strip()
        if text and not ONLY_DASHES.match(text):
            lines.append(text)
    return lines


# ---------- 3. Read the lines and build the pieces ----------
def split_lines(lines: list[str]) -> list[dict]:
    pieces = []
    current = None
    zone = "start"  # start -> recitals -> body -> end
    chapter = section = ""
    waiting_for = None  # "chapter", "section", "article" or "annex": the next line is its title

    def new_piece(kind, number):
        piece = {"type": kind, "number": number, "title": "", "chapter": chapter, "section": section, "lines": []}
        pieces.append(piece)
        return piece

    for line in lines:
        # titles come on the line after "Article 6", "CHAPTER III", ...
        if waiting_for:
            if waiting_for == "chapter":
                chapter = f"{chapter} {line}"
            elif waiting_for == "section":
                section = f"{section} {line}"
            else:
                current["title"] = line.strip("'’ ")
            waiting_for = None
            continue

        if WHEREAS.match(line):
            zone = "recitals"
            continue
        if ADOPTED.match(line):
            zone = "body"
            current = None
            continue

        if zone == "recitals":
            match = RECITAL.match(line)
            if match:
                current = new_piece("recital", match.group(1))
                if match.group(2):
                    current["lines"].append(match.group(2))
            elif current:
                current["lines"].append(line)
            continue

        if m := CHAPTER.match(line):
            zone, chapter, section, waiting_for = "body", m.group(0), "", "chapter"
            continue
        if m := SECTION.match(line):
            zone, section, waiting_for = "body", m.group(0), "section"
            continue
        if m := ARTICLE.match(line):
            zone, waiting_for = "body", "article"
            current = new_piece("article", m.group(1))
            continue
        if m := ANNEX.match(line):
            zone, chapter, section, waiting_for = "body", "", "", "annex"
            current = new_piece("annex", m.group(1))
            continue

        if SIGNATURE.match(line) or FOOTNOTE.match(line):
            current = None  # signatures and footnotes are not part of any article
            continue

        if zone == "body" and current:
            current["lines"].append(line)

    for piece in pieces:
        piece["text"] = "\n".join(piece.pop("lines")).strip()
    return pieces


# ---------- Put it all together ----------
def parse_source(src: dict, html: str) -> list[dict]:
    pieces = split_lines(to_lines(clean_html(html)))
    records = []
    for p in pieces:
        if p["type"] not in src["parts"]:
            continue
        law_key = "ai_act" if src["law"] == "AI Act" else "gdpr"
        records.append({
            "id": f"{law_key}-{src['lang']}-{p['type']}-{p['number']}",
            "law": src["law"],
            "lang": src["lang"],
            "type": p["type"],
            "number": p["number"],
            "title": p["title"],
            "chapter": p["chapter"],
            "section": p["section"],
            "text": p["text"],
            "version": src["version"],
            "source_url": src["url"],
        })
    return records


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    all_records = []
    for src in SOURCES:
        path = RAW_DIR / f"{src['name']}.html"
        if not path.exists():
            print(f"[missing] {path.name}  -> run: python -m src.download_laws")
            continue
        records = parse_source(src, path.read_text(encoding="utf-8"))
        print(f"[ok] {path.name}: {len(records)} pieces")
        all_records += records

    out = PROCESSED_DIR / "laws.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"\nSaved {len(all_records)} pieces to {out}\n")

    # Check: do we have the numbers we expect?
    counts = Counter((r["law"], r["lang"], r["type"]) for r in all_records)
    print(f"{'Law':8} {'Lang':5} {'Type':8} {'Found':>6} {'Expected':>9}")
    for (law, kind), expected in EXPECTED.items():
        for lang in ("en", "de"):
            found = counts.get((law, lang, kind), 0)
            flag = "" if found == expected else "  <-- check"
            if kind == "article" and law == "AI Act" and found > expected:
                flag = "  (new articles added in 2026)"
            print(f"{law:8} {lang:5} {kind:8} {found:>6} {expected:>9}{flag}")

    empty = [r["id"] for r in all_records if not r["text"]]
    if empty:
        print(f"\nWarning: {len(empty)} pieces have no text, e.g. {empty[:5]}")


if __name__ == "__main__":
    main()
