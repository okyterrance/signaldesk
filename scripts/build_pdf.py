"""Render an HTML page in docs/ to PDF, and fail loudly if it runs long.

    python scripts/build_pdf.py                 # docs/writeup.html, must be 1 page
    python scripts/build_pdf.py deck/cue-card 1 # any page, any page budget

The Expo caps the write-up at one page, so "it looked fine in the browser"
is not verification -- browser width and A4 width reflow differently, and
that document was two pages five times while looking correct on screen.

Prints the exact overflow in pixels when it does not fit, so the next trim
is a measurement rather than a guess.
"""
from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright
from pypdf import PdfReader

ROOT = pathlib.Path(__file__).resolve().parents[1]
STEM = sys.argv[1] if len(sys.argv) > 1 else "writeup"
MAX_PAGES = int(sys.argv[2]) if len(sys.argv) > 2 else 1
SRC = ROOT / "docs" / f"{STEM}.html"
OUT = SRC.with_suffix(".pdf")
PREVIEW = SRC.with_name(f"{SRC.stem}_preview.png")

# A4 at 96 dpi, less the @page margins declared in the stylesheet.
PAGE_W, PAGE_H = 794, 1123
MARGIN_V, MARGIN_H = "10mm", "12mm"
CONTENT_W, CONTENT_H = PAGE_W - 2 * 45, PAGE_H - 2 * 38

# Playwright's bundled Chromium may not match a preinstalled one; pass an
# explicit path when the environment provides it.
CHROME_CANDIDATES = [
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
]


def main() -> int:
    if not SRC.exists():
        sys.exit(f"missing {SRC}")

    executable = next((p for p in CHROME_CANDIDATES if pathlib.Path(p).exists()), None)

    with sync_playwright() as p:
        browser = (
            p.chromium.launch(executable_path=executable)
            if executable
            else p.chromium.launch()
        )
        page = browser.new_page(viewport={"width": CONTENT_W, "height": CONTENT_H})
        page.goto(SRC.as_uri())

        height = page.evaluate("document.body.scrollHeight")
        page.pdf(
            path=str(OUT),
            format="A4",
            print_background=True,
            margin={
                "top": MARGIN_V, "bottom": MARGIN_V,
                "left": MARGIN_H, "right": MARGIN_H,
            },
        )
        page.screenshot(path=str(PREVIEW), full_page=True)
        browser.close()

    pages = len(PdfReader(str(OUT)).pages)
    print(f"content {height}px / {CONTENT_H * MAX_PAGES}px usable")
    print(f"{OUT.relative_to(ROOT)} — {pages} page(s), {OUT.stat().st_size / 1024:.0f} KB")

    if pages > MAX_PAGES:
        over = height - CONTENT_H * MAX_PAGES
        print(f"\nFAIL: overflows by {over}px. Trim, then re-run.")
        return 1
    print(f"OK — {pages} page(s), budget {MAX_PAGES}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
