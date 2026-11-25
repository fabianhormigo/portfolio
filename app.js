/* Interacciones del portafolio. Cada bloque actúa solo si su página tiene los elementos. */
(() => {
const EN = document.documentElement.lang === "en", T = (es, en) => EN ? en : es, $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

/* grabaciones reales y, en el chat, su gráfico */
document.querySelectorAll("[data-replay]").forEach(box => {
  const d = window.DATOS.grab, sel = box.querySelector("select"), out = box.querySelector(".out");
  d.forEach((x, i) => sel.add(new Option(x.titulo, i)));
  const pinta = () => {
    const x = d[sel.value]; out.className = "out" + (box.dataset.replay === "mcp" ? " mono" : "") + (x.clase === "err" ? " mal" : x.clase ? " ok" : ""); out.textContent = x.texto;
    const g = $("graf"); if (!g) return;
    const v = window.DATOS.graficos[sel.value];
    if (!v) { g.innerHTML = `<p class="sub">${T("Esta acción filtra el panel; no dibuja un gráfico.", "This action filters the dashboard; it draws no chart.")}</p>`; return; }
    const max = Math.max(...v.datos.map(p => p[1]));
    g.innerHTML = `<h3 style="margin-top:18px">${esc(v.titulo)}</h3>` + v.datos.map(([n, y]) =>
      `<div class="barra"><span>${esc(n)}</span><span><i style="width:${100 * y / max}%"></i></span><b>${y.toLocaleString(EN ? "en-GB" : "es-ES")}${v.unidad}</b></div>`).join("");
  };
  sel.onchange = pinta; pinta();
});

/* demo de idempotencia */
const vistos = new Set(), clientes = new Map(), reg = [];
const EV = {a: {id: "ev-1", email: "ana@ejemplo.com", estado: T("nuevo", "new")}, b: {id: "ev-2", email: " ANA@ejemplo.com ", estado: T("contactado", "contacted")}, x: {id: "ev-3", email: "luis@ejemplo.com", estado: "???"}};
document.querySelectorAll("[data-ev]").forEach(b => b.onclick = () => {
  const e = EV[b.dataset.ev], email = e.email.trim().toLowerCase(); let r;
  if (vistos.has(e.id)) r = T("duplicado: ignorado", "duplicate: ignored");
  else if (e.estado === "???") r = T("estado no válido: se revierte y podrá reintentarse", "invalid status: rolled back, can be retried");
  else { vistos.add(e.id); clientes.set(email, e.estado); r = T("aplicado", "applied"); }
  reg.unshift(`${e.id} → ${r}`);
  $("e-o").textContent = reg.slice(0, 6).join("\n") + `\n\n${T("Clientes en la base", "Customers stored")}: ${clientes.size}\n` + [...clientes].map(([k, v]) => `· ${k} (${v})`).join("\n");
});

if ($("q-doc")) {
/* ---------- 1 · documento ---------- */
const VACIAS = new Set(("a al algo como con cual cuando cuanto de del desde donde el ella en entre es esa ese esta este hay la las le lo los mas me mi no o para pero por que quien se si sin sobre son su sus un una unos y ya cada debe puede " +
  "an and are as at be by for from has have how in is it its of on or that the this to was what when where which with do does can must should much many often").split(" "));
const tokens = s => (s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").match(/[a-z0-9]+/g) || [])
  .filter(t => !VACIAS.has(t)).map(t => t.length > 4 && t.endsWith("s") ? t.slice(0, -1) : t);
const raizT = t => t.length > 5 ? t.slice(0, 5) : t;
function buscar(texto, pregunta) {
  const parr = texto.split(/\n\s*\n|\n(?=\S)/).map(p => p.trim()).filter(p => p.length > 15);
  const docs = parr.map(p => tokens(p).map(raizT)), q = [...new Set(tokens(pregunta).map(raizT))];
  if (!parr.length || !q.length) return [];
  const avg = docs.reduce((a, d) => a + d.length, 0) / docs.length, N = docs.length;
  return docs.map((d, i) => {
    let s = 0, hit = 0;
    q.forEach(t => {
      const tf = d.filter(x => x === t).length; if (!tf) return; hit++;
      const df = docs.filter(x => x.includes(t)).length;
      s += Math.log(1 + (N - df + .5) / (df + .5)) * tf * 2.5 / (tf + 1.5 * (.25 + .75 * d.length / avg));
    });
    return {i, s, cob: hit / q.length, p: parr[i], q};
  }).filter(r => r.cob >= .4).sort((a, b) => b.s - a.s).slice(0, 2);
}
const marcar = (p, q) => p.split(/([\p{L}\p{N}]+)/u).map(w => {
  const t = tokens(w)[0]; return t && q.includes(raizT(t)) ? `<mark>${esc(w)}</mark>` : esc(w); }).join("");
$("q-doc").value = T("1. El sensor de inclinación se calibra cada doce meses o después de un golpe.\n2. Las lecturas se toman en dos posiciones opuestas en cada profundidad.\n3. El equipo se almacena entre 5 y 35 grados, dentro de su maleta.\n4. El informe indica el desplazamiento acumulado con su incertidumbre.",
  "1. The inclination sensor is calibrated every twelve months or after an impact.\n2. Readings are taken in two opposite positions at each depth.\n3. The equipment is stored between 5 and 35 degrees, inside its case.\n4. The report states cumulative displacement with its uncertainty.");
$("q-q").value = T("¿cada cuánto se calibra el sensor?", "how often is the sensor calibrated?");
$("q-b").onclick = () => {
  const o = $("q-o"), r = buscar($("q-doc").value, $("q-q").value); o.hidden = false;
  o.className = "out " + (r.length ? "ok" : "mal");
  o.innerHTML = r.length ? r.map((x, n) => `<p><b>${n ? T("También relacionado", "Also related") : T("Evidencia", "Evidence")} · ${T("párrafo", "paragraph")} ${x.i + 1}</b><br>${marcar(x.p, x.q)}</p>`).join("")
    : `<b>${T("Sin evidencia en este documento.", "No evidence in this document.")}</b> ${T("No se inventa una respuesta.", "No answer is made up.")}`;
};

}

if ($("c-t")) {
function fecha(s) {
  const m = s.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?$/);
  return m ? new Date(+m[3], m[2] - 1, +m[1], +(m[4] || 0), +(m[5] || 0), +(m[6] || 0)).getTime() : Date.parse(s.replace(" ", "T"));
}
const mediana = a => { const s = [...a].sort((x, y) => x - y); return s[s.length >> 1]; };
function revisar(texto, min, max) {
  const lineas = texto.split(/\r?\n/).map((l, i) => [l.trim(), i + 1]).filter(([l]) => l);
  if (lineas.length > 50000) return {error: T("Máximo 50 000 filas.", "50,000 rows maximum.")};
  const sep = [";", "\t", ","].find(s => lineas.slice(0, 5).some(([l]) => l.includes(s))), filas = [], inc = [];
  lineas.forEach(([l, n], k) => {
    const c = l.split(sep).map(x => x.trim().replace(/^"|"$/g, ""));
    const t = fecha(c[0] || ""), crudo = sep === "," ? c[1] : (c[1] || "").replace(",", "."), v = crudo === "" || crudo === undefined ? NaN : Number(crudo);
    if (Number.isFinite(t) && Number.isFinite(v)) filas.push({n, t, v, f: c[0]});
    else if (k) inc.push({n, f: c[0] || "", tipo: T("fila ilegible", "unreadable row")});
  });
  if (filas.length < 10) return {error: T("Necesito al menos 10 filas con fecha y valor.", "I need at least 10 rows with timestamp and value.")};
  filas.sort((a, b) => a.t - b.t);
  const dts = filas.slice(1).map((r, i) => r.t - filas[i].t).filter(d => d > 0), paso = dts.length ? mediana(dts) : 0;
  const marca = (r, tipo) => { inc.push({n: r.n, f: r.f, v: r.v, tipo}); r.mal = r.mal || tipo; };
  filas.slice(1).forEach((r, i) => { const d = r.t - filas[i].t;
    if (d === 0) marca(r, T("fecha duplicada", "duplicate timestamp")); else if (paso && d > 1.5 * paso) marca(r, T("hueco antes de esta fila", "gap before this row")); });
  filas.forEach(r => { r.fuera = (min !== "" && r.v < +min) || (max !== "" && r.v > +max); if (r.fuera) marca(r, T("fuera de rango", "out of range")); });
  for (let i = 0, j = 1; j <= filas.length; j++) if (j === filas.length || filas[j].v !== filas[i].v) {
    if (j - i >= 6) filas.slice(i, j).forEach(r => { r.congelada = true; marca(r, T("lectura congelada", "frozen reading")); }); i = j; }
  // picos: se comparan solo contra lecturas sanas, para que un tramo congelado no arrastre la mediana
  const sanas = filas.filter(r => !r.fuera && !r.congelada);
  const res = sanas.map((r, i) => r.v - mediana(sanas.slice(Math.max(0, i - 5), i + 6).map(x => x.v)));
  const escala = 1.4826 * mediana(res.map(Math.abs).filter(x => x > 0).concat(0));
  if (escala > 0) sanas.forEach((r, i) => { if (Math.abs(res[i]) > 6 * escala) marca(r, T("pico", "spike")); });
  return {filas, inc: inc.sort((a, b) => a.n - b.n)};
}
function pintar() {
  const r = revisar($("c-t").value, "", ""), o = $("c-o"); o.hidden = false;
  if (r.error) { o.className = "out mal"; o.textContent = r.error; return; }
  const n = {}; r.inc.forEach(x => n[x.tipo] = (n[x.tipo] || 0) + 1); o.className = "out" + (r.inc.length ? "" : " ok");
  o.textContent = `${r.filas.length} ${T("lecturas", "readings")} · ${r.inc.length} ${T("incidencias", "issues")}\n` + Object.entries(n).map(([k, v]) => `${k}: ${v}`).join("\n") +
    (r.inc.length ? "\n\n" + r.inc.slice(0, 10).map(x => `${T("línea", "line")} ${x.n} · ${x.f} · ${x.tipo}`).join("\n") : "");
}
$("c-e").onclick = () => {
  const L = [T("fecha;valor", "timestamp;value")];
  for (let i = 0; i < 240; i++) {
    if (i >= 60 && i < 66) continue;
    const d = new Date(2025, 0, 1, i), p = n => String(n).padStart(2, "0");
    let v = (10 + Math.sin(i / 12) + .05 * Math.sin(i * 7.3)).toFixed(3);
    if (i >= 120 && i < 130) v = "10.500"; if (i === 180) v = "14.900"; if (i === 200) v = "error";
    L.push(`${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:00;${v}`);
  }
  $("c-t").value = L.join("\n"); pintar();
};
$("c-f").onchange = e => { const f = e.target.files[0]; if (!f) return;
  if (f.size > 3e6) { $("c-o").hidden = false; $("c-o").textContent = T("Máximo 3 MB.", "3 MB maximum."); return; }
  f.text().then(t => { $("c-t").value = t; pintar(); }); };
$("c-b").onclick = pintar;
}
})();
