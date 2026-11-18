"""Step 1a: download the law texts from EUR-Lex into data/raw.

Run:  python -m src.download_laws

Files that are already downloaded are skipped, so you can run it again safely.
"""
import re
import time

import requests

from src.config import RAW_DIR
from src.sources import SOURCES

# Look like a normal browser, so the website doesn't block us
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "en,de;q=0.9",
}


# "Article 1" or "Artikel 1". Newer pages put a special space (&nbsp;) between the words.
ARTICLE_1 = re.compile(r"Arti(?:cle|kel)(?:\s|&nbsp;|&#160;|\xa0)+1\b")


def looks_like_law(html: str) -> bool:
    """A real law page is big and contains 'Article 1' or 'Artikel 1'."""
    return len(html) > 100_000 and bool(ARTICLE_1.search(html))


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    problems = []

    for src in SOURCES:
        path = RAW_DIR / f"{src['name']}.html"
        if path.exists():
            print(f"[skip] {path.name} is already there")
            continue

        print(f"[download] {src['name']} ...")
        try:
            response = requests.get(src["url"], headers=HEADERS, timeout=60)
            response.raise_for_status()
        except requests.RequestException as error:
            problems.append((src, str(error)))
            continue

        html = response.text
        if not looks_like_law(html):
            # keep the strange page so we can look at what we got
            debug = RAW_DIR / "debug"
            debug.mkdir(exist_ok=True)
            (debug / f"{src['name']}.html").write_text(html, encoding="utf-8")
            problems.append((src, f"page does not look like the law text ({len(html) // 1000} KB, saved in data/raw/debug)"))
            continue

        path.write_text(html, encoding="utf-8")
        print(f"   saved {path.name} ({len(html) // 1000} KB)")
        time.sleep(2)  # be polite to the EUR-Lex server

    if problems:
        print("\nSome downloads did not work. Do this for each one:")
        print("  1. Open the link in your browser")
        print("  2. Press Ctrl+S, choose 'Webpage, HTML only'")
        print(f"  3. Save it in {RAW_DIR} with the file name shown\n")
        for src, reason in problems:
            print(f"  {src['name']}.html  <-  {src['url']}")
            print(f"     (reason: {reason})")
    else:
        print("\nAll laws downloaded.")


if __name__ == "__main__":
    main()
