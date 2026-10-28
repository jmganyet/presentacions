"""Genera <deck>/notes.html amb les notes del presentador d'un deck de Slides (claude.ai).
Ús: python3 eines/pagina-notes.py per-que-juguem"""
import html, re, sys
from html.parser import HTMLParser

deck = sys.argv[1].rstrip("/")
src = open(f"{deck}/index.html", encoding="utf-8").read()

class Notes(HTMLParser):
    def __init__(self):
        super().__init__(); self.slides = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "section" and "deck-slide" in (a.get("class") or "").split():
            self.slides.append((a.get("data-label") or "", a.get("data-speaker-notes") or ""))

p = Notes(); p.feed(src)
title = html.unescape(re.search(r"<title>(.*?)</title>", src, re.S).group(1).strip())

items = []
for i, (label, note) in enumerate(p.slides, 1):
    lines = "".join(f"<p>{html.escape(t)}</p>" for t in note.split(" · ") if t.strip()) or '<p class="buida">(sense nota)</p>'
    items.append(f'<section id="{i}"><h2><a href="index.html#{i}">{i}</a> <span>{html.escape(label)}</span></h2>{lines}</section>')

out = f"""<!doctype html>
<html lang="ca">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Notes · {html.escape(title)}</title>
<style>
:root {{ --fons: #fff; --text: #231F20; --gris: #6d6e71; --filet: #e2e1dd; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fons: #1b1a19; --text: #f0efec; --gris: #9c9a95; --filet: #3a3836; }} }}
body {{ margin: 0 auto; max-width: 44rem; padding: 24px 16px 64px; background: var(--fons); color: var(--text); font: 18px/1.5 system-ui, sans-serif; }}
h1 {{ font-size: 26px; margin: 0 0 4px; }}
.peu {{ color: var(--gris); font-size: 14px; margin: 0 0 24px; }}
section {{ border-top: 1px solid var(--filet); padding: 14px 0 6px; scroll-margin-top: 8px; }}
h2 {{ font-size: 14px; font-weight: 600; margin: 0 0 6px; color: var(--gris); }}
h2 a {{ color: inherit; }}
h2 span {{ margin-left: 6px; }}
section p {{ margin: 0 0 6px; }}
.buida {{ color: var(--gris); }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p class="peu">Notes del presentador · {len(p.slides)} diapos · el número obre la diapo · <a href="index.html">presentació</a></p>
{chr(10).join(items)}
</body>
</html>
"""
open(f"{deck}/notes.html", "w", encoding="utf-8").write(out)
print(f"{deck}/notes.html: {len(p.slides)} diapos, {sum(1 for _, n in p.slides if n)} amb nota, {len(out)//1024} KB")
