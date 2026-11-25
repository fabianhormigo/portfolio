/* Modelo dentro del navegador del visitante (WebLLM + WebGPU). Emite los mismos eventos que el servidor local.
   La librería se carga de jsdelivr y los pesos de huggingface.co, solo cuando el visitante lo pide. */
window.Navegador = (() => {
const LIB = "https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@0.2.89/+esm";   // versión fijada
const MODELOS = [{nombre: "Qwen2.5-0.5B-Instruct", mb: 290}, {nombre: "Qwen2.5-1.5B-Instruct", mb: 880}];
let motor = null, activo = "", cola = Promise.resolve();
const api = {MODELOS, importar: () => import(LIB), listo: () => !!motor, nombre: () => activo};

api.cargar = async (i, progreso) => {
  const adaptador = navigator.gpu && await navigator.gpu.requestAdapter();
  if (!adaptador) throw new Error("WebGPU");
  const id = `${MODELOS[i].nombre}-${adaptador.features.has("shader-f16") ? "q4f16_1" : "q4f32_1"}-MLC`;
  const {CreateMLCEngine} = await api.importar();
  motor = await CreateMLCEngine(id, {initProgressCallback: r => progreso(r.progress, r.text)});
  activo = MODELOS[i].nombre;
};

/* una generación cada vez; si el visitante lanza otra, la anterior se interrumpe */
function generar(mensajes, esquema, emitir, vigente) {
  const turno = cola.then(async () => {
    let texto = "";
    if (!vigente()) return texto;
    const flujo = await motor.chat.completions.create({messages: mensajes, stream: true, temperature: 0, max_tokens: 300,
      response_format: {type: "json_object", schema: JSON.stringify(esquema)}});
    for await (const trozo of flujo) {
      const t = trozo.choices[0]?.delta?.content || "";
      if (!vigente()) { motor.interruptGenerate(); continue; }
      texto += t; if (t) emitir({paso: "token", t});
    }
    return texto;
  });
  cola = turno.catch(() => {});
  return turno;
}
const json = s => { try { return JSON.parse(s); } catch { return null; } };

/* ---------- documento: BM25 + modelo + cita literal ---------- */
const VACIAS = new Set(("a al algo como con cual cuando cuanto de del desde donde el ella en entre es esa ese esta este hay la las le lo los mas me mi no o para pero por que quien se si sin sobre son su sus un una unos y ya cada debe puede " +
  "an and are as at be by for from has have how in is it its of on or that the this to was what when where which with do does can must should much many often").split(" "));
const tokens = s => (s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").match(/[a-z0-9]+/g) || []).filter(t => !VACIAS.has(t)).map(t => t.slice(0, 5));
api.buscar = (frags, pregunta, k = 3) => {
  const docs = frags.map(f => tokens(f.texto)), q = [...new Set(tokens(pregunta))], N = docs.length;
  const media = docs.reduce((a, d) => a + d.length, 0) / (N || 1);
  return frags.map((f, i) => ({f, s: q.reduce((s, t) => {
    const tf = docs[i].filter(x => x === t).length; if (!tf) return s;
    const df = docs.filter(d => d.includes(t)).length;
    return s + Math.log(1 + (N - df + .5) / (df + .5)) * tf * 2.5 / (tf + 1.5 * (.25 + .75 * docs[i].length / media));
  }, 0)})).filter(x => x.s > 0).sort((a, b) => b.s - a.s).slice(0, k).map(x => x.f);
};
const plano = s => String(s).replace(/\s+/g, " ").replace(/^[ ."«»]+|[ ."«»]+$/g, "");
api.validar = (salida, frags) => {
  if (!salida) return "rechazada";
  if (!salida.hay_evidencia) return "sin_evidencia";
  const f = frags.find(x => x.id === String(salida.id).replace(/[\[\] ]/g, ""));
  return f && plano(salida.cita) && String(salida.respuesta || "").trim() && plano(f.texto).includes(plano(salida.cita)) ? "valida" : "rechazada";
};
const ESQUEMA_RAG = {type: "object", required: ["hay_evidencia", "id", "cita", "respuesta"], properties: {
  hay_evidencia: {type: "boolean"}, id: {type: "string"}, cita: {type: "string"}, respuesta: {type: "string"}}};

api.rag = async (q, emitir, vigente, base) => {
  let frags, total;
  if (q.documento !== undefined) {
    frags = q.documento.slice(0, 20000).split("\n").map(s => s.trim()).filter(s => s.length > 15).slice(0, 60)
      .map((texto, i) => ({id: `P${i + 1}`, texto}));
    total = frags.length;
    emitir({paso: "filtro", total, candidatos: total, norma: "DOC", version: "1"});
  } else {
    const corpus = await (await fetch(base + "vivo/corpus.json")).json();
    frags = corpus.filter(d => d.norma === q.norma && d.version === q.version);
    emitir({paso: "filtro", total: corpus.length, candidatos: frags.length, norma: q.norma, version: q.version});
  }
  const t0 = performance.now(), top = api.buscar(frags, q.pregunta);
  emitir({paso: "recuperar", ms: Math.round(performance.now() - t0), fragmentos: top.map((f, i) => ({...f, bm25: i + 1, vector: null}))});
  if (!top.length) { emitir({paso: "validar", estado: "sin_evidencia", salida: {}}); return; }
  const t1 = performance.now();
  const bruto = await generar([
    {role: "system", content: "Respondes preguntas técnicas SOLO con los fragmentos dados. Si ninguno contiene la respuesta exacta, devuelve hay_evidencia=false y deja los demás campos vacíos. Si la contiene, da el id del fragmento, una cita copiada literalmente de él y una respuesta breve y obligatoria." +
      (q.idioma === "en" ? " Answer in English; copy the quote verbatim in its original language." : "")},
    {role: "user", content: `Fragmentos:\n${top.map(f => `[${f.id}] ${f.texto}`).join("\n")}\n\nPregunta: ${q.pregunta}`}], ESQUEMA_RAG, emitir, vigente);
  if (!vigente()) return;
  emitir({paso: "generar", ms: Math.round(performance.now() - t1), modelo: activo});
  const salida = json(bruto);
  emitir({paso: "validar", estado: api.validar(salida, top), salida: salida || {}});
};

/* ---------- datos: el código calcula, el modelo redacta ---------- */
let agregados = null;
api.resumir = d => {
  const sec = {}, anio = {};
  for (const h of d.hechos) { if (h.anio === "?") continue;
    const s = sec[h.sector] ||= {n: 0, vol: 0, os: 0, oc: 0, u: 0, bs: 0, bc: 0};
    s.n += h.n; s.vol += h.vol; s.os += h.of_sum; s.oc += h.of_cnt; s.u += h.unico; s.bs += h.baja_sum; s.bc += h.baja_cnt; }
  for (const h of d.hechos_tot) { if (h.anio === "?") continue;
    const a = anio[h.anio] ||= {n: 0, vol: 0}; a.n += h.n; a.vol += h.vol; }
  const r1 = x => Math.round(x * 10) / 10;
  const por_sector = Object.entries(sec).map(([sector, s]) => ({sector, n: s.n, volumen_eur: Math.round(s.vol),
    competencia_media: r1(s.os / s.oc), pct_oferta_unica: r1(100 * s.u / s.oc), baja_media_pct: r1(s.bs / s.bc)}));
  const por_anio = Object.entries(anio).sort().map(([a, v]) => ({anio: a, n: v.n, volumen_eur: Math.round(v.vol)}));
  return {por_sector, por_anio, total: por_anio.reduce((a, x) => a + x.n, 0)};
};
const MEDIDAS = {competencia_media: "licitadores por adjudicación", pct_oferta_unica: "% de adjudicaciones con oferta única", baja_media_pct: "baja media en %", n: "número de licitaciones", volumen_eur: "volumen en euros"};
/* cifras de la respuesta que no aparecen en lo que se le dio al modelo */
const cifras = s => (String(s).replace(/(\d)[.,  ](?=\d{3}(\D|$))/g, "$1").match(/\d+([.,]\d+)?/g) || []).map(x => Number(x.replace(",", ".")));
api.sinRespaldo = (respuesta, contexto) => { const ok = new Set(cifras(contexto)); return cifras(respuesta).filter(x => !ok.has(x)); };

api.datos = async (q, emitir, vigente, base) => {
  const t0 = performance.now();
  agregados ||= api.resumir(await (await fetch(base + "vivo/datos_agregados.json")).json());
  const r = agregados;
  emitir({paso: "calcular", ms: Math.round(performance.now() - t0), licitaciones: r.total, sectores: r.por_sector.length});
  const extremos = Object.entries(MEDIDAS).map(([k, nombre]) => { const o = [...r.por_sector].sort((a, b) => a[k] - b[k]);
    return `${nombre}: mínimo ${o[0].sector} (${o[0][k]}), máximo ${o[o.length - 1].sector} (${o[o.length - 1][k]})`; }).join("\n");
  const contexto = `Licitaciones totales: ${r.total}\nMáximos y mínimos por sector (ya calculados):\n${extremos}`;
  const esquema = {type: "object", required: ["respuesta", "dataset", "medida"], properties: {respuesta: {type: "string"},
    dataset: {type: "string", enum: ["por_sector", "por_anio", "ninguno"]}, medida: {type: "string", enum: Object.keys(MEDIDAS)}}};
  const t1 = performance.now();
  const bruto = await generar([
    {role: "system", content: "Eres analista de un panel de licitaciones. Contesta en una frase usando SOLO estas cifras. 'competencia' se mide en licitadores por adjudicación: menos licitadores es menos competencia. Indica en dataset y medida qué gráfico ayuda (ninguno si no hace falta; por_anio solo admite n o volumen_eur)." +
      (q.idioma === "en" ? " Answer in English." : " Responde en español.") + "\n\n" + contexto},
    {role: "user", content: q.pregunta}], esquema, emitir, vigente);
  if (!vigente()) return;
  emitir({paso: "generar", ms: Math.round(performance.now() - t1), modelo: activo});
  const s = json(bruto);
  if (!s) { emitir({paso: "error", texto: "El modelo no devolvió un JSON completo. Prueba de nuevo o usa el modelo grande."}); return; }
  const filas = r[s.dataset] || [], eje = s.dataset === "por_sector" ? "sector" : "anio";
  const datos = filas.filter(f => f[s.medida] !== undefined).map(f => [f[eje], f[s.medida]]);
  if (eje === "sector") datos.sort((a, b) => b[1] - a[1]);
  emitir({paso: "respuesta", texto: s.respuesta, accion: s.dataset === "ninguno" ? null : {tipo: "chart", dataset: s.dataset, medida: s.medida},
    grafico: datos.length ? {titulo: MEDIDAS[s.medida], medida: s.medida, datos} : null, sinRespaldo: api.sinRespaldo(s.respuesta, contexto + " " + q.pregunta)});
};
return api;
})();
