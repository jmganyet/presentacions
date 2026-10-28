// Vista de presentador per als decks exportats de Slides (claude.ai).
// Es llegeix data-speaker-notes de cada <section class="deck-slide">.
// N obre una finestra amb la nota de la diapo actual, la següent i el temps;
// les fletxes i l'espai, premuts a la finestra de notes, també fan avançar el deck.
// Si el navegador bloqueja la finestra, les notes surten en un plafó a peu de pàgina (N l'amaga).
(function () {
  var slides = Array.prototype.slice.call(document.querySelectorAll("section.deck-slide"));
  if (!slides.length) return;
  var win = null, panel = null, start = null, last = -1;

  function current() {
    // En mode escenari el reproductor marca amb data-off totes les diapos menys la visible;
    // en mode desplaçament no n'amaga cap i mana la que hi ha a dalt.
    var on = slides.filter(function (s) { return !s.hasAttribute("data-off"); });
    if (on.length === 1) return slides.indexOf(on[0]);
    var best = 0, bestDist = Infinity;
    for (var i = 0; i < slides.length; i++) {
      var d = Math.abs(slides[i].getBoundingClientRect().top);
      if (d < bestDist) { bestDist = d; best = i; }
    }
    return best;
  }
  function note(i) { return slides[i] ? slides[i].getAttribute("data-speaker-notes") || "" : ""; }
  function label(i) { return slides[i] ? slides[i].getAttribute("data-label") || "" : ""; }
  function lines(doc, el, text) {
    el.textContent = "";
    text.split(" · ").forEach(function (t) {
      var p = doc.createElement("p"); p.textContent = t; el.appendChild(p);
    });
  }
  function clock() {
    var s = Math.floor((Date.now() - start) / 1000);
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  }

  function render(force) {
    var i = current();
    if (win && win.closed) win = null;
    if (win) {
      var d = win.document;
      d.getElementById("pos").textContent = (i + 1) + " / " + slides.length;
      d.getElementById("clock").textContent = clock();
      if (force || i !== last) {
        lines(d, d.getElementById("note"), note(i) || "(sense nota)");
        var nx = i + 1 < slides.length ? (i + 2) + " · " + label(i + 1) + (note(i + 1) ? " — " + note(i + 1).split(" · ")[0] : "") : "Final";
        d.getElementById("next").textContent = "Següent: " + nx;
      }
    }
    if (panel && (force || i !== last)) lines(document, panel, (i + 1) + " / " + slides.length + " · " + (note(i) || "(sense nota)"));
    last = i;
  }

  function openWindow() {
    win = window.open("", "notes-presentador", "width=720,height=560");
    if (!win) return false;
    var d = win.document;
    d.open();
    d.write('<!doctype html><html lang="ca"><head><meta charset="utf-8"><title>Notes · ' + document.title + '</title></head>' +
      '<body style="margin:0;padding:24px 28px;background:#1b1a19;color:#f0efec;font:22px/1.45 system-ui,sans-serif">' +
      '<div style="display:flex;justify-content:space-between;color:#9c9a95;font-size:18px"><span id="pos"></span><span id="clock"></span></div>' +
      '<div id="note" style="margin:12px 0 20px"></div>' +
      '<div id="next" style="color:#9c9a95;font-size:17px;border-top:1px solid #3a3836;padding-top:12px"></div>' +
      '</body></html>');
    d.close();
    d.addEventListener("keydown", function (e) {
      if (e.key === "n" || e.key === "N") { win.close(); win = null; return; }
      if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "PageUp", "PageDown", " ", "Home", "End"].indexOf(e.key) < 0) return;
      e.preventDefault();
      window.dispatchEvent(new KeyboardEvent("keydown", { key: e.key, shiftKey: e.shiftKey }));
    });
    return true;
  }

  function togglePanel() {
    if (panel) { panel.remove(); panel = null; return; }
    panel = document.createElement("div");
    panel.setAttribute("style", "position:fixed;left:0;right:0;bottom:0;z-index:2147483647;max-height:40vh;overflow:auto;" +
      "padding:12px 20px;background:rgba(27,26,25,.94);color:#f0efec;font:18px/1.4 system-ui,sans-serif");
    document.body.appendChild(panel);
    render(true);
  }

  window.addEventListener("keydown", function (e) {
    if (e.metaKey || e.ctrlKey || e.altKey || (e.key !== "n" && e.key !== "N")) return;
    if (start === null) start = Date.now();
    if (panel) { togglePanel(); return; }
    if (win && !win.closed) { win.focus(); return; }
    if (openWindow()) render(true); else togglePanel();
  });
  setInterval(function () { if (win || panel) render(false); }, 250);
})();
