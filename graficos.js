/* Gráficos SVG propios: columnas, barras horizontales e intervalos. Un eje, marcas finas, etiqueta al pasar y tabla. */
window.G = (() => {
const NS = "http://www.w3.org/2000/svg";
const EN = document.documentElement.lang === "en";
const C = {azul: "#2a78d6", naranja: "#eb6834", agua: "#1baf7a", gris: "#c9ccd1", rejilla: "#e7e8ea", tinta: "#0b0b0b", suave: "#52514e", critico: "#c43d3c"};
const num = (x, d = 0) => Number(x).toLocaleString(EN ? "en-GB" : "es-ES", {maximumFractionDigits: d, useGrouping: "always"});
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const tip = document.createElement("div"); tip.className = "tip"; tip.setAttribute("role", "tooltip"); document.body.appendChild(tip);
function sobre(nodo, html) {
  nodo.addEventListener("pointermove", e => { tip.innerHTML = html; tip.classList.add("on");
    tip.style.left = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8) + "px"; tip.style.top = (e.clientY + 14) + "px"; });
  nodo.addEventListener("pointerleave", () => tip.classList.remove("on"));
}
const el = (t, a, p) => { const n = document.createElementNS(NS, t); for (const k in a) n.setAttribute(k, a[k]); p?.appendChild(n); return n; };
const texto = (p, x, y, s, a = {}) => { const t = el("text", {x, y, fill: C.suave, "font-size": 11.5, ...a}, p); t.textContent = s; return t; };
const techo = m => { if (m <= 0) return 1; const p = 10 ** Math.floor(Math.log10(m)), r = m / p; return (r <= 1 ? 1 : r <= 2 ? 2 : r <= 2.5 ? 2.5 : r <= 5 ? 5 : 10) * p; };
/* barra con el extremo del dato redondeado y la base recta */
const columna = (x, y, w, h, r = 4) => { r = Math.min(r, w / 2, h); return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`; };
const fila = (x, y, w, h, r = 4) => { r = Math.min(r, h / 2, w); return `M${x},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h - r}Q${x + w},${y + h} ${x + w - r},${y + h}H${x}Z`; };

function marco(caja, alto) {
  caja.innerHTML = "";
  const ancho = Math.max(280, caja.clientWidth || 560);
  return {ancho, svg: el("svg", {viewBox: `0 0 ${ancho} ${alto}`, width: "100%", role: "img"}, caja)};
}
function extras(caja, leyenda, cabecera, filas) {
  if (leyenda?.length > 1) caja.insertAdjacentHTML("beforeend", `<div class="leyenda">${leyenda.map(([n, c]) => `<span><i style="background:${c}"></i>${esc(n)}</span>`).join("")}</div>`);
  caja.insertAdjacentHTML("beforeend", `<details class="datos"><summary>${EN ? "View data" : "Ver datos"}</summary><div class="desliza"><table><thead><tr>${cabecera.map(c => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody>${filas.map(f => `<tr>${f.map(c => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div></details>`);
}

/* columnas agrupadas o apiladas */
function columnas(caja, {cats, series, apiladas = false, refs = [], dec = 0, alto = 260, unidad = "", etiquetas = false}) {
  const {ancho, svg} = marco(caja, alto), m = {t: 20, r: 8, b: 26, l: 52}, w = ancho - m.l - m.r, h = alto - m.t - m.b;
  const totales = cats.map((_, i) => apiladas ? series.reduce((a, s) => a + s.valores[i], 0) : Math.max(...series.map(s => s.valores[i])));
  const max = techo(Math.max(...totales, ...refs.map(r => r.v)) * 1.05), y = v => m.t + h - v / max * h;
  for (let k = 0; k <= 4; k++) { const v = max * k / 4; el("line", {x1: m.l, x2: ancho - m.r, y1: y(v), y2: y(v), stroke: C.rejilla}, svg); texto(svg, m.l - 6, y(v) + 4, num(v, dec), {"text-anchor": "end"}); }
  const paso = w / cats.length, n = apiladas ? 1 : series.length, bw = Math.min(26, (paso * .72 - 2 * (n - 1)) / n);
  cats.forEach((cat, i) => {
    let base = 0; const x0 = m.l + i * paso + (paso - (bw * n + 2 * (n - 1))) / 2;
    series.forEach((s, j) => {
      const v = s.valores[i], x = x0 + (apiladas ? 0 : j * (bw + 2)), arriba = y(base + v), altoB = Math.max(0, y(base) - arriba - (apiladas && base ? 2 : 0));
      const cima = !apiladas || j === series.length - 1 || series.slice(j + 1).every(t => !t.valores[i]);
      const p = el("path", {d: columna(x, arriba, bw, altoB, cima ? 4 : 0), fill: s.color}, svg);
      sobre(el("rect", {x: x - 1, y: arriba, width: bw + 2, height: Math.max(8, altoB), fill: "transparent"}, svg), `<b>${esc(cat)}</b><br>${esc(s.nombre)}: ${num(v, dec)} ${unidad}`);
      if (etiquetas && !apiladas) texto(svg, x + bw / 2, arriba - 5, num(v, dec), {"text-anchor": "middle", fill: C.tinta});
      if (apiladas) base += v;
    });
    if (i % Math.ceil(cats.length / (w / 44)) === 0) texto(svg, m.l + i * paso + paso / 2, alto - 8, cat, {"text-anchor": "middle"});
  });
  refs.forEach(r => { el("line", {x1: m.l, x2: ancho - m.r, y1: y(r.v), y2: y(r.v), stroke: r.color || C.suave, "stroke-width": 1.5, "stroke-dasharray": "5 4"}, svg); texto(svg, ancho - m.r, y(r.v) - 5, r.nombre, {"text-anchor": "end", fill: C.tinta}); });
  extras(caja, series.map(s => [s.nombre, s.color]), ["", ...series.map(s => s.nombre)], cats.map((c, i) => [c, ...series.map(s => num(s.valores[i], dec))]));
}

/* barras horizontales ordenadas, con una destacada */
function barras(caja, {items, dec = 0, unidad = "", color = C.azul, destaca = null, titulo = ""}) {
  const fh = 28, {ancho, svg} = marco(caja, items.length * fh + 6), etq = Math.min(210, ancho * .4), w = ancho - etq - 78;
  const max = Math.max(...items.map(i => i[1])) || 1;
  items.forEach(([n, v], i) => {
    const y = i * fh + 6, bw = Math.max(2, v / max * w), on = destaca === null || destaca === n;
    texto(svg, etq - 8, y + 13, n.length > 30 ? n.slice(0, 29) + "…" : n, {"text-anchor": "end", fill: C.tinta, "font-size": 12});
    el("path", {d: fila(etq, y + 1, bw, 16), fill: on ? color : C.gris}, svg);
    texto(svg, etq + bw + 6, y + 13, `${num(v, dec)}${unidad}`, {fill: C.tinta, "font-weight": 600});
    sobre(el("rect", {x: 0, y, width: ancho, height: fh - 4, fill: "transparent"}, svg), `<b>${esc(n)}</b>: ${num(v, dec)}${unidad}`);
  });
  extras(caja, null, ["", titulo || unidad.trim() || "valor"], items.map(([n, v]) => [n, num(v, dec) + unidad]));
}

/* punto e intervalo, para comparar incertidumbres */
function intervalos(caja, {filas, dec = 3, unidad = ""}) {
  const fh = 46, {ancho, svg} = marco(caja, filas.length * fh + 26), etq = Math.min(150, ancho * .32), w = ancho - etq - 20;
  const lo = Math.min(...filas.map(f => f.lo)), hi = Math.max(...filas.map(f => f.hi)), pad = (hi - lo) * .12, x = v => etq + (v - lo + pad) / (hi - lo + 2 * pad) * w;
  filas.forEach((f, i) => {
    const y = i * fh + 22;
    texto(svg, etq - 10, y + 4, f.nombre, {"text-anchor": "end", fill: C.tinta, "font-size": 12});
    el("line", {x1: x(f.lo), x2: x(f.hi), y1: y, y2: y, stroke: f.color, "stroke-width": 2}, svg);
    [f.lo, f.hi].forEach(v => { el("line", {x1: x(v), x2: x(v), y1: y - 7, y2: y + 7, stroke: f.color, "stroke-width": 2}, svg); texto(svg, x(v), y + 21, num(v, dec), {"text-anchor": "middle"}); });
    el("circle", {cx: x(f.centro), cy: y, r: 5, fill: f.color, stroke: "#fff", "stroke-width": 2}, svg);
    sobre(el("rect", {x: x(f.lo), y: y - 12, width: x(f.hi) - x(f.lo), height: 24, fill: "transparent"}, svg), `<b>${esc(f.nombre)}</b><br>${num(f.centro, dec + 1)} [${num(f.lo, dec)} – ${num(f.hi, dec)}] ${unidad}`);
  });
  extras(caja, null, ["", "min", "centro", "max"], filas.map(f => [f.nombre, num(f.lo, dec), num(f.centro, dec + 1), num(f.hi, dec)]));
}
return {C, num, esc, sobre, columnas, barras, intervalos};
})();
