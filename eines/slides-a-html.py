#!/usr/bin/env python3
"""Exporta un deck de Slides de claude.ai (fitxers project/) a una presentació HTML per a GitHub Pages.

Ús: slides-a-html.py <carpeta project> <mapa.tsv> <carpeta de sortida> [--titol T] [--bessones a=b,c=d] [--sense-numero id,id]

- <mapa.tsv>: «id del blob<TAB>fitxer local», un per línia; els fitxers es copien a <sortida>/media/.
- --bessones: parelles «quieta=amb-vídeo». A Slides, el vídeo arrenca en una diapo bessona;
  aquí es fonen en una sola diapo i el vídeo (o l'àudio) arrenca amb el clic endavant.
- --sense-numero: diapos que no compten per a la línia de progrés ni per al número (p. ex. una pantalla negra).
- Les notes del presentador van a notes.html (noindex); les línies amb ⁇ no s'hi publiquen.
"""
import html as H, json, os, re, shutil, sys

a = sys.argv[1:]
proj, mapa, out = a[0], a[1], a[2]
opt = lambda k, d='': a[a.index(k) + 1] if k in a else d
titol = opt('--titol', 'Presentació')
bessones = dict(p.split('=') for p in opt('--bessones').split(',') if p)
sense_num = set(x for x in opt('--sense-numero').split(',') if x)

deck = json.load(open(f'{proj}/deck.json'))
css = open(f'{proj}/deck.css').read()
fonts = [f['href'] for f in deck.get('faces', {}).values() if f.get('href')]
order = deck['order']
starts = {v['start']: k for k, v in deck['sections'].items()}

os.makedirs(f'{out}/media', exist_ok=True)
media = {}
for linia in open(mapa):
    if not linia.strip():
        continue
    bid, fitxer = linia.rstrip('\n').split('\t')
    ext = os.path.splitext(fitxer)[1].lower()
    media[bid] = f'media/{bid}{ext}'
    shutil.copyfile(fitxer, f'{out}/{media[bid]}')


def llegeix(sid):
    return open(f'{proj}/slides/{sid}.html').read().strip()


def blobs(s):
    def r(m):
        if m.group(1) not in media:
            sys.exit(f'falta el blob {m.group(1)}')
        return media[m.group(1)]
    return re.sub(r'/_blob/([0-9a-f]{32})', r, s)


# Parts (seccions), línia de progrés i número: les bessones i les diapos sense número no compten
part, p = {}, -1
for sid in order:
    if sid in starts:
        p += 1
    part[sid] = max(p, 0)
amb_video = set(bessones.values())
vis = [s for s in order if s not in amb_video and s not in sense_num]
num = {s: i + 1 for i, s in enumerate(vis)}
N, W = len(vis), 1664
inici = {}
for s in vis:
    inici.setdefault(part[s], vis.index(s))


def capcalera(sid, attrs, mapa_vell):
    pos, pt = vis.index(sid), part[sid]
    segs = ''.join('<div class="sg%s%s"></div>' % (' fet' if j <= pos else '', ' part' if part[v] == pt else '')
                   for j, v in enumerate(vis))
    # el mapa (noms i revelació) es conserva tal com és a Slides; només es recalculen les posicions
    def pos_nom(m):
        q = int(m.group(2))
        return m.group(1) + 'left:%dpx' % round(inici.get(q, 0) / N * W)
    mapa_nou = re.sub(r'(<p class="mp[^"]*"[^>]*style=")left:\d+px(?=">(\d+)\.)', pos_nom, mapa_vell)
    return '<div class="cap"%s>\n<div class="prog">%s</div>\n%s\n</div>' % (attrs, segs, mapa_nou)


seccions, notes = [], []
for sid in order:
    if sid in amb_video:
        continue
    s = llegeix(sid)
    if sid in bessones:
        # fon la bessona: els elements amb vídeo de la bessona substitueixen (o s'afegeixen a) la diapo quieta
        b = llegeix(bessones[sid])
        for v in re.findall(r'<img[^>]*data-video="[^"]*"[^>]*>', b):
            still = re.search(r'src="([^"]+)"', v).group(1)
            v2 = v.replace('<img ', '<img data-pas="1" ', 1)
            antic = re.search(r'<img[^>]*src="%s"[^>]*>' % re.escape(still), s)
            if antic and 'data-video' not in antic.group(0):
                s = s.replace(antic.group(0), v2, 1)
            else:
                s = s.replace('<p class="num">', v2 + '\n<p class="num">', 1)
    m = re.search(r'<div class="cap"([^>]*)>\s*<div class="prog">.*?</div>\s*(<div class="mapa">.*?</div>)\s*</div>', s, re.S)
    if m and sid in num:
        s = s[:m.start()] + capcalera(sid, m.group(1), m.group(2)) + s[m.end():]
    if sid in num:
        s = re.sub(r'(<p class="num">.*?<span>)\d+(</span></p>)', r'\g<1>%02d\g<2>' % num[sid], s)
    nt = re.search(r'<aside>(.*?)</aside>', s, re.S)
    s = re.sub(r'\s*<aside>.*?</aside>', '', s, flags=re.S)
    s = blobs(s)
    seccions.append(s)
    text = H.unescape(nt.group(1)) if nt else ''
    linies = [l for l in text.split('\n') if '⁇' not in l and 'bessona' not in l and 'idèntica' not in l
              and 'continuació de la' not in l]
    titols = re.findall(r'<(?:h1|h2|h3|p) class="(?:mega|enunciat|titol|sub)[^"]*"[^>]*>(.*?)</', s, re.S)
    nom = re.sub('<[^>]+>', ' ', titols[0]).replace('&nbsp;', ' ').strip() if titols else ''
    notes.append((len(seccions), re.sub(r'\s+', ' ', H.unescape(nom)), '\n'.join(linies).strip()))

css_extra = '''
/* — Reproductor — */
html, body { margin: 0; height: 100%; background: #0c0c0c; overflow: hidden; }
.escena { position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; }
.deck { position: relative; width: 1920px; height: 1080px; flex: none; transform-origin: 50% 50%; }
.deck > section { position: absolute; inset: 0; box-sizing: border-box; width: 1920px; height: 1080px; overflow: hidden; }
.deck > section:not(.actiu):not(.sortint) { display: none !important; }
.deck > section.sortint { z-index: 0; }
.deck > section.actiu { z-index: 1; animation: entra-diapo 380ms ease both; }
@keyframes entra-diapo { from { opacity: 0; } }
.deck p, .deck h1, .deck h2, .deck h3 { margin: 0; }
.deck * { box-sizing: border-box; }
.cap { position: relative; z-index: 2000000; }
.num, .peu { z-index: 2000000; }
.retall { overflow: hidden; }
.retall > img { width: 100%; height: 100%; object-fit: cover; }
.imgw { animation: puja 1100ms cubic-bezier(.16,1,.3,1) both; animation-delay: calc(260ms + var(--i, 0) * 110ms); }
video { display: block; }
/* Comptador (count-up de Slides): el número es pinta amb un comptador CSS que anima --n de 0 al valor final */
.compta { counter-reset: n var(--n); }
.compta::before { content: counter(n); }
/* Navegador (com el de les presentacions Marp de la UPF): surt en moure el punter i s'amaga als 2 s, amb el cursor */
.osc { position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%); z-index: 10; display: flex; align-items: center; gap: 2px; padding: 6px; border-radius: 12px; background: rgba(20, 20, 19, .78); -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px); color: #f4f4f1; font: 500 15px/1 'IBM Plex Mono', ui-monospace, monospace; transition: opacity .3s ease; }
.osc button { display: grid; place-items: center; width: 44px; height: 44px; border: 0; border-radius: 8px; background: transparent; color: inherit; cursor: pointer; touch-action: manipulation; }
.osc button:hover { background: rgba(255, 255, 255, .14); }
.osc button:focus-visible { outline: 2px solid #f4f4f1; outline-offset: -2px; }
.osc button:disabled { opacity: .35; cursor: default; background: transparent; }
.osc svg { width: 22px; height: 22px; }
.osc .pag { min-width: 96px; padding: 0 8px; text-align: center; font-variant-numeric: tabular-nums; }
body.inactiu .osc { opacity: 0; pointer-events: none; }
body.inactiu { cursor: none; }
.graella { position: fixed; inset: 0; z-index: 20; overflow-y: auto; overscroll-behavior: contain; padding: 32px; background: #0c0c0c; display: none; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px 20px; align-content: start; }
.graella.oberta { display: grid; }
body.amb-graella { cursor: auto; }
body.amb-graella .osc { opacity: 0; pointer-events: none; }
.graella button { padding: 0; border: 0; background: none; color: #a8a8a1; font: 500 13px/1.4 'IBM Plex Mono', ui-monospace, monospace; text-align: left; cursor: pointer; }
.graella .mini { position: relative; aspect-ratio: 16 / 9; overflow: hidden; border-radius: 4px; outline: 1px solid #2a2a28; margin-bottom: 6px; }
.graella button:hover .mini, .graella button:focus-visible .mini { outline: 2px solid #f4f4f1; }
.graella button.ara .mini { outline: 3px solid #f4f4f1; }
.graella button.ara { color: #f4f4f1; }
.graella .mini > section { position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; box-sizing: border-box; overflow: hidden; transform-origin: 0 0; pointer-events: none; }
.graella .mini * { animation: none !important; transition: none !important; }
.graella .mini .fragment { opacity: 1 !important; }
@media (prefers-reduced-motion: reduce) { .osc { transition: none; } }
@media (prefers-reduced-motion: reduce) { .deck * { animation-duration: 1ms !important; animation-iteration-count: 1 !important; } }
'''

js = r'''
(() => {
  const deck = document.querySelector('.deck');
  const S = [...deck.children];
  // vídeos: l'<img data-video> de Slides passa a <video>
  deck.querySelectorAll('img[data-video]').forEach(img => {
    const v = document.createElement('video');
    for (const at of img.attributes) if (!['src', 'alt', 'data-video'].includes(at.name)) v.setAttribute(at.name, at.value);
    v.src = img.dataset.video; v.poster = img.getAttribute('src'); v.playsInline = true; v.preload = 'auto';
    v.loop = true; v.muted = img.dataset.videoSound !== 'on';
    v.setAttribute('aria-label', img.alt || '');
    v.style.objectFit = img.style.objectFit || 'contain';
    img.replaceWith(v);
  });
  // retalls de Slides (data-crop = zoom, x %, y %): un contenidor que retalla i la imatge ampliada a dins
  deck.querySelectorAll('img[data-crop]').forEach(img => {
    const [z, x, y] = img.dataset.crop.split(' ');
    const w = document.createElement('div');
    w.setAttribute('style', img.getAttribute('style') || '');
    w.className = 'retall ' + (img.className || 'imgw');
    const st = w.style.getPropertyValue('--i'); if (st) w.style.setProperty('--i', st);
    img.removeAttribute('style'); img.className = 'fix';
    img.style.objectPosition = `${x} ${y}`; img.style.transformOrigin = `${x} ${y}`; img.style.scale = z;
    img.replaceWith(w); w.appendChild(img);
  });
  // comptadors: el text («571») passa a ser el valor final de --n, i l'animació de Slides el fa pujar des de 0
  deck.querySelectorAll('.compta').forEach(el => {
    const v = parseInt(el.textContent.replace(/[^0-9]/g, ''), 10);
    if (Number.isFinite(v)) { el.style.setProperty('--n', v); el.setAttribute('aria-label', el.textContent.trim()); el.textContent = ''; }
  });
  // Paul Bunyans i altres bucles: la imatge que torna a sortir es posa al davant
  let z = 10;
  deck.querySelectorAll('.bun').forEach(img => {
    const up = () => { img.parentElement.style.zIndex = ++z; };
    img.addEventListener('animationstart', up); img.addEventListener('animationiteration', up);
  });
  // passos de cada diapo: fragments (per data-fragment-index, després per ordre) i vídeos que arrenquen amb un clic
  function passos(s) {
    const fr = [...s.querySelectorAll('.fragment')];
    const grups = new Map(); let seg = 1000;
    fr.forEach(f => { const k = f.dataset.fragmentIndex !== undefined ? +f.dataset.fragmentIndex : seg++; if (!grups.has(k)) grups.set(k, []); grups.get(k).push(f); });
    const p = [...grups.keys()].sort((a, b) => a - b).map(k => ({ fr: grups.get(k) }));
    // vídeo o àudio: un clic l'engega, el següent l'atura (per poder-se parar a explicar) i el següent passa de diapo
    s.querySelectorAll('video[data-pas]').forEach(v => { p.push({ video: v }); p.push({ pausa: v }); });
    return p;
  }
  let i = 0, pas = 0, P = [], actualitza = () => {};
  function atura(s) { s.querySelectorAll('video').forEach(v => { v.pause(); try { v.currentTime = 0; } catch (e) {} }); }
  function mostra(n, alFinal) {
    n = Math.max(0, Math.min(S.length - 1, n));
    // en canviar de diapo, s'aturen tots els vídeos i àudios del deck, no només els de la diapo que deixem
    deck.querySelectorAll('video').forEach(v => { v.pause(); try { v.currentTime = 0; } catch (e) {} });
    S.forEach(s => s.classList.remove('sortint'));
    S.forEach(s => { if (s.classList.contains('actiu')) { atura(s); s.classList.remove('actiu'); if (S.indexOf(s) !== n) { s.classList.add('sortint'); setTimeout(() => s.classList.remove('sortint'), 420); } } });
    i = n; const s = S[i];
    s.querySelectorAll('.fragment').forEach(f => f.classList.remove('visible'));
    void s.offsetWidth; s.classList.add('actiu');
    P = passos(s); pas = 0;
    s.querySelectorAll('video:not([data-pas])').forEach(v => { v.currentTime = 0; v.play().catch(() => {}); });
    if (alFinal) while (pas < P.length && !P[pas].video && !P[pas].pausa) fes();
    history.replaceState(null, '', '#' + (i + 1));
    actualitza();
  }
  function fes() {
    const q = P[pas++];
    if (q.fr) q.fr.forEach(f => f.classList.add('visible'));
    if (q.video) { q.video.currentTime = 0; q.video.play().catch(() => {}); }
    if (q.pausa) q.pausa.pause();
    actualitza();
  }
  const endavant = () => { if (pas < P.length) fes(); else if (i < S.length - 1) mostra(i + 1); };
  const enrere = () => { if (i > 0) mostra(i - 1, true); };
  addEventListener('keydown', e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (['ArrowRight', 'ArrowDown', 'PageDown', ' ', 'Enter', 'n', 'N'].includes(e.key)) { e.preventDefault(); endavant(); }
    else if (['ArrowLeft', 'ArrowUp', 'PageUp', 'Backspace', 'p', 'P'].includes(e.key)) { e.preventDefault(); enrere(); }
    else if (e.key === 'Home') mostra(0);
    else if (e.key === 'End') mostra(S.length - 1);
    else if (e.key === 'f' || e.key === 'F') { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen(); }
  });
  // navegador
  const ic = d => `<svg viewBox="0 0 256 256" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="16" stroke-linecap="round" stroke-linejoin="round" d="${d}"/></svg>`;
  const osc = document.createElement('nav');
  osc.className = 'osc'; osc.setAttribute('aria-label', 'Navegació de la presentació');
  osc.innerHTML = `<button type="button" data-a="ant" aria-label="Anterior">${ic('M160 208 80 128l80-80')}</button>`
    + `<span class="pag" aria-live="polite"></span>`
    + `<button type="button" data-a="seg" aria-label="Següent">${ic('m96 48 80 80-80 80')}</button>`
    + `<button type="button" data-a="gr" aria-label="Totes les diapos (O)">${ic('M48 48h64v64H48zM144 48h64v64h-64zM48 144h64v64H48zM144 144h64v64h-64z')}</button>`
    + `<button type="button" data-a="pc" aria-label="Pantalla completa (F)">${ic('M168 48h40v40M88 208H48v-40M208 168v40h-40M48 88V48h40')}</button>`;
  document.body.appendChild(osc);
  const pag = osc.querySelector('.pag');
  const pantalla = () => { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen(); };
  osc.addEventListener('click', e => {
    e.stopPropagation();
    const b = e.target.closest('button'); if (!b) return;
    b.blur();
    if (b.dataset.a === 'ant') enrere(); else if (b.dataset.a === 'seg') endavant(); else if (b.dataset.a === 'gr') graella(); else pantalla();
  });
  actualitza = () => {
    pag.textContent = `${i + 1} / ${S.length}`;
    osc.querySelector('[data-a="ant"]').disabled = i === 0;
    osc.querySelector('[data-a="seg"]').disabled = i === S.length - 1 && pas >= P.length;
  };
  // graella: miniatures estàtiques de totes les diapos (sense animacions, amb els clics fets)
  const gr = document.createElement('div');
  gr.className = 'graella'; gr.setAttribute('role', 'dialog'); gr.setAttribute('aria-label', 'Totes les diapos');
  document.body.appendChild(gr);
  let feta = false;
  function omple() {
    S.forEach((s, k) => {
      const b = document.createElement('button'); b.type = 'button'; b.dataset.k = k;
      const m = document.createElement('div'); m.className = 'mini';
      const c = s.cloneNode(true); c.classList.remove('actiu', 'sortint'); c.removeAttribute('id');
      c.querySelectorAll('video').forEach(v => { const im = document.createElement('img'); im.src = v.poster; im.setAttribute('style', v.getAttribute('style') || ''); im.className = v.className; v.replaceWith(im); });
      m.appendChild(c); b.appendChild(m); b.append(String(k + 1)); gr.appendChild(b);
    });
    feta = true;
  }
  function escalaMinis() { gr.querySelectorAll('.mini').forEach(m => { m.firstChild.style.transform = `scale(${m.clientWidth / 1920})`; }); }
  function graella(obre) {
    const o = obre ?? !gr.classList.contains('oberta');
    if (o) {
      if (!feta) omple();
      gr.classList.add('oberta'); document.body.classList.add('amb-graella'); escalaMinis();
      gr.querySelectorAll('button').forEach(b => b.classList.toggle('ara', +b.dataset.k === i));
      const ara = gr.querySelector('button.ara'); if (ara) { ara.scrollIntoView({ block: 'center' }); ara.focus(); }
    } else { gr.classList.remove('oberta'); document.body.classList.remove('amb-graella'); }
  }
  gr.addEventListener('click', e => { e.stopPropagation(); const b = e.target.closest('button'); if (b) { graella(false); mostra(+b.dataset.k); } });
  addEventListener('resize', () => { if (gr.classList.contains('oberta')) escalaMinis(); });
  addEventListener('keydown', e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === 'o' || e.key === 'O') { e.preventDefault(); e.stopImmediatePropagation(); graella(); }
    else if (e.key === 'Escape' && gr.classList.contains('oberta')) { e.preventDefault(); e.stopImmediatePropagation(); graella(false); }
    else if (gr.classList.contains('oberta')) { e.stopImmediatePropagation(); }
  }, true);
  let tem;
  const actiu = () => { document.body.classList.remove('inactiu'); clearTimeout(tem); tem = setTimeout(() => document.body.classList.add('inactiu'), 2000); };
  ['mousemove', 'mousedown', 'touchend'].forEach(t => document.addEventListener(t, actiu, { passive: true }));
  setTimeout(actiu, 0);
  addEventListener('click', e => { if (!e.target.closest('a, .osc')) endavant(); });
  let x0 = null;
  addEventListener('touchstart', e => { x0 = e.touches[0].clientX; }, { passive: true });
  addEventListener('touchend', e => { if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0; if (Math.abs(dx) > 40) (dx < 0 ? endavant : enrere)(); x0 = null; });
  function escala() { const k = Math.min(innerWidth / 1920, innerHeight / 1080); deck.style.transform = `scale(${k})`; }
  addEventListener('resize', escala); escala();
  document.addEventListener('visibilitychange', () => { if (document.hidden) deck.querySelectorAll('video').forEach(v => v.pause()); });
  const h = parseInt(location.hash.slice(1), 10);
  mostra(Number.isFinite(h) ? h - 1 : 0);
})();
'''

pagina = f'''<!doctype html>
<html lang="ca">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{H.escape(titol)}</title>
{''.join(f'<link rel="stylesheet" href="{H.escape(u)}">' + chr(10) for u in fonts)}<style>
{css}
{css_extra}
</style>
</head>
<body>
<div class="escena"><div class="deck">
{chr(10).join(seccions)}
</div></div>
<script>{js}</script>
</body>
</html>
'''
open(f'{out}/index.html', 'w').write(pagina)

cos = '\n'.join(
    f'<section id="{n}"><h2><a href="index.html#{n}">{n}</a> <span>{H.escape(nom)}</span></h2>'
    + ''.join(f'<p>{H.escape(l.strip())}</p>' for l in t.split('\n') if l.strip())
    + ('' if t.strip() else '<p class="buida">Sense notes.</p>') + '</section>'
    for n, nom, t in notes)
open(f'{out}/notes.html', 'w').write(f'''<!doctype html>
<html lang="ca">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Notes · {H.escape(titol)}</title>
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
section p {{ margin: 0 0 6px; white-space: pre-wrap; }}
.buida {{ color: var(--gris); }}
</style>
</head>
<body>
<h1>{H.escape(titol)}</h1>
<p class="peu">Notes del presentador · {len(notes)} diapos · el número obre la diapo · <a href="index.html">presentació</a></p>
{cos}
</body>
</html>
''')
print(len(seccions), 'diapos;', N, 'amb número;', len(media), 'fitxers')
