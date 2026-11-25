/* Agente investigador: ventana de contexto llamada a llamada, memoria de notas y citas. En vivo o grabado. */
(() => {
const raiz = document.getElementById("investigador");
if (!raiz) return;
const EN = document.documentElement.lang === "en", T = (es, en) => EN ? en : es, base = raiz.dataset.base;
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const num = n => Number(n).toLocaleString(EN ? "en-GB" : "es-ES", {maximumFractionDigits: 1});
const dormir = ms => new Promise(r => setTimeout(r, ms));
const $ = id => document.getElementById(id);
const PARTES = {instrucciones: [T("instrucciones", "instructions"), "#7c8db5"], pregunta: [T("pregunta", "question"), "#38d0ff"],
  fragmento: [T("fragmento", "fragment"), "#ffc15e"], notas: [T("notas", "notes"), "#3ee6a0"], salida: [T("respuesta", "output"), "#c99bff"]};
let modelos = [], datos, sectores, sector, turno = 0, control = null;

function ventana(ctx, titulo) {
  const partes = {...ctx.partes, salida: ctx.salida}, usado = ctx.entrada + ctx.salida;
  $("a-barra").innerHTML = Object.entries(partes).map(([k, v]) => `<i style="width:${100 * v / ctx.num_ctx}%;background:${PARTES[k]?.[1]}" title="${PARTES[k]?.[0]}: ${v}"></i>`).join("");
  $("a-cifra").textContent = `${num(usado)} / ${num(ctx.num_ctx)} tokens · ${titulo}`;
  $("a-ley").innerHTML = Object.entries(partes).map(([k, v]) => `<span><i style="background:${PARTES[k]?.[1]}"></i>${PARTES[k]?.[0]} ${num(v)}</span>`).join("");
  const col = document.createElement("i"); col.style.height = `${Math.max(3, 100 * usado / ctx.num_ctx)}%`; col.title = `${titulo}: ${usado} tokens`; $("a-hist").appendChild(col);
}
function paso(titulo, cuerpo = "", clase = "", ms) {
  const d = document.createElement("div"); d.className = "paso " + clase;
  d.innerHTML = `<header><b>${titulo}</b><span>${ms == null ? "" : num(ms / 1000) + " s"}</span></header>${cuerpo}`;
  const c = $("a-pasos"); c.appendChild(d); c.scrollTop = c.scrollHeight; return d;
}
function pinta(ev) {
  if (ev.paso === "plan") { ventana(ev.ctx, T("planificar", "plan"));
    paso(T("1 · Plan de búsqueda", "1 · Search plan"), `<p>${ev.busquedas.map(b => `<code>${esc(b)}</code>`).join(" ")}</p>`, "", ev.ctx.ms); }
  else if (ev.paso === "buscar") paso(T("2 · Búsqueda híbrida", "2 · Hybrid search"),
    `<p>${num(ev.total)} ${T("fragmentos en la norma →", "fragments in the law →")} ${ev.resultados.map(r => `<code>${esc(r.ref)}</code>`).join(" ")}</p>`);
  else if (ev.paso === "ampliar") paso(T("Sin notas todavía: amplía la búsqueda", "No notes yet: widening the search"), "", "aviso");
  else if (ev.paso === "leer") { ventana(ev.ctx, `${T("leer", "read")} ${ev.ref}`);
    const ok = !!ev.nota;
    paso(`${ok ? "✓" : "·"} ${T("Lee", "Reads")} ${esc(ev.ref)} <small>${esc(ev.titulo)}</small>`,
      ok ? "" : `<p class="tenue">${ev.motivo === "cita no literal" ? T("descartado: la cita no era literal", "dropped: quote was not verbatim") : T("no contesta: se olvida", "not useful: forgotten")}</p>`, ok ? "ok" : "mini", ev.ctx.ms);
    if (ok) { const n = ev.nota, m = $("a-memoria"); m.querySelector(".vacio")?.remove();
      m.insertAdjacentHTML("beforeend", `<div class="nota"><b>[${m.querySelectorAll(".nota").length + 1}] ${esc(n.ref)}</b><blockquote>«${esc(n.cita)}»</blockquote><a href="${esc(n.url)}" target="_blank" rel="noopener">${T("ver en la fuente, pág.", "open source, p.")} ${n.pagina} ↗</a></div>`); } }
  else if (ev.paso === "final") { if (ev.ctx) ventana(ev.ctx, T("responder", "answer"));
    const sello = {respaldada: T("RESPALDADA POR NOTAS", "BACKED BY NOTES"), sin_evidencia: T("SIN EVIDENCIA: NO RESPONDE", "NO EVIDENCE: NO ANSWER"), rechazada: T("RECHAZADA", "REJECTED")}[ev.estado];
    paso(T("3 · Respuesta", "3 · Answer"), `<em class="sello">${sello}</em>${ev.estado === "respaldada" ? `<p class="grande">${esc(ev.respuesta)}</p><p>${ev.citas.map(c => `<a href="${esc(c.url)}" target="_blank" rel="noopener">[${c.n}] ${esc(c.corto)}, ${esc(c.ref)}, ${T("pág.", "p.")} ${c.pagina} ↗</a>`).join("<br>")}</p>` : ""}<p class="tenue">${num(ev.segundos)} s</p>`,
      ev.estado === "respaldada" ? "final" : "aviso"); }
  else if (ev.paso === "error") paso("Error", `<p>${esc(ev.texto)}</p>`, "mal");
}
function limpiar() { $("a-pasos").innerHTML = ""; $("a-hist").innerHTML = ""; $("a-barra").innerHTML = ""; $("a-ley").innerHTML = ""; $("a-cifra").textContent = "";
  $("a-memoria").innerHTML = `<p class="vacio">${T("Aquí se guardan solo las notas útiles.", "Only useful notes are kept here.")}</p>`; }
async function reproducir(g) {
  const mio = ++turno; control?.abort(); limpiar();
  paso(T("Pregunta", "Question"), `<p class="grande">${esc(g.q.pregunta)}</p>`);
  for (const ev of g.eventos) { await dormir(ev.paso === "leer" ? 800 : 1100); if (mio !== turno) return; pinta(ev); }
}
async function enVivo() {
  const pregunta = $("a-q").value.trim(); if (!pregunta) { $("a-q").focus(); return; }
  const mio = ++turno; control?.abort(); control = new AbortController(); limpiar();
  paso(T("Pregunta", "Question"), `<p class="grande">${esc(pregunta)}</p>`);
  const espera = document.createElement("div"); espera.className = "espera"; espera.textContent = T("trabajando…", "working…"); $("a-pasos").appendChild(espera);
  try {
    const r = await fetch("/api/investigar", {method: "POST", headers: {"Content-Type": "application/json"}, signal: control.signal,
      body: JSON.stringify({pregunta, sector, modelo: $("a-m").value, idioma: EN ? "en" : "es"})});
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const lector = r.body.getReader(), dec = new TextDecoder(); let resto = "";
    for (;;) { const {value, done} = await lector.read(); if (done || mio !== turno) break;
      resto += dec.decode(value, {stream: true}); const ls = resto.split("\n"); resto = ls.pop();
      for (const l of ls) if (l) { pinta(JSON.parse(l)); $("a-pasos").appendChild(espera); } }
  } catch (e) { if (e.name !== "AbortError" && mio === turno) pinta({paso: "error", texto: e.message}); }
  finally { espera.remove(); }
}
function elegir(s) {
  sector = s; raiz.querySelectorAll("[data-s]").forEach(b => b.setAttribute("aria-selected", b.dataset.s === s));
  const f = sectores.find(x => x.sector === s), ej = datos.filter(g => g.q.sector === s);
  $("a-fuente").innerHTML = `${esc(f.titulo)} · <a href="${esc(f.url)}" target="_blank" rel="noopener">PDF ${T("oficial", "official")} ↗</a>`;
  $("a-ej").innerHTML = ej.length ? ej.map(g => `<button data-g="${datos.indexOf(g)}">${esc(g.q.pregunta)} <small>▶ ${T("grabada", "recorded")}</small></button>`).join("")
    : `<p class="sub">${T("Sin ejecución grabada en este sector.", "No recorded run for this sector.")}</p>`;
  $("a-ej").querySelectorAll("[data-g]").forEach(b => b.onclick = () => reproducir(datos[b.dataset.g]));
}
async function iniciar() {
  try { const r = await fetch("/api/estado", {signal: AbortSignal.timeout(8000)}); if (r.ok) modelos = (await r.json()).modelos; } catch { modelos = []; }
  [datos, sectores] = await Promise.all(["agente/grabaciones.json", "agente/fuentes.json"].map(u => fetch(base + u).then(r => r.json())));
  const vivo = modelos.length > 0;
  const NOMBRES = {contratacion: T("Contratación pública", "Public procurement"), prevencion: T("Prevención de riesgos", "Occupational safety"), energia: T("Energía", "Energy"),
    ambiente: T("Ruido ambiental", "Environmental noise"), ia: T("Inteligencia artificial", "Artificial intelligence"), datos: T("Protección de datos", "Data protection"), edificacion: T("Edificación", "Building")};
  raiz.innerHTML = `<div class="estado ${vivo ? "on" : ""}"><span>${vivo ? T("EN VIVO · pregunta lo que quieras", "LIVE · ask anything") : T("MODO GRABACIÓN · ejecuciones reales", "RECORDED MODE · real runs")}</span>
  ${vivo ? `<label>${T("Modelo", "Model")} <select id="a-m">${modelos.map(m => `<option>${esc(m)}</option>`).join("")}</select></label>` : `<a href="#arrancar">${T("Cómo ejecutarlo en vivo", "How to run it live")} ↓</a>`}</div>
  <div class="pestanas">${sectores.map(s => `<button data-s="${s.sector}">${NOMBRES[s.sector]}</button>`).join("")}</div><p class="sub" id="a-fuente"></p>
  <div class="ejemplos fila-ej" id="a-ej"></div>
  ${vivo ? `<div class="fila"><input id="a-q" aria-label="${T("Tu pregunta", "Your question")}" placeholder="${T("Escribe tu pregunta sobre esta norma", "Ask about this law (in Spanish)")}"><button class="btn" id="a-go">▶ ${T("Investigar", "Investigate")}</button></div>` : ""}
  <div class="ctx"><header><b>${T("Ventana de contexto del modelo", "Model context window")}</b><span id="a-cifra"></span></header><div class="ventana" id="a-barra"></div><div class="leyenda" id="a-ley"></div><div class="historial" id="a-hist" aria-label="${T("Ocupación de cada llamada", "Usage per call")}"></div></div>
  <div class="mesa2"><div class="pista" id="a-pasos" aria-live="polite"></div><div class="memoria"><h3>${T("Memoria del agente", "Agent memory")}</h3><div id="a-memoria"></div></div></div>`;
  raiz.querySelectorAll("[data-s]").forEach(b => b.onclick = () => elegir(b.dataset.s));
  if (vivo) { $("a-go").onclick = enVivo; $("a-q").onkeydown = e => { if (e.key === "Enter") enVivo(); }; }
  const bien = g => g.eventos.at(-1).estado === "respaldada";
  const inicial = datos.find(g => g.q.sector === "datos" && bien(g)) || datos.find(bien) || datos[0];
  elegir(inicial.q.sector); reproducir(inicial);
}
iniciar();
})();
