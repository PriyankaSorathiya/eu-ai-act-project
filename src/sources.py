"""The official law texts we use, all from EUR-Lex.

Each source is one web page (one law, one language).
"parts" says which pieces we take from that page:
- The AI Act was changed in 2026. The "consolidated" version has the
  up-to-date articles and annexes, but it has NO recitals.
  So we take the recitals from the original 2024 text.
- The GDPR has not been changed, so we take everything from the original.
"""

EURLEX = "https://eur-lex.europa.eu/legal-content/{lang}/TXT/HTML/?uri=CELEX:{celex}"

# CELEX = EUR-Lex's ID number for a document
AI_ACT_CONSOLIDATED = "02024R1689-20260727"  # AI Act with all changes up to 27 July 2026
AI_ACT_ORIGINAL = "32024R1689"               # AI Act as published in 2024
GDPR = "32016R0679"                          # GDPR as published in 2016

SOURCES = []
for lang in ["EN", "DE"]:
    SOURCES += [
        {
            "name": f"ai_act_consolidated_{lang.lower()}",
            "law": "AI Act",
            "lang": lang.lower(),
            "url": EURLEX.format(lang=lang, celex=AI_ACT_CONSOLIDATED),
            "version": "consolidated 2026-07-27",
            "parts": ["article", "annex"],
        },
        {
            "name": f"ai_act_original_{lang.lower()}",
            "law": "AI Act",
            "lang": lang.lower(),
            "url": EURLEX.format(lang=lang, celex=AI_ACT_ORIGINAL),
            "version": "original 2024-07-12",
            "parts": ["recital"],
        },
        {
            "name": f"gdpr_{lang.lower()}",
            "law": "GDPR",
            "lang": lang.lower(),
            "url": EURLEX.format(lang=lang, celex=GDPR),
            "version": "original 2016-05-04",
            "parts": ["recital", "article"],
        },
    ]

# Numbers we expect, used to check the parser worked
EXPECTED = {
    ("AI Act", "recital"): 180,
    ("AI Act", "article"): 113,  # can be a bit more if the 2026 change added articles like "4a"
    ("AI Act", "annex"): 13,
    ("GDPR", "recital"): 173,
    ("GDPR", "article"): 99,
}
