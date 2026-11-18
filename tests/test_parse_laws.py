"""Tests for the law parser, using small fake pages that copy EUR-Lex's layout.

Run:  pytest
"""
from src.parse_laws import clean_html, parse_source, split_lines, to_lines

# Like the original Official Journal pages (GDPR, AI Act 2024)
OJ_PAGE = """
<html><body>
<p class="oj-normal">Acting in accordance with the ordinary legislative procedure <a href="#ntr3-X">(3)</a>,</p>
<p class="oj-normal">Whereas:</p>
<table><tr><td><p>(1)</p></td><td><p>The protection of personal data is a fundamental right.</p></td></tr></table>
<table><tr><td><p>(2)</p></td><td><p>Second recital text.</p></td></tr></table>
<p class="oj-normal">HAVE ADOPTED THIS REGULATION:</p>
<p class="oj-ti-section-1">CHAPTER I</p>
<p class="oj-ti-section-2">GENERAL PROVISIONS</p>
<p class="oj-ti-art">Article 1</p>
<p class="oj-sti-art">Subject matter</p>
<p class="oj-normal">1. This Regulation lays down rules.</p>
<table><tr><td><p>(a)</p></td><td><p>first point;</p></td></tr></table>
<p class="ti-section-1">Section 2</p>
<p class="ti-section-2">Rights</p>
<p class="oj-ti-art">Article 2</p>
<p class="oj-sti-art">Scope</p>
<p class="oj-normal">This Regulation applies to everyone.</p>
<p class="oj-normal">Done at Brussels, 13 June 2024.</p>
<p class="oj-doc-ti">ANNEX I</p>
<p class="oj-doc-ti">List of legislation</p>
<p class="oj-normal">1. Machinery.</p>
<p class="oj-note" id="ntc3-X">(3) OJ C 123, 1.1.2024, p. 1.</p>
</body></html>
"""

# Like the consolidated (updated) pages: no recitals, change markers, grids
CONSOLIDATED_PAGE = """
<html><body>
<p>REGULATION (EU) 2024/1689</p>
<p class="title-division-1">CHAPTER I</p>
<p class="title-division-2">GENERAL PROVISIONS</p>
<p class="title-article-norm">Artikel 1</p>
<p class="stitle-article-norm">Gegenstand'</p>
<p class="norm">▼M1 Zweck dieser Verordnung ist es.</p>
<div class="grid-container"><div class="grid-list-column-1"><span>a)</span></div><div class="grid-list-column-2"><p class="norm">erster Punkt</p></div></div>
<p class="title-article-norm">Artikel 4a</p>
<p class="stitle-article-norm">Neu</p>
<p class="norm">▼M1</p>
<p class="norm">Eingefügter Text.</p>
<p class="title-article-norm">Artikel 5</p>
<p class="stitle-article-norm">Absätze</p>
<div class="norm"><span class="no-parag">1.  </span><div class="norm inline-element">Erster Absatz.</div></div>
<div class="norm"><span class="no-parag">2.  </span><div class="norm inline-element">Zweiter Absatz.</div></div>
</body></html>
"""

GDPR_SRC = {"law": "GDPR", "lang": "en", "url": "x", "version": "v", "parts": ["recital", "article"]}


def test_recitals_and_articles():
    records = parse_source(GDPR_SRC, OJ_PAGE)
    ids = [r["id"] for r in records]
    assert ids == ["gdpr-en-recital-1", "gdpr-en-recital-2", "gdpr-en-article-1", "gdpr-en-article-2"]

    recital = records[0]
    assert recital["text"] == "The protection of personal data is a fundamental right."

    article = records[2]
    assert article["title"] == "Subject matter"
    assert article["chapter"] == "CHAPTER I GENERAL PROVISIONS"
    assert "(a) first point;" in article["text"]


def test_footnotes_and_signature_removed():
    pieces = split_lines(to_lines(clean_html(OJ_PAGE)))
    all_text = " ".join(p["text"] for p in pieces)
    assert "OJ C 123" not in all_text          # footnote text removed
    assert "procedure (3)" not in all_text     # footnote number removed
    assert "Done at Brussels" not in all_text  # signature not inside Article 2


def test_section_and_annex():
    pieces = split_lines(to_lines(clean_html(OJ_PAGE)))
    article2 = next(p for p in pieces if p["type"] == "article" and p["number"] == "2")
    assert article2["section"] == "Section 2 Rights"
    annex = next(p for p in pieces if p["type"] == "annex")
    assert annex["number"] == "I"
    assert annex["title"] == "List of legislation"
    assert annex["chapter"] == ""


def test_only_wanted_parts_are_kept():
    src = dict(GDPR_SRC, parts=["recital"])
    records = parse_source(src, OJ_PAGE)
    assert {r["type"] for r in records} == {"recital"}


def test_consolidated_german_page():
    src = {"law": "AI Act", "lang": "de", "url": "x", "version": "v", "parts": ["article", "annex"]}
    records = parse_source(src, CONSOLIDATED_PAGE)
    assert [r["number"] for r in records] == ["1", "4a", "5"]
    first = records[0]
    assert first["title"] == "Gegenstand"           # stray apostrophe removed
    assert "▼" not in first["text"]                 # change markers removed
    assert "a) erster Punkt" in first["text"]       # grid points kept
    assert records[1]["text"] == "Eingefügter Text."
    assert records[2]["text"] == "1. Erster Absatz.\n2. Zweiter Absatz."  # paragraphs in <div class="norm">
