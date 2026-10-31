(function () {
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const norm = (s) => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const hl = (text, q) => {
    const safe = esc(text);
    if (!q) return safe;
    const i = norm(text).indexOf(q);
    if (i < 0) return safe;
    return esc(text.slice(0, i)) + "<mark>" + esc(text.slice(i, i + q.length)) + "</mark>" + esc(text.slice(i + q.length));
  };
  const $ = (id) => document.getElementById(id);

  /* ---------- tarjetas de artículo ---------- */
  const card = (a, q) => `
    <article class="card">
      <div>
        <div class="meta"><span class="pill ${a.veredicto}">${esc(a.veredictoTexto)}</span><span class="tag">${esc(a.especialidad)}</span><span>${esc(a.revista)} · ${esc(a.fecha)}</span></div>
        <h3>${hl(a.titulo, q)}</h3>
        <p>${hl(a.resumen, q)}</p>
        <p style="margin-top:6px"><b style="color:var(--fg)">Aprendes:</b> ${hl(a.leccion, q)}</p>
      </div>
      <div class="acts">
        <a class="btn small primary" href="${a.pdf}" download>Descargar resumen (PDF)</a>
        <a class="btn small" href="https://doi.org/${a.doi}" target="_blank" rel="noopener">Artículo original</a>
      </div>
    </article>`;

  const ART = window.ARTICULOS || [];
  if ($("n-art")) $("n-art").textContent = ART.length;
  if ($("recientes")) $("recientes").innerHTML = ART.slice(0, 3).map((a) => card(a, "")).join("");

  if ($("lista")) {
    const state = { q: "", esp: "Todas", ver: "Todos" };
    const VER = { Todos: null, "Cambia la práctica": "si", "Refuerza o todavía no": "ref", "No cambia": "no" };
    const toks = (e) => String(e).split(" · ").map((x) => x.trim()).filter(Boolean);
    const cnt = {}; ART.forEach((a) => toks(a.especialidad).forEach((t) => (cnt[t] = (cnt[t] || 0) + 1)));
    const esps = ["Todas", ...Object.keys(cnt).sort((x, y) => x.localeCompare(y, "es"))];
    const chips = (el, items, key) => {
      el.innerHTML = items.map((x) => `<button class="chip" type="button" aria-pressed="${state[key] === x}">${esc(x)}</button>`).join("");
      el.querySelectorAll("button").forEach((b, i) => b.addEventListener("click", () => { state[key] = items[i]; render(); }));
    };
    const render = () => {
      chips($("f-esp"), esps, "esp");
      chips($("f-ver"), Object.keys(VER), "ver");
      const q = norm(state.q.trim());
      const out = ART.filter((a) =>
        (state.esp === "Todas" || toks(a.especialidad).includes(state.esp)) &&
        (!VER[state.ver] || a.veredicto === VER[state.ver]) &&
        (!q || norm([a.titulo, a.resumen, a.especialidad, a.revista, a.leccion, a.tipo].join(" ")).includes(q)));
      $("lista").innerHTML = out.map((a) => card(a, q)).join("");
      $("vacio").hidden = out.length > 0;
    };
    $("q").addEventListener("input", (e) => { state.q = e.target.value; render(); });
    render();
  }


  /* ---------- guías: búsqueda y filtro por especialidad ---------- */
  if ($("glista")) {
    const cards = [...$("glista").querySelectorAll("article.card")];
    const tk = (c) => { const t = c.querySelector(".tag"); return t ? t.textContent.split(" · ").map((x) => x.trim()) : []; };
    const all = [...new Set(cards.flatMap(tk))].sort((x, y) => x.localeCompare(y, "es"));
    const st = { q: "", esp: "Todas" };
    const opts = ["Todas", ...all];
    const draw = () => {
      $("g-esp").innerHTML = opts.map((x) => `<button class="chip" type="button" aria-pressed="${st.esp === x}">${esc(x)}</button>`).join("");
      $("g-esp").querySelectorAll("button").forEach((b, i) => b.addEventListener("click", () => { st.esp = opts[i]; draw(); }));
      const q = norm(st.q.trim()); let n = 0;
      cards.forEach((c) => { const ok = (st.esp === "Todas" || tk(c).includes(st.esp)) && (!q || norm(c.textContent).includes(q)); c.hidden = !ok; if (ok) n++; });
      $("gvacio").hidden = n > 0;
    };
    $("gq").addEventListener("input", (e) => { st.q = e.target.value; draw(); });
    draw();
  }
  /* ---------- fuentes ---------- */
  if ($("series") && window.FUENTES) {
    const { R, S } = window.FUENTES;
    if ($("n-ser")) $("n-ser").textContent = S.length;
    const render = (raw) => {
      const q = norm(raw.trim());
      let html = "", nav = "", shown = 0;
      for (const s of S) {
        const txt = norm([s.t, s.k, s.n || "", ...s.v.flat()].join(" "));
        const refs = s.r.filter(([id, uso]) => !q || txt.includes(q) || norm(R[id].c + " " + (uso || "")).includes(q));
        if (q && !refs.length) continue;
        shown++;
        nav += `<a class="chip" href="#${s.id}" style="text-decoration:none">${esc(s.t)}</a>`;
        html += `<section class="serie" id="${s.id}"><span class="kicker">${esc(s.k)}</span><h2>${hl(s.t, q)}</h2>
          <ul class="videos">${s.v.map(([a, b]) => `<li><b>${esc(a)}</b>${hl(b, q)}</li>`).join("")}</ul>
          ${s.n ? `<p class="muted" style="margin:0">${esc(s.n)}</p>` : ""}
          <ol class="refs">${refs.map(([id, uso]) => {
            const r = R[id]; const url = r.d ? "https://doi.org/" + r.d : r.u;
            return `<li><span class="cita">${url ? `<a href="${url}" target="_blank" rel="noopener">${hl(r.c, q)}</a>` : hl(r.c, q)}${r.d ? ` <span class="muted" style="font-size:13px">doi:${esc(r.d)}</span>` : ""}${uso ? `<span class="uso">Usado en: ${hl(uso, q)}</span>` : ""}</span></li>`;
          }).join("")}</ol></section>`;
      }
      $("series").innerHTML = html; $("idx").innerHTML = nav; $("vaciof").hidden = shown > 0;
    };
    $("qf").addEventListener("input", (e) => render(e.target.value));
    render("");
  }
})();
