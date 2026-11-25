/* Portafolio: una pestaña por producto. Todas las cifras se leen de los ficheros del repositorio. */
(() => {
const EN = document.documentElement.lang === "en", T = (es, en) => EN ? en : es;
const base = document.body.dataset.base, REPO = "https://github.com/fabianhormigo/portfolio";
const {C, num, esc} = G, $ = id => document.getElementById(id);
const cache = {};
const leer = u => cache[u] ||= fetch(base + u).then(r => { if (!r.ok) throw new Error(`${u}: HTTP ${r.status}`); return r.json(); });
const cargarScript = u => cache[u] ||= new Promise((ok, mal) => { const s = document.createElement("script"); s.src = base + u; s.onload = ok; s.onerror = () => mal(new Error(u)); document.body.appendChild(s); });

const kpis = l => `<div class="kpis">${l.map(([v, t]) => `<div><b>${v}</b><span>${t}</span></div>`).join("")}</div>`;
const tarjeta = (t, sub, id, extra = "") => `<div class="tarjeta"><h3>${t}</h3><p class="sub">${sub}</p><div id="${id}" class="grafico"></div>${extra}</div>`;
const cabeza = ({etiqueta, titulo, pregunta, fichas}) => `<header class="cabeza"><span class="etq">${etiqueta}</span><h2>${titulo}</h2><p class="pregunta">${pregunta}</p><div class="fichas">${fichas.map(([a, b]) => `<span>${a}: <b>${b}</b></span>`).join("")}</div></header>`;
const pie = (conclusion, enlaces) => `<p class="conclusion">${conclusion}</p><p class="enlaces">${enlaces.map(([t, u]) => `<a href="${u}">${t} →</a>`).join("")}</p>`;

/* aciertos tras la revisión manual */
async function evaluacion() {
  const [ev, rev] = await Promise.all([leer("agente/resultados/evaluacion.json"), leer("agente/resultados/revision.json")]);
  const fuera = rev.huella === ev.huella ? rev.descartados : [];
  const ok = (c, m) => ev.resumen[c][m].correctas - fuera.filter(x => x.modo === m && ev.detalle.some(f => f.n === x.n && f.modo === m && f.conjunto === c)).length;
  return {ev, ok};
}
const METODOS = () => [["simple", T("RAG simple", "Simple RAG"), C.naranja], ["volcado", T("Volcado", "Stuffing"), C.agua], ["agente", T("Agente", "Agent"), C.azul]];

/* ───────── inicio ───────── */
async function inicio(s) {
  const [{ev}, datos, pruebas] = await Promise.all([evaluacion(), leer("vivo/datos_agregados.json"), leer("docs/pruebas.json")]);
  const lic = datos.hechos_tot.filter(h => h.anio !== "?").reduce((a, h) => a + h.n, 0);
  const prods = [
    ["agente", T("Agente investigador de normativa", "Regulation research agent"), T("Responde sobre 7 normas oficiales citando artículo y página.", "Answers over 7 official laws, citing article and page."), T("Abrir el agente", "Open the agent"), "m-agente"],
    ["licitaciones", T("Panel de contratación pública", "Public procurement dashboard"), T(`${num(lic)} licitaciones: dónde está el dinero y dónde se compite poco.`, `${num(lic)} tenders: where the money is and where competition is low.`), T("Explorar el panel", "Explore the dashboard"), "m-lic"],
    ["datos", T("Revisor de ficheros de sensores", "Sensor file checker"), T("Sube un CSV y obtén huecos, congelados, picos y el informe.", "Upload a CSV and get gaps, frozen values, spikes and a report."), T("Probar con un fichero", "Try with a file"), "m-datos"],
    ["herramientas", T("Herramientas para agentes (MCP)", "Tools for agents (MCP)"), T("El modelo consulta y calcula con código probado.", "The model looks up and computes with tested code."), T("Ver una sesión", "See a session"), "m-mcp"]];
  s.innerHTML = `<div class="portada"><h1>${T("Productos de IA y datos que <em>se pueden usar y comprobar</em>.", "AI and data products you can <em>use and verify</em>.")}</h1>
    <p>${T("Soy físico. Construyo agentes que citan sus fuentes, paneles sobre datos reales y automatizaciones con pruebas. Todo lo de aquí funciona en tu navegador.", "I'm a physicist. I build agents that cite sources, dashboards on real data and tested automations. Everything here runs in your browser.")}</p>
    ${kpis([[num(ev.fragmentos), T("fragmentos de normas indexados", "indexed law fragments")], [num(lic), T("licitaciones en el panel", "tenders in the dashboard")], [num(pruebas.total), T("tests automáticos", "automated tests")], ["ES · EN", T("documentado en dos idiomas", "documented in two languages")]])}</div>
    <div class="productos">${prods.map(([id, t, d, boton, g], i) => `<a class="producto${i ? "" : " principal"}" href="#${id}"><div class="mini" id="${g}"></div><div><h3>${t}</h3><p>${d}</p><span>${boton} →</span></div></a>`).join("")}</div>`;
  const r = (await leer("agente/grabaciones.json")).find(g => g.q.sector === "datos");
  const ll = r.eventos.filter(e => e.ctx);
  G.columnas($("m-agente"), {cats: ll.map((_, i) => String(i + 1)), series: [{nombre: T("tokens por llamada", "tokens per call"), color: C.azul, valores: ll.map(e => e.ctx.entrada + e.ctx.salida)}],
    refs: [{v: ev.resumen.desarrollo.volcado.max_entrada, nombre: T("meterlo todo de golpe", "stuffing everything")}], alto: 190});
  const anos = porAnio(datos.hechos_tot);
  G.columnas($("m-lic"), {cats: anos.map(a => a[0]), series: [{nombre: T("miles de millones €", "billion €"), color: C.azul, valores: anos.map(a => a[1].vol / 1e9)}], alto: 150});
  const m = revisar(EJEMPLO()); linea($("m-datos"), m, 110);
  $("m-mcp").innerHTML = flujo(true);
  s.querySelectorAll(".mini details,.mini .leyenda").forEach(n => n.remove());
}

/* ───────── agente ───────── */
async function agente(s) {
  const [{ev, ok}, grab] = await Promise.all([evaluacion(), leer("agente/grabaciones.json")]);
  const r = ev.resumen, pico = Math.max(r.desarrollo.agente.max_entrada, r.reservado.agente.max_entrada);
  s.innerHTML = cabeza({etiqueta: T("Producto 1 · agente con ingeniería de contexto", "Product 1 · context-engineered agent"), titulo: T("Agente investigador de normativa", "Regulation research agent"),
    pregunta: T("Un modelo pequeño no puede leer una ley entera. ¿Cómo responde con pruebas sin llenar su memoria?", "A small model cannot read a whole law. How can it answer with evidence without filling its memory?"),
    fichas: [[T("Modelo", "Model"), ev.modelo], [T("Documentos", "Documents"), T("7 normas oficiales", "7 official laws")], [T("Corre", "Runs"), T("en local con Ollama", "locally with Ollama")]]}) +
    kpis([[num(pico), T(`tokens como máximo por llamada, de ${num(ev.num_ctx)}`, `peak tokens per call, out of ${num(ev.num_ctx)}`)], [`${ok("desarrollo", "agente")}/${r.desarrollo.agente.con_respuesta}`, T(`aciertos en desarrollo (RAG simple ${ok("desarrollo", "simple")})`, `correct on development (simple RAG ${ok("desarrollo", "simple")})`)],
      [`${ok("reservado", "agente")}/${r.reservado.agente.con_respuesta}`, T(`en preguntas reservadas (RAG simple ${ok("reservado", "simple")}, volcado ${ok("reservado", "volcado")})`, `on held-out questions (simple RAG ${ok("reservado", "simple")}, stuffing ${ok("reservado", "volcado")})`)],
      [`${r.reservado.agente.negativas + r.desarrollo.agente.negativas}/${r.reservado.agente.sin_respuesta + r.desarrollo.agente.sin_respuesta}`, T("se niega cuando la norma no lo dice", "refuses when the law is silent")]]) +
    `<div class="tarjeta"><h3>${T("Pruébalo", "Try it")}</h3><p class="sub">${T("Elige una norma y mira cada paso: qué lee, qué guarda y la cita con su página.", "Pick a law (questions in Spanish) and watch each step: what it reads, what it keeps and the quote with its page.")}</p><div id="investigador" data-base="${base}"></div></div>
    <div class="dos">${tarjeta(T("Qué ocupa la memoria del modelo", "What fills the model's memory"), T("Tokens en cada llamada de una pregunta real sobre protección de datos", "Tokens per call on a real data-protection question"), "g-ventana")}
    ${tarjeta(T("Memoria máxima por método", "Peak memory by method"), T("Tokens de entrada en la llamada más grande de la evaluación", "Input tokens in the largest call of the evaluation"), "g-pico")}</div>` +
    pie(T(`<b>Qué se consigue:</b> citas verificadas con artículo y página usando una fracción de la ventana. <b>Qué no:</b> en preguntas nuevas no acierta más que las alternativas; el límite está en la búsqueda.`, `<b>What it achieves:</b> verified article-and-page quotes using a fraction of the window. <b>What it doesn't:</b> on new questions it is not more accurate than the alternatives; search is the limit.`),
      [[T("Cómo está medido", "How it is measured"), "#calidad"], [T("Código y documentación", "Code and documentation"), `${REPO}/tree/main/agente`]]);
  const g = grab.find(x => x.q.sector === "datos"), ll = g.eventos.filter(e => e.ctx);
  const nombre = e => e.paso === "plan" ? "plan" : e.paso === "final" ? T("responde", "answer") : e.ref;
  const parte = (e, k) => k.reduce((a, x) => a + (e.ctx.partes[x] || 0), 0);
  G.columnas($("g-ventana"), {apiladas: true, cats: ll.map(nombre), unidad: "tokens", series: [
    {nombre: T("instrucciones y pregunta", "instructions and question"), color: C.agua, valores: ll.map(e => parte(e, ["instrucciones", "pregunta"]))},
    {nombre: T("material leído", "material read"), color: C.azul, valores: ll.map(e => parte(e, ["fragmento", "notas"]))},
    {nombre: T("respuesta", "output"), color: C.naranja, valores: ll.map(e => e.ctx.salida)}]});
  G.barras($("g-pico"), {items: [[T("Volcado de documentos", "Document stuffing"), r.reservado.volcado.max_entrada], [T("RAG simple", "Simple RAG"), r.reservado.simple.max_entrada], [T("Agente con notas", "Agent with notes"), r.reservado.agente.max_entrada], [T("Límite del modelo", "Model limit"), ev.num_ctx]], destaca: T("Agente con notas", "Agent with notes"), titulo: "tokens"});
  await cargarScript("agente.js");
}

/* ───────── licitaciones ───────── */
const SECTOR = {"Construccion/Obra civil": ["Obra civil", "Civil works"], "TIC/Software/Telecom": ["Tecnología", "ICT"], "Maquinaria/Equipo": ["Maquinaria y equipo", "Machinery"], "Ingenieria/Tecnico": ["Ingeniería", "Engineering"],
  "Residuos/Agua/Ambiental": ["Agua y medio ambiente", "Water & environment"], "Energia": ["Energía", "Energy"], "Laboratorio": ["Laboratorio", "Laboratory"], "Quimica": ["Química", "Chemicals"], "Mineria/Metales": ["Minería y metales", "Mining & metals"], "Maquinaria pesada": ["Maquinaria pesada", "Heavy machinery"], "I+D": ["I+D", "R&D"]};
const sector = k => SECTOR[k]?.[EN ? 1 : 0] || k;
function sumar(filas, clave) {
  const o = {};
  for (const h of filas) { const a = o[h[clave]] ||= {n: 0, vol: 0, os: 0, oc: 0, u: 0, bs: 0, bc: 0};
    a.n += h.n; a.vol += h.vol; a.os += h.of_sum; a.oc += h.of_cnt; a.u += h.unico; a.bs += h.baja_sum; a.bc += h.baja_cnt; }
  return o;
}
const porAnio = filas => Object.entries(sumar(filas.filter(h => h.anio >= "2018" && h.anio <= "2026"), "anio")).sort();
async function licitaciones(s) {
  const d = await leer("vivo/datos_agregados.json");
  const regiones = Object.entries(sumar(d.hechos_tot, "region")).filter(([r]) => r && r !== "(sin región)" && r !== "null").sort((a, b) => b[1].n - a[1].n).slice(0, 52).map(x => x[0]);
  const anos = ["2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"];
  const op = (l, v) => l.map(x => `<option${x === v ? " selected" : ""}>${esc(x)}</option>`).join("");
  s.innerHTML = cabeza({etiqueta: T("Producto 2 · datos públicos", "Product 2 · public data"), titulo: T("Panel de contratación pública", "Public procurement dashboard"),
    pregunta: T("¿Dónde está el dinero de la contratación pública y en qué sectores se presenta menos gente?", "Where is public procurement money, and which sectors attract the fewest bidders?"),
    fichas: [[T("Fuente", "Source"), "PLACSP"], [T("Ámbito", "Scope"), T("industria y obra civil, sin contratos menores", "industry and civil works, minor contracts excluded")], [T("Datos", "Data"), T("agregados, sin datos personales", "aggregated, no personal data")]]}) +
    `<div class="filtros"><label>${T("Territorio", "Region")}<select id="f-r"><option value="">${T("Toda España", "All Spain")}</option>${op(regiones)}</select></label><label>${T("Desde", "From")}<select id="f-a">${op(anos, "2018")}</select></label><label>${T("Hasta", "To")}<select id="f-b">${op(anos, "2026")}</select></label></div>
    <div id="l-kpis"></div><div class="dos">${tarjeta(T("Importe licitado por año", "Tendered amount per year"), T("Miles de millones de euros. 2026, año incompleto", "Billion euros. 2026 is partial"), "g-anio")}${tarjeta(T("Licitaciones por año", "Tenders per year"), T("Número de expedientes publicados", "Published procedures"), "g-num")}</div>
    <div class="dos">${tarjeta(T("Competencia por sector", "Competition by sector"), T("Media de ofertas por adjudicación: menos es menos competencia", "Average bids per award: fewer means less competition"), "g-comp")}${tarjeta(T("Adjudicaciones con una sola oferta", "Single-bid awards"), T("Porcentaje sobre las adjudicaciones con dato", "Share of awards with data"), "g-uni")}</div>
    <div class="tarjeta"><h3>${T("Detalle por sector", "Detail by sector")}</h3><div class="desliza" id="l-tabla"></div></div><div id="l-pie"></div>`;
  const pintar = () => {
    const reg = $("f-r").value, a = $("f-a").value, b = $("f-b").value;
    const filtra = h => (!reg || h.region === reg) && h.anio >= a && h.anio <= b;
    const tot = d.hechos_tot.filter(filtra), t = Object.values(sumar(tot.map(h => ({...h, k: 1})), "k"))[0];
    if (!t) { $("l-kpis").innerHTML = `<p class="aviso">${T("No hay datos para ese filtro.", "No data for that filter.")}</p>`; ["g-anio", "g-num", "g-comp", "g-uni", "l-tabla", "l-pie"].forEach(i => $(i).innerHTML = ""); return; }
    $("l-kpis").innerHTML = kpis([[num(t.n), T("licitaciones", "tenders")], [`${num(t.vol / 1e9, 1)} ${T("mil M€", "bn €")}`, T("importe licitado", "tendered amount")], [num(t.os / t.oc, 1), T("ofertas por adjudicación", "bids per award")], [`${num(100 * t.u / t.oc, 1)} %`, T("con una sola oferta", "with a single bid")], [`${num(t.bs / t.bc, 1)} %`, T("baja media", "average discount")]]);
    const porA = Object.entries(sumar(tot, "anio")).sort();
    G.columnas($("g-anio"), {cats: porA.map(x => x[0]), series: [{nombre: T("miles de millones €", "billion €"), color: C.azul, valores: porA.map(x => x[1].vol / 1e9)}], dec: 1});
    G.columnas($("g-num"), {cats: porA.map(x => x[0]), series: [{nombre: T("licitaciones", "tenders"), color: C.azul, valores: porA.map(x => x[1].n)}]});
    const sec = Object.entries(sumar(d.hechos.filter(filtra), "sector")).filter(([, v]) => v.oc >= 20).map(([k, v]) => ({s: sector(k), n: v.n, vol: v.vol, comp: v.os / v.oc, uni: 100 * v.u / v.oc, baja: v.bc ? v.bs / v.bc : 0}));
    if (!sec.length) { ["g-comp", "g-uni", "l-tabla", "l-pie"].forEach(i => $(i).innerHTML = ""); return; }
    const menos = [...sec].sort((x, y) => x.comp - y.comp), uni = [...sec].sort((x, y) => y.uni - x.uni);
    G.barras($("g-comp"), {items: menos.map(x => [x.s, x.comp]), dec: 1, destaca: menos[0].s, titulo: T("ofertas", "bids")});
    G.barras($("g-uni"), {items: uni.map(x => [x.s, x.uni]), dec: 1, unidad: " %", destaca: uni[0].s});
    $("l-tabla").innerHTML = `<table><thead><tr>${[T("Sector", "Sector"), T("Licitaciones", "Tenders"), T("Importe (M€)", "Amount (M€)"), T("Ofertas", "Bids"), T("Una oferta", "Single bid"), T("Baja media", "Discount")].map(x => `<th>${x}</th>`).join("")}</tr></thead><tbody>${[...sec].sort((x, y) => y.vol - x.vol).map(x => `<tr><td>${esc(x.s)}</td><td>${num(x.n)}</td><td>${num(x.vol / 1e6)}</td><td>${num(x.comp, 1)}</td><td>${num(x.uni, 1)} %</td><td>${num(x.baja, 1)} %</td></tr>`).join("")}</tbody></table>`;
    const donde = reg || T("toda España", "all Spain");
    $("l-pie").innerHTML = pie(T(`<b>${esc(donde)}, ${a}–${b}:</b> donde menos se compite es en <b>${menos[0].s}</b> (${num(menos[0].comp, 1)} ofertas de media; ${num(menos[0].uni, 1)} % con una sola). Donde más, en <b>${menos.at(-1).s}</b> (${num(menos.at(-1).comp, 1)}). Una empresa que busque entrar tiene ahí menos rivales.`,
      `<b>${esc(donde)}, ${a}–${b}:</b> competition is lowest in <b>${menos[0].s}</b> (${num(menos[0].comp, 1)} bids on average; ${num(menos[0].uni, 1)}% single-bid) and highest in <b>${menos.at(-1).s}</b> (${num(menos.at(-1).comp, 1)}). A company entering there faces fewer rivals.`),
      [[T("Chat sobre estos datos (código)", "Chat over this data (code)"), `${REPO}/tree/main/chat-analista`]]);
  };
  ["f-r", "f-a", "f-b"].forEach(i => $(i).onchange = pintar); pintar();
}

/* ───────── revisor de ficheros ───────── */
function EJEMPLO() {
  const L = ["fecha;valor"], p = n => String(n).padStart(2, "0");
  for (let i = 0; i < 240; i++) {
    if (i >= 60 && i < 66) continue;
    const d = new Date(2025, 0, 1, i);
    let v = (10 + Math.sin(i / 12) + .05 * Math.sin(i * 7.3)).toFixed(3);
    if (i >= 120 && i < 130) v = "10.500"; if (i === 180) v = "14.900"; if (i === 200) v = "error";
    L.push(`${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:00;${v}`);
  }
  return L.join("\n");
}
const fecha = s => { const m = s.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})(?:[ T](\d{1,2}):(\d{2}))?$/); return m ? new Date(+m[3], m[2] - 1, +m[1], +(m[4] || 0), +(m[5] || 0)).getTime() : Date.parse(s.replace(" ", "T")); };
const mediana = a => { const s = [...a].sort((x, y) => x - y); return s[s.length >> 1]; };
const TIPOS = () => ({ilegible: T("Fila ilegible", "Unreadable row"), duplicado: T("Fecha duplicada", "Duplicate timestamp"), hueco: T("Hueco", "Gap"), congelado: T("Valor congelado", "Frozen value"), pico: T("Pico", "Spike")});
function revisar(texto) {
  const lineas = texto.split(/\r?\n/).map((l, i) => [l.trim(), i + 1]).filter(([l]) => l);
  if (lineas.length > 50000) return {error: T("Máximo 50 000 filas.", "50,000 rows maximum.")};
  const sep = [";", "\t", ","].find(x => lineas.slice(0, 5).some(([l]) => l.includes(x))), filas = [], inc = [];
  lineas.forEach(([l, n], k) => {
    const c = l.split(sep).map(x => x.trim().replace(/^"|"$/g, "")), t = fecha(c[0] || ""), crudo = sep === "," ? c[1] : (c[1] || "").replace(",", "."), v = crudo ? Number(crudo) : NaN;
    if (Number.isFinite(t) && Number.isFinite(v)) filas.push({n, t, v, f: c[0]}); else if (k) inc.push({n, f: c[0] || "", tipo: "ilegible"});
  });
  if (filas.length < 10) return {error: T("Se necesitan al menos 10 filas con fecha y valor.", "At least 10 rows with timestamp and value are needed.")};
  filas.sort((a, b) => a.t - b.t);
  const pasos = filas.slice(1).map((r, i) => r.t - filas[i].t).filter(x => x > 0), paso = pasos.length ? mediana(pasos) : 0;
  const marca = (r, tipo) => { inc.push({n: r.n, f: r.f, v: r.v, tipo}); r.mal ||= tipo; };
  filas.slice(1).forEach((r, i) => { const x = r.t - filas[i].t; if (x === 0) marca(r, "duplicado"); else if (paso && x > 1.5 * paso) marca(r, "hueco"); });
  for (let i = 0, j = 1; j <= filas.length; j++) if (j === filas.length || filas[j].v !== filas[i].v) { if (j - i >= 6) filas.slice(i, j).forEach(r => { r.quieto = true; marca(r, "congelado"); }); i = j; }
  const sanas = filas.filter(r => !r.quieto), res = sanas.map((r, i) => r.v - mediana(sanas.slice(Math.max(0, i - 5), i + 6).map(x => x.v)));
  const escala = 1.4826 * mediana(res.map(Math.abs).filter(x => x > 0).concat(0));
  if (escala > 0) sanas.forEach((r, i) => { if (Math.abs(res[i]) > 6 * escala) marca(r, "pico"); });
  return {filas, inc: inc.sort((a, b) => a.n - b.n)};
}
function linea(caja, r, alto = 240) {
  const w = Math.max(260, caja.clientWidth || 600), NS = "http://www.w3.org/2000/svg";
  const vs = r.filas.map(f => f.v), lo = vs.reduce((a, b) => Math.min(a, b)), hi = vs.reduce((a, b) => Math.max(a, b)), t0 = r.filas[0].t, t1 = r.filas.at(-1).t;
  const x = t => 6 + (t - t0) / (t1 - t0 || 1) * (w - 12), y = v => alto - 8 - (v - lo) / (hi - lo || 1) * (alto - 18);
  caja.innerHTML = `<svg viewBox="0 0 ${w} ${alto}" width="100%" role="img" aria-label="${T("Serie con incidencias", "Series with issues")}"></svg>`;
  const svg = caja.firstChild, add = (t, a) => { const n = document.createElementNS(NS, t); for (const k in a) n.setAttribute(k, a[k]); svg.appendChild(n); return n; };
  add("path", {d: r.filas.map((f, i) => `${i ? "L" : "M"}${x(f.t)},${y(f.v)}`).join(""), fill: "none", stroke: C.azul, "stroke-width": 2, "stroke-linejoin": "round"});
  r.filas.filter(f => f.mal).forEach(f => G.sobre(add("circle", {cx: x(f.t), cy: y(f.v), r: 4.5, fill: C.critico, stroke: "#fff", "stroke-width": 1.5}), `<b>${TIPOS()[f.mal]}</b><br>${esc(f.f)} · ${num(f.v, 3)}`));
}
async function datos(s) {
  s.innerHTML = cabeza({etiqueta: T("Producto 3 · automatización", "Product 3 · automation"), titulo: T("Revisor de ficheros de sensores", "Sensor file checker"),
    pregunta: T("Antes de calcular nada: ¿este fichero de medidas es de fiar?", "Before computing anything: can this measurement file be trusted?"),
    fichas: [[T("Entrada", "Input"), "CSV"], [T("Salida", "Output"), T("informe descargable", "downloadable report")], [T("Privacidad", "Privacy"), T("no sale de tu navegador", "never leaves your browser")]]}) +
    `<div class="filtros"><label>${T("Tu fichero (fecha; valor)", "Your file (timestamp; value)")}<input type="file" id="c-f" accept=".csv,.txt"></label><button class="btn claro" id="c-e">${T("Volver al ejemplo", "Reset example")}</button><button class="btn" id="c-d">${T("Descargar informe", "Download report")}</button></div>
    <div id="c-kpis"></div><div class="tarjeta"><h3>${T("Serie y puntos marcados", "Series and flagged points")}</h3><p class="sub" id="c-sub"></p><div id="g-serie" class="grafico"></div></div>
    <div class="dos">${tarjeta(T("Incidencias por tipo", "Issues by type"), T("Número de filas afectadas", "Affected rows"), "g-tipos")}<div class="tarjeta"><h3>${T("Filas a revisar", "Rows to review")}</h3><div class="desliza alta" id="c-tabla"></div></div></div>` +
    pie(T("<b>Qué aporta:</b> en segundos separa lo medible de lo dudoso y deja constancia, en vez de revisar filas a ojo.", "<b>What it brings:</b> in seconds it separates usable from doubtful data and leaves a record, instead of eyeballing rows."),
      [[T("Código", "Code"), `${REPO}/blob/main/portfolio.js`]]);
  let informe = "", origen = T("Fichero de ejemplo con fallos puestos a propósito.", "Example file with faults added on purpose.");
  const pintar = (texto, de) => {
    const r = revisar(texto); $("c-sub").textContent = de;
    if (r.error) { $("c-kpis").innerHTML = `<p class="aviso">${r.error}</p>`; ["g-serie", "g-tipos", "c-tabla"].forEach(i => $(i).innerHTML = ""); informe = ""; return; }
    const n = {}; r.inc.forEach(x => n[x.tipo] = (n[x.tipo] || 0) + 1);
    const mal = new Set(r.inc.map(x => x.n)).size, total = r.filas.length + (n.ilegible || 0);
    $("c-kpis").innerHTML = kpis([[num(total), T("filas leídas", "rows read")], [num(r.inc.length), T("incidencias", "issues")], [`${num(100 * (total - mal) / total, 1)} %`, T("filas sin incidencias", "clean rows")]]);
    linea($("g-serie"), r);
    if (r.inc.length) G.barras($("g-tipos"), {items: Object.entries(n).map(([k, v]) => [TIPOS()[k], v]).sort((a, b) => b[1] - a[1]), titulo: T("filas", "rows")}); else $("g-tipos").innerHTML = `<p class="sub">${T("Sin incidencias.", "No issues.")}</p>`;
    $("c-tabla").innerHTML = `<table><thead><tr><th>${T("Línea", "Line")}</th><th>${T("Fecha", "Timestamp")}</th><th>${T("Problema", "Problem")}</th></tr></thead><tbody>${r.inc.slice(0, 200).map(x => `<tr><td>${x.n}</td><td>${esc(x.f)}</td><td>${TIPOS()[x.tipo]}</td></tr>`).join("")}</tbody></table>`;
    informe = [T("linea;fecha;valor;problema", "line;timestamp;value;problem"), ...r.inc.map(x => [x.n, x.f.replace(/^[=+\-@]/, "'$&"), x.v ?? "", TIPOS()[x.tipo]].join(";"))].join("\n");
  };
  $("c-e").onclick = () => { $("c-f").value = ""; pintar(EJEMPLO(), origen); };
  $("c-f").onchange = e => { const f = e.target.files[0]; if (!f) return; if (f.size > 3e6) { $("c-kpis").innerHTML = `<p class="aviso">${T("Máximo 3 MB.", "3 MB maximum.")}</p>`; return; } f.text().then(t => pintar(t, f.name)); };
  $("c-d").onclick = () => { if (!informe) return; const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob(["﻿" + informe], {type: "text/csv"})); a.download = T("informe.csv", "report.csv"); a.click(); URL.revokeObjectURL(a.href); };
  pintar(EJEMPLO(), origen);
}

/* ───────── herramientas MCP ───────── */
function flujo(mini) {
  const cajas = [[T("Pregunta", "Question"), 8], [T("Modelo", "Model"), 118], [T("Herramienta", "Tool"), 228], [T("Respuesta", "Answer"), 338]];
  return `<svg class="flujo" viewBox="0 0 438 ${mini ? 120 : 90}" width="100%" role="img" aria-label="${T("La pregunta pasa por el modelo, que elige una herramienta y responde con su resultado", "The question goes to the model, which picks a tool and answers with its result")}">` +
    cajas.map(([t, x], i) => `<rect x="${x}" y="${mini ? 40 : 24}" width="92" height="40" rx="6" fill="${i === 2 ? C.azul : "#fff"}" stroke="${i === 2 ? C.azul : C.gris}"/><text x="${x + 46}" y="${mini ? 64 : 48}" text-anchor="middle" font-size="12" fill="${i === 2 ? "#fff" : C.tinta}">${t}</text>` +
      (i < 3 ? `<path d="M${x + 94},${mini ? 60 : 44}h12m-4,-4l4,4l-4,4" fill="none" stroke="${C.suave}"/>` : "")).join("") + "</svg>";
}
const HERR = () => [[T("Documentos", "Documents"), "biblioteca_listar · leer · buscar · consultar · indexar", T("Búsqueda con cita sobre archivos propios", "Cited search over own files")],
  [T("Incertidumbre", "Uncertainty"), "incertidumbre_propagar · estimar_malla · validar", T("GUM, Monte Carlo, error de malla y validación", "GUM, Monte Carlo, mesh error and validation")],
  [T("Código", "Code"), "proyectos_listar · arbol · leer · buscar · git", T("Lectura de proyectos, sin escritura", "Read-only project access")]];
async function herramientas(s) {
  const [grab, pruebas] = await Promise.all([leer("vivo/grabaciones.json"), leer("docs/pruebas.json")]);
  const txt = grab.agente.flatMap(r => r.eventos).find(e => e.paso === "resultado" && e.texto.includes('"gum"'))?.texto || "";
  const g = txt.match(/"gum": \{"y": ([\d.]+), "u": [\d.]+, "k": [\d.]+, "U": ([\d.]+)/), mc = txt.match(/"intervalo": \[([\d.]+), ([\d.]+)\]/), mcy = txt.match(/"monte_carlo": \{"y": ([\d.]+)/);
  s.innerHTML = cabeza({etiqueta: T("Producto 4 · agentes", "Product 4 · agents"), titulo: T("Herramientas para agentes (MCP)", "Tools for agents (MCP)"),
    pregunta: T("¿Cómo se consigue que un asistente calcule y consulte de verdad en lugar de responder de memoria?", "How do you make an assistant actually compute and look things up instead of answering from memory?"),
    fichas: [[T("Protocolo", "Protocol"), "Model Context Protocol"], [T("Lenguaje", "Language"), "Python"], [T("Seguridad", "Safety"), T("cada herramienta declara si escribe", "each tool declares whether it writes")]]}) +
    kpis([["13", T("herramientas", "tools")], ["3", T("áreas independientes", "independent areas")], [num(pruebas.proyectos.find(p => p.proyecto === "mcp-hub").pasan), T("tests del servidor", "server tests")]]) +
    `<div class="tarjeta"><h3>${T("Cómo trabaja", "How it works")}</h3>${flujo(false)}</div>
    <div class="dos">${tarjeta(T("Un resultado real de una herramienta", "A real tool result"), T("Área de una placa, a = 3,75 m y b = 2,65 m (u = 0,01 m). Intervalos al 95 %, en m²", "Plate area, a = 3.75 m and b = 2.65 m (u = 0.01 m). 95% intervals, m²"), "g-inc")}
    <div class="tarjeta"><h3>${T("Qué puede hacer", "What it can do")}</h3><div class="desliza"><table><thead><tr><th>${T("Área", "Area")}</th><th>${T("Para qué", "Purpose")}</th></tr></thead><tbody>${HERR().map(([a, b, c]) => `<tr><td><b>${a}</b><br><code>${b}</code></td><td>${c}</td></tr>`).join("")}</tbody></table></div></div></div>
    <div class="tarjeta"><h3>${T("Pruébalo", "Try it")}</h3><p class="sub">${T("Sesiones reales grabadas. Con el servidor local, en directo con Ollama.", "Real recorded sessions. With the local server, live with Ollama.")}</p><div id="vivo" data-base="${base}"></div></div>` +
    pie(T("<b>Qué aporta:</b> las cifras salen de código probado y queda registro de cada llamada. El modelo elige y redacta, no calcula.", "<b>What it brings:</b> numbers come from tested code and every call is logged. The model chooses and writes; it does not compute."),
      [[T("Código", "Code"), `${REPO}/tree/main/mcp-hub`]]);
  if (g && mc) G.intervalos($("g-inc"), {unidad: "m²", filas: [{nombre: T("Fórmula (GUM)", "Formula (GUM)"), color: C.naranja, centro: +g[1], lo: +g[1] - +g[2], hi: +g[1] + +g[2]}, {nombre: "Monte Carlo", color: C.azul, centro: +mcy[1], lo: +mc[1], hi: +mc[2]}]});
  await cargarScript("navegador.js"); await cargarScript("vivo.js");
}

/* ───────── calidad ───────── */
async function calidad(s) {
  const [{ev, ok}, pr] = await Promise.all([evaluacion(), leer("docs/pruebas.json")]);
  const r = ev.resumen, M = METODOS(), conj = [["desarrollo", T("Desarrollo", "Development")], ["reservado", T("Reservadas", "Held-out")]];
  s.innerHTML = cabeza({etiqueta: T("Cómo se comprueba", "How it is verified"), titulo: T("Calidad del agente", "Agent quality"),
    pregunta: T("¿Funciona de verdad? Se mide cada etapa contra dos alternativas, incluidas las preguntas donde pierde.", "Does it really work? Each stage is measured against two alternatives, including where it loses."),
    fichas: [[T("Preguntas", "Questions"), String(ev.detalle.length / 3)], [T("Ventana", "Window"), `${num(ev.num_ctx)} tokens`], [T("Fecha", "Date"), ev.fecha]]}) +
    kpis([[num(pr.total), T("tests automáticos, también en GitHub", "automated tests, also on GitHub")], [pr.cobertura_agente?.["agente.py"] || "—", T("cobertura del código del agente", "agent code coverage")], [`${r.reservado.embudo.recuperada}/${r.reservado.embudo.preguntas}`, T("reservadas en las que la búsqueda trae el fragmento", "held-out questions where search finds the fragment")], [`${num(r.reservado.agente.tokens_medios / r.reservado.simple.tokens_medios, 1)}×`, T("tokens frente a un RAG simple", "tokens versus simple RAG")]]) +
    `<div class="dos">${tarjeta(T("Aciertos por método", "Correct answers by method"), T("Porcentaje, tras revisar las respuestas a mano", "Percentage, after manual review"), "g-ac")}${tarjeta(T("Dónde pierde el agente la respuesta", "Where the agent loses the answer"), T("Preguntas reservadas que conservan la evidencia en cada etapa", "Held-out questions still holding the evidence after each stage"), "g-emb")}</div>
    <div class="dos">${tarjeta(T("Calidad de la búsqueda", "Search quality"), T("El fragmento con la respuesta aparece entre los k primeros (reservadas, %)", "Fragment with the answer within the top k (held-out, %)"), "g-rec")}${tarjeta(T("Tests por proyecto", "Tests per project"), T("Unitarios, flujo con modelo simulado, integración y seguridad", "Unit, pipeline with simulated model, integration and security"), "g-test")}</div>` +
    pie(T(`<b>Conclusión:</b> en desarrollo el agente acierta ${ok("desarrollo", "agente")}/${r.desarrollo.agente.con_respuesta} frente a ${ok("desarrollo", "simple")} del RAG simple, pero en preguntas reservadas queda en ${ok("reservado", "agente")}/${r.reservado.agente.con_respuesta} (RAG simple ${ok("reservado", "simple")}, volcado ${ok("reservado", "volcado")}). La mejora no generaliza todavía; el siguiente paso es la búsqueda.`,
      `<b>Conclusion:</b> on development the agent scores ${ok("desarrollo", "agente")}/${r.desarrollo.agente.con_respuesta} versus ${ok("desarrollo", "simple")} for simple RAG, but on held-out questions it gets ${ok("reservado", "agente")}/${r.reservado.agente.con_respuesta} (simple RAG ${ok("reservado", "simple")}, stuffing ${ok("reservado", "volcado")}). The gain does not generalise yet; search is next.`),
      [[T("Informe completo", "Full report"), `${REPO}/blob/main/agente/docs/${T("EVALUACION", "EVALUATION")}.md`], [T("Decisiones y fallos", "Decisions and failures"), `${REPO}/blob/main/agente/docs/DECISIONES.md`], [T("Tests en GitHub", "Tests on GitHub"), `${REPO}/actions`]]);
  G.columnas($("g-ac"), {cats: conj.map(c => c[1]), etiquetas: true, unidad: "%", series: M.map(([m, n, color]) => ({nombre: n, color, valores: conj.map(([c]) => Math.round(100 * ok(c, m) / r[c][m].con_respuesta))}))});
  const e = r.reservado.embudo;
  G.barras($("g-emb"), {items: [[T("Con respuesta en la norma", "Answerable"), e.preguntas], [T("Fragmento leído", "Fragment read"), e.recuperada], [T("Guardado como nota", "Kept as note"), e.anotada], [T("Respuesta correcta", "Correct answer"), e.correcta]], titulo: T("preguntas", "questions")});
  const rec = r.reservado.recuperacion;
  G.columnas($("g-rec"), {cats: ["k = 1", "k = 4", "k = 6", "k = 12"], unidad: "%", series: [["bm25", "BM25", C.naranja], ["vector", T("Vectorial", "Vector"), C.agua], ["hibrido", T("Híbrida", "Hybrid"), C.azul]].map(([k, n, color]) => ({nombre: n, color, valores: [1, 4, 6, 12].map(x => Math.round(100 * rec[k][`hit@${x}`]))}))});
  G.barras($("g-test"), {items: pr.proyectos.map(p => [p.proyecto, p.pasan]).sort((a, b) => b[1] - a[1]), titulo: "tests"});
}

/* ───────── pestañas ───────── */
const PAGINAS = {inicio, agente, licitaciones, datos, herramientas, calidad};
const hechas = new Set();
async function mostrar(id) {
  document.querySelectorAll("main > section").forEach(s => s.hidden = s.id !== "p-" + id);
  document.querySelectorAll("nav [data-t]").forEach(a => a.toggleAttribute("aria-current", a.dataset.t === id));
  const idioma = $("idioma"); idioma.href = idioma.href.split("#")[0] + "#" + id;
  if (hechas.has(id)) return;
  hechas.add(id); const s = $("p-" + id);
  s.innerHTML = `<p class="sub">${T("Cargando…", "Loading…")}</p>`;
  try { await PAGINAS[id](s); }
  catch (e) { console.error(e); hechas.delete(id); s.innerHTML = `<p class="aviso">${T("No se han podido cargar los datos. Recarga la página.", "Could not load the data. Reload the page.")}</p>`; }
}
function ruta() {
  const h = location.hash.slice(1);
  if (PAGINAS[h]) { mostrar(h); scrollTo(0, 0); } else if (!h) mostrar("inicio"); else if (!hechas.size) mostrar("inicio");
}
addEventListener("hashchange", ruta);
let ancho = innerWidth, espera;
addEventListener("resize", () => { if (innerWidth === ancho) return; ancho = innerWidth; clearTimeout(espera);
  espera = setTimeout(() => { const v = document.querySelector("main > section:not([hidden])").id.slice(2); if (!["agente", "herramientas"].includes(v)) { hechas.delete(v); mostrar(v); } }, 250); });
ruta();
})();
