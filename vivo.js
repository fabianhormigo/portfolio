/* Consola de demos: en vivo contra el servidor local (Ollama) o reproduciendo ejecuciones reales grabadas. */
(() => {
const raiz = document.getElementById("vivo"), hero = document.getElementById("hero");
if (!raiz && !hero) return;
const EN = document.documentElement.lang === "en", T = (es, en) => EN ? en : es;
const base = (raiz || hero).dataset.base;
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const limpio = s => String(s).replace(/\\times/g, "×").replace(/\\text\{([^}]*)\}/g, "$1").replace(/\\[()\[\]]/g, "").replace(/\\,/g, " ").replace(/\^\{?2\}?/g, "²").replace(/ {2,}/g, " ");
const num = n => Number(n).toLocaleString(EN ? "en-GB" : "es-ES", {maximumFractionDigits: 1});
const dormir = ms => new Promise(r => setTimeout(r, ms));
const seg = ms => ms == null ? "" : ms < 1000 ? `${ms} ms` : `${num(ms / 1000)} s`;

/* ---------- pintor de eventos: sirve igual para vivo y grabado ---------- */
function pintor(caja) {
  let consola = null;
  caja.innerHTML = "";
  const paso = (titulo, cuerpo = "", ms, clase = "") => {
    const d = document.createElement("div"); d.className = "paso " + clase;
    d.innerHTML = `<header><b>${titulo}</b><span>${seg(ms)}</span></header>${cuerpo}`;
    caja.appendChild(d); caja.scrollTop = caja.scrollHeight; return d;
  };
  return ev => {
    switch (ev.paso) {
      case "filtro": paso(T("1 · Filtro por documento y versión", "1 · Filter by document and version"),
        `<p>${ev.total} ${T("fragmentos", "fragments")} → <strong>${ev.candidatos}</strong> ${T("candidatos", "candidates")} (${esc(ev.norma)} ${esc(ev.version)})</p>`, ev.ms); break;
      case "recuperar": paso(T("2 · Búsqueda híbrida", "2 · Hybrid search"), ev.fragmentos.map(f =>
        `<div class="frag"><code>${esc(f.id)}</code><p>${esc(f.texto)}</p><small><i>BM25 ${f.bm25 ? "#" + f.bm25 : "—"}</i>${f.vector ? `<i>${T("vector", "vector")} #${f.vector}</i>` : ""}</small></div>`).join(""), ev.ms); break;
      case "token": if (!consola) consola = paso(T("3 · El modelo escribe", "3 · The model writes"), "<pre></pre>").querySelector("pre");
        consola.textContent += ev.t; caja.scrollTop = caja.scrollHeight; break;
      case "generar": if (consola) consola.closest(".paso").querySelector("span").textContent = `${ev.modelo || ""} · ${seg(ev.ms)}`;
        else paso(T("El modelo redacta", "The model writes"), `<p>${esc(ev.modelo)}</p>`, ev.ms); break;
      case "validar": {
        const s = ev.salida, ok = ev.estado === "valida";
        const rot = {valida: T("CITA VERIFICADA", "QUOTE VERIFIED"), sin_evidencia: T("SIN EVIDENCIA: NO RESPONDE", "NO EVIDENCE: NO ANSWER"), rechazada: T("RECHAZADA POR LA VALIDACIÓN", "REJECTED BY VALIDATION")}[ev.estado];
        const d = paso(T("4 · Validación", "4 · Validation"), `<em class="sello">${rot}</em>${ok ? `<p class="grande">${esc(limpio(s.respuesta))}</p><blockquote>«${esc(s.cita)}» <code>${esc(s.id)}</code></blockquote><button class="btn">${T("Aprobar respuesta", "Approve answer")}</button>` : ""}`, ev.ms, ok ? "ok" : ev.estado === "rechazada" ? "mal" : "aviso");
        const b = d.querySelector("button"); if (b) b.onclick = () => { b.textContent = T("Aprobada por una persona ✓", "Approved by a person ✓"); b.disabled = true; };
        break; }
      case "herramientas": paso(T("Servidor MCP conectado", "MCP server connected"), `<p class="chips">${ev.lista.map(n => `<code>${esc(n)}</code>`).join(" ")}</p>`, ev.ms); break;
      case "pensar": paso(ev.pide ? T("El modelo decide usar una herramienta", "The model decides to use a tool") : T("El modelo redacta la respuesta", "The model writes the answer"), `<p>${esc(ev.modelo)}</p>`, ev.ms); break;
      case "llamada": paso(`→ ${esc(ev.nombre)}`, `<pre>${esc(JSON.stringify(ev.args, null, 1))}</pre>`, null, "llamada"); break;
      case "resultado": paso(T("← Resultado de la herramienta (código, no el modelo)", "← Tool result (code, not the model)"), `<pre>${esc(ev.texto)}</pre>`, ev.ms, ev.error ? "mal" : "ok"); break;
      case "calcular": paso(T("El código calcula las cifras", "Code computes the figures"), `<p><strong>${num(ev.licitaciones)}</strong> ${T("licitaciones agregadas en", "tenders aggregated into")} ${ev.sectores} ${T("sectores", "sectors")}</p>`, ev.ms); break;
      case "respuesta": {
        let h = ev.texto && ev.texto !== "(sin texto)" ? `<p class="grande">${esc(limpio(ev.texto))}</p>` : "";
        if (ev.accion) h += `<p class="sub">${T("Acción validada", "Validated action")}</p><pre>${esc(JSON.stringify(ev.accion))}</pre>`;
        const g = ev.grafico;
        if (g) { const max = Math.max(...g.datos.map(p => p[1])) || 1, vol = g.medida === "volumen_eur";
          h += `<p class="sub">${esc(g.titulo)}</p>` + g.datos.map(([n, y]) => `<div class="barra"><span>${esc(n)}</span><span><i style="width:${100 * y / max}%"></i></span><b>${vol ? num(y / 1e9) + (EN ? " bn €" : " mil M€") : num(y)}</b></div>`).join(""); }
        if (ev.sinRespaldo) h = (ev.sinRespaldo.length
          ? `<em class="sello alerta">${T("CIFRAS SIN RESPALDO", "UNSUPPORTED FIGURES")}: ${esc(ev.sinRespaldo.join(" · "))}</em>`
          : `<em class="sello">${T("CIFRAS COMPROBADAS", "FIGURES CHECKED")}</em>`) + h;
        paso(T("Respuesta", "Answer"), h || "<p>—</p>", null, ev.sinRespaldo?.length ? "aviso" : "final"); break; }
      case "error": paso("Error", `<p>${esc(ev.texto)}</p>`, null, "mal"); break;
    }
  };
}

async function reproducir(eventos, caja, vigente) {
  const p = pintor(caja);
  for (const ev of eventos) {
    await dormir(ev.paso === "token" ? 45 : Math.min(300 + (ev.ms || 0) / 4, 1100));
    if (!vigente()) return;
    p(ev);
  }
}

/* ---------- portada: reproducción automática ---------- */
if (hero) fetch(base + "vivo/grabaciones.json").then(r => r.json()).then(async g => {
  const lista = [g.rag[0], g.agente[1], g.rag[2]];
  hero.innerHTML = `<div class="barra-c"><i></i><i></i><i></i><span></span></div><div class="pista"></div>`;
  const rot = hero.querySelector("span"), pista = hero.querySelector(".pista");
  for (let i = 0; ; i = (i + 1) % lista.length) {
    rot.textContent = `${T("ejecución real grabada", "recorded real run")} · ${lista[i].q.pregunta.slice(0, 54)}…`;
    await reproducir(lista[i].eventos, pista, () => true);
    await dormir(4500);
  }
});
if (!raiz) return;

/* ---------- consola completa ---------- */
const PEST = {rag: T("Pregunta a un documento", "Ask a document"), agente: T("Agente con herramientas", "Agent with tools"), datos: T("Pregunta a los datos", "Ask the data")};
let modelos = [], grab, pest = "rag", turno = 0;
const enNavegador = () => !modelos.length && window.Navegador.listo() && pest !== "agente";
const ejecutable = () => modelos.length > 0 || enNavegador();

async function iniciar() {
  try { const r = await fetch("/api/estado", {signal: AbortSignal.timeout(8000)}); if (r.ok) modelos = (await r.json()).modelos; } catch { modelos = []; }
  grab = await (await fetch(base + "vivo/grabaciones.json")).json();
  const vivo = modelos.length > 0;
  raiz.innerHTML = `<div class="estado ${vivo ? "on" : ""}"><span>${vivo ? T("EN VIVO · modelos en este equipo", "LIVE · models on this machine") : T("MODO GRABACIÓN · ejecuciones reales", "RECORDED MODE · real runs")}</span>
  ${vivo ? `<label>${T("Modelo", "Model")} <select id="v-m">${modelos.map(m => `<option>${esc(m)}</option>`).join("")}</select></label>` : `<a href="#arrancar">${T("Con tus propios modelos de Ollama", "With your own Ollama models")} ↓</a>`}</div>
  ${vivo ? "" : `<div class="carga" id="v-carga"><div><b>${T("Ejecútalo tú, dentro de tu navegador", "Run it yourself, inside your browser")}</b>
  <small>${T("El modelo se descarga de huggingface.co una vez y queda en la caché. Tus textos no salen de tu equipo. Los modelos pequeños se equivocan más.", "The model is downloaded once from huggingface.co and cached. Your text never leaves your machine. Small models make more mistakes.")}</small></div>
  <select id="v-nm" aria-label="${T("Modelo", "Model")}">${window.Navegador.MODELOS.map((m, i) => `<option value="${i}">${m.nombre.replace("-Instruct", "")} · ~${m.mb} MB</option>`).join("")}</select>
  <button class="btn" id="v-cargar">${T("Descargar y activar", "Download and start")}</button><progress id="v-prog" max="1" value="0" hidden></progress><small id="v-info" role="status"></small></div>`}
  <div class="pestanas" role="tablist">${Object.entries(PEST).map(([k, v]) => `<button role="tab" data-p="${k}">${v}</button>`).join("")}</div>
  <div class="mesa"><div class="entrada" id="v-e"></div><div class="pista" id="v-s" aria-live="polite"></div></div>`;
  raiz.querySelectorAll("[data-p]").forEach(b => b.onclick = () => { pest = b.dataset.p; formulario(); });
  const cargar = document.getElementById("v-cargar");
  if (cargar && !navigator.gpu) { cargar.disabled = true; document.getElementById("v-info").textContent = T("Tu navegador no tiene WebGPU. Prueba con Chrome o Edge actualizados en un ordenador.", "Your browser lacks WebGPU. Try an up-to-date desktop Chrome or Edge."); }
  if (cargar) cargar.onclick = activar;
  formulario();
}

async function activar() {
  const b = document.getElementById("v-cargar"), sel = document.getElementById("v-nm"), barra = document.getElementById("v-prog"), info = document.getElementById("v-info");
  b.disabled = sel.disabled = true; barra.hidden = false; info.textContent = T("Preparando…", "Preparing…");
  try {
    await window.Navegador.cargar(+sel.value, (p, texto) => { barra.value = p; info.textContent = texto; });
    barra.hidden = true; info.textContent = T("Modelo listo en tu navegador.", "Model ready in your browser."); b.textContent = T("Activo ✓", "Active ✓");
    const e = raiz.querySelector(".estado"); e.classList.add("on");
    e.querySelector("span").textContent = `${T("EN TU NAVEGADOR", "IN YOUR BROWSER")} · ${window.Navegador.nombre()}`;
    formulario();
  } catch (err) {
    b.disabled = sel.disabled = false; barra.hidden = true;
    info.textContent = err.message === "WebGPU" ? T("No se pudo usar la gráfica (WebGPU).", "Could not use the GPU (WebGPU).") : `${T("No se pudo cargar el modelo", "Could not load the model")}: ${err.message}`;
  }
}

function formulario() {
  turno++;
  const vivo = ejecutable(), e = document.getElementById("v-e"), s = document.getElementById("v-s");
  raiz.querySelectorAll("[data-p]").forEach(b => b.setAttribute("aria-selected", b.dataset.p === pest));
  s.innerHTML = `<p class="vacio">${T("Elige un ejemplo o escribe tu pregunta. Aquí verás cada paso.", "Pick an example or type a question. Every step shows up here.")}</p>`;
  const rag = pest === "rag";
  e.innerHTML = `<p class="sub">${T("Ejemplos", "Examples (recorded in Spanish)")}</p><div class="ejemplos">${grab[pest].map((g, i) => `<button data-i="${i}">${esc(g.q.pregunta)}${g.q.version ? ` <small>${esc(g.q.norma)} ${esc(g.q.version)}</small>` : ""}</button>`).join("")}</div>
  ${vivo ? `${rag ? `<label class="sub">${T("Fuente", "Source")}<select id="v-f"><option value="corpus">${T("Corpus de ejemplo (ficticio)", "Example corpus (fictional, Spanish)")}</option><option value="doc">${T("Mi documento", "My document")}</option></select></label>
  <div class="fila" id="v-c"><select id="v-n" aria-label="${T("Norma", "Standard")}"><option>NT-HORMIGON</option><option>NT-SENSOR</option></select><select id="v-v" aria-label="${T("Versión", "Version")}"><option>2025</option><option>2022</option></select></div>
  <textarea id="v-d" rows="7" hidden placeholder="${T("Pega aquí tu texto, una idea por línea.", "Paste your text, one statement per line.")}"></textarea>` : ""}
  <label class="sub">${T("Tu pregunta", "Your question")}<textarea id="v-q" rows="3"></textarea></label><button class="btn" id="v-go">▶ ${T("Ejecutar", "Run")}</button>`
  : `<p class="sub">${pest === "agente" && window.Navegador.listo() ? T("El agente usa el servidor MCP en Python: solo corre en local con Ollama. Aquí ves ejecuciones grabadas.", "The agent uses the Python MCP server: it runs only locally with Ollama. Recorded runs shown here.") : T("Para escribir tus preguntas, activa el modelo en tu navegador o arranca el servidor local.", "To type your own questions, start the in-browser model or the local server.")}</p>`}`;
  e.querySelectorAll("[data-i]").forEach(b => b.onclick = () => {
    const g = grab[pest][b.dataset.i];
    if (!vivo) return reproducirGrabado(g);
    document.getElementById("v-q").value = g.q.pregunta;
    if (rag) { fuente("corpus"); document.getElementById("v-f").value = "corpus"; document.getElementById("v-n").value = g.q.norma; document.getElementById("v-v").value = g.q.version; }
    enVivo();
  });
  if (!vivo) return reproducirGrabado(grab[pest][0]);   // sin servidor: arranca sola la primera ejecución
  if (rag) document.getElementById("v-f").onchange = ev => fuente(ev.target.value);
  document.getElementById("v-go").onclick = enVivo;
}
function fuente(v) { document.getElementById("v-c").hidden = v === "doc"; document.getElementById("v-d").hidden = v !== "doc"; }
function reproducirGrabado(g) { const mio = ++turno; reproducir(g.eventos, document.getElementById("v-s"), () => mio === turno); }

let control = null;
async function enVivo() {
  const q = {pregunta: document.getElementById("v-q").value.trim(), modelo: document.getElementById("v-m")?.value, idioma: EN ? "en" : "es"};
  const s = document.getElementById("v-s");
  if (!q.pregunta) { s.innerHTML = `<p class="vacio">${T("Escribe una pregunta.", "Type a question.")}</p>`; return; }
  if (pest === "rag") {
    if (document.getElementById("v-f").value === "doc") {
      q.documento = document.getElementById("v-d").value;
      if (q.documento.trim().length < 16) { s.innerHTML = `<p class="vacio">${T("Pega primero tu documento.", "Paste your document first.")}</p>`; return; }
    } else { q.norma = document.getElementById("v-n").value; q.version = document.getElementById("v-v").value; }
  }
  control?.abort(); control = new AbortController();
  const mio = ++turno, p = pintor(s), espera = document.createElement("div");
  espera.className = "espera"; const t0 = Date.now(), reloj = setInterval(() => espera.textContent = `${T("trabajando", "working")}… ${Math.round((Date.now() - t0) / 1000)} s`, 500);
  espera.textContent = T("trabajando…", "working…"); s.appendChild(espera);
  try {
    if (enNavegador()) {
      await window.Navegador[pest](q, ev => { if (mio === turno) { p(ev); s.appendChild(espera); } }, () => mio === turno, base);
      return;
    }
    const r = await fetch("/api/" + pest, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(q), signal: control.signal});
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const lector = r.body.getReader(), dec = new TextDecoder(); let resto = "";
    for (;;) {
      const {value, done} = await lector.read(); if (done || mio !== turno) break;
      resto += dec.decode(value, {stream: true}); const lineas = resto.split("\n"); resto = lineas.pop();
      for (const l of lineas) if (l) { p(JSON.parse(l)); s.appendChild(espera); }
    }
  } catch (err) { if (err.name !== "AbortError" && mio === turno) p({paso: "error", texto: err.message}); }
  finally { clearInterval(reloj); espera.remove(); }
}
iniciar();
})();
