"""Sestaví manuál (docs/manual/MANUAL-<lang>.md) do samostatné HTML stránky s obrázky ve formě data URI
a (volitelně) z ní vyrobí PDF přes Edge. Výstup: docs/manual/out/manual-<lang>.html a .pdf

    python tools/build_manual.py en [pdf]
"""

import base64
import io
import os
import re
import subprocess
import sys

import markdown
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, "docs", "manual")
OUT = os.path.join(MAN, "out")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

TITLES = {"en": "Spray Drone Manual", "cs": "Manuál servisního vleku"}

CSS = """
:root { --bg:#fbfbf8; --fg:#1d2420; --muted:#5b665f; --accent:#2f6b2a; --line:#d8ddd4; --card:#f0f3ec; --code:#e8ece3; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#171c18; --fg:#e4e9e1; --muted:#9aa69d; --accent:#8ccb5e; --line:#2f3832; --card:#202722; --code:#262e28; color-scheme: dark } }
:root[data-theme="dark"] { --bg:#171c18; --fg:#e4e9e1; --muted:#9aa69d; --accent:#8ccb5e; --line:#2f3832; --card:#202722; --code:#262e28; color-scheme: dark }
body { background:var(--bg); color:var(--fg); font:16px/1.6 "Inter", system-ui, "Segoe UI", sans-serif; margin:0;
  padding-block:24px; padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); }
main { max-width:860px; margin:0 auto; }
h1,h2,h3 { font-family:"Space Grotesk", "Inter", system-ui, sans-serif; text-wrap:balance; line-height:1.2; }
h1 { font-size:2.1rem; margin:0 0 .6rem; } h2 { font-size:1.5rem; margin:2.6rem 0 .8rem; padding-top:.4rem; border-top:2px solid var(--accent); }
h3 { font-size:1.15rem; margin:1.8rem 0 .5rem; }
a { color:var(--accent); } hr { border:0; border-top:1px solid var(--line); margin:2rem 0; }
img { max-width:100%; height:auto; border-radius:4px; display:block; margin:.9rem 0 .3rem; }
em { color:var(--muted); }
blockquote { margin:1rem 0; padding:.6rem 1rem; background:var(--card); border-left:4px solid var(--accent); }
blockquote p { margin:.3rem 0; }
code { background:var(--code); padding:.1em .35em; border-radius:3px; font-size:.9em; }
.tw { overflow-x:auto; margin:1rem 0; }
table { border-collapse:collapse; width:100%; font-size:.93rem; }
th,td { border:1px solid var(--line); padding:.4rem .6rem; text-align:left; vertical-align:top; }
th { background:var(--card); }
li { margin:.2rem 0; }
@media print {
  :root { --bg:#fff; --fg:#111; --card:#f3f3f0; --code:#eee; color-scheme: light }
  body { font-size:10.5pt; padding:0 } main { max-width:none }
  h2 { break-after:avoid; } img, table, blockquote { break-inside:avoid; } img { max-height:11cm; width:auto; }
}
"""


def embed(match, lang):
    alt, path = match.group(1), match.group(2)
    if path.startswith("http") or path.startswith("data:"):
        return match.group(0)
    full = os.path.join(MAN, path)
    im = Image.open(full).convert("RGB")
    if im.width > 1100:
        im = im.resize((1100, round(im.height * 1100 / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80, optimize=True)
    uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    return f"![{alt}]({uri})"


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    src = open(os.path.join(MAN, f"MANUAL-{lang}.md"), encoding="utf-8").read()
    src = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", lambda m: embed(m, lang), src)
    body = markdown.markdown(src, extensions=["tables", "sane_lists"])
    body = re.sub(r"(<table>.*?</table>)", r'<div class="tw">\1</div>', body, flags=re.S)
    html = (f'<title>{TITLES[lang]}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Space+Grotesk:wght@600&display=swap">\n'
            f"<style>{CSS}</style>\n<main>{body}</main>\n")
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"manual-{lang}.html")
    open(path, "w", encoding="utf-8").write(html)
    print(path, round(len(html) / 1e6, 2), "MB")
    if "pdf" in sys.argv:
        full = os.path.join(OUT, f"manual-{lang}-print.html")
        open(full, "w", encoding="utf-8").write(
            f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">' + html.replace("<main>", "</head><body><main>", 1) + "</body></html>")
        pdf = os.path.join(OUT, f"manual-{lang}.pdf")
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf}", "file:///" + full.replace("\\", "/")], check=True, timeout=180)
        print(pdf)


main()
