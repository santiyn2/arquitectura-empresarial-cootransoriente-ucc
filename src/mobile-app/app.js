"use strict";
/* App móvil Cootransoriente (PWA) — ayudante/conductor.
   Funciona sin conexión: el manifiesto del viaje se descarga antes de salir,
   los QR se validan contra esa copia y los abordajes/pagos quedan en una cola
   local que se sincroniza sola al volver la señal. Reenviar es seguro: cada
   registro lleva un id_cliente y el servidor no duplica. */

const CLAVE = "ct_movil_v1";
const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pesos = (n) => new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(n);

/* ---------- estado persistente ---------- */
let memoria = null; // respaldo si localStorage no está disponible
function estadoVacio() {
  return { sesion: null, viajes: [], manifiestos: {}, vistos: {}, cola_abordajes: [], cola_pagos: [], viaje_actual: null };
}
function cargar() {
  try { const t = localStorage.getItem(CLAVE); if (t) return { ...estadoVacio(), ...JSON.parse(t) }; } catch (_) {}
  return memoria || estadoVacio();
}
let S = cargar();
function guardar() {
  memoria = S;
  try { localStorage.setItem(CLAVE, JSON.stringify(S)); } catch (_) {}
  pintarContador();
}

function nuevoId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, "0")).join("");
}

function aviso(texto, malo = false) {
  const p = $("mensaje");
  p.textContent = texto;
  p.className = "aviso" + (malo ? " mal" : "");
  p.hidden = !texto;
}

/* ---------- red ---------- */
class SinRed extends Error {}
async function api(ruta, json) {
  const cab = {};
  if (json !== undefined) cab["Content-Type"] = "application/json";
  if (S.sesion) cab.Authorization = `Bearer ${S.sesion.token}`;
  let r;
  try {
    r = await fetch(ruta, { method: json !== undefined ? "POST" : "GET", headers: cab,
      body: json !== undefined ? JSON.stringify(json) : undefined });
  } catch (_) { throw new SinRed("Sin conexión"); }
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) {
    const d = Array.isArray(datos.detail) ? datos.detail.map((e) => e.msg).join(" · ") : datos.detail;
    const err = new Error(d || `Error ${r.status}`);
    err.status = r.status;
    throw err;
  }
  return datos;
}

function pintarRed() {
  const e = $("estado-red");
  e.textContent = navigator.onLine ? "En línea" : "Sin conexión";
  e.className = "red" + (navigator.onLine ? "" : " off");
}
window.addEventListener("online", () => { pintarRed(); sincronizar(true); });
window.addEventListener("offline", pintarRed);

/* ---------- sesión ---------- */
function mostrar() {
  const hay = !!S.sesion;
  $("vista-login").hidden = hay;
  $("app").hidden = !hay;
  if (hay) {
    $("quien").textContent = S.sesion.nombre;
    pintarRed();
    pintarViajes();
    pintarContador();
  }
}

$("form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("error-login").textContent = "";
  const f = new FormData(e.target);
  try {
    const d = await api("/api/auth/login", { usuario: f.get("usuario"), password: f.get("password") });
    if (d.rol !== "CONDUCTOR") { $("error-login").textContent = "Esta app es para ayudantes/conductores (rol CONDUCTOR)."; return; }
    S.sesion = { token: d.access_token, nombre: d.nombre, usuario: d.usuario };
    guardar();
    e.target.reset();
    mostrar();
    await refrescarViajes();
    sincronizar(true);
  } catch (err) {
    $("error-login").textContent = err instanceof SinRed ? "Necesita señal para iniciar sesión." : err.message;
  }
});

$("salir").addEventListener("click", () => {
  const pendientes = S.cola_abordajes.length + S.cola_pagos.length;
  if (pendientes && !confirm(`Hay ${pendientes} registros sin sincronizar. Se conservan en este teléfono, pero necesita volver a iniciar sesión con señal para enviarlos. ¿Salir?`)) return;
  S.sesion = null;
  guardar();
  mostrar();
});

/* ---------- pestañas ---------- */
document.querySelectorAll("#pestanas button").forEach((b) => b.addEventListener("click", () => {
  const v = b.dataset.v;
  ["viaje", "escanear", "pagos", "cola"].forEach((k) => { $(`v-${k}`).hidden = k !== v; });
  document.querySelectorAll("#pestanas button").forEach((x) => x.setAttribute("aria-current", x === b ? "page" : "false"));
  if (v !== "escanear") detenerCamara();
  if (v === "cola") pintarCola();
  aviso("");
}));

/* ---------- viajes y manifiesto ---------- */
function pintarViajes() {
  const sel = $("sel-viaje");
  sel.innerHTML = S.viajes.length
    ? S.viajes.map((v) => `<option value="${esc(v.id)}">#${esc(v.id)} · ${esc(v.ruta)} · ${esc(v.salida_programada.replace("T", " "))} · ${esc(v.placa)}</option>`).join("")
    : `<option value="">Sin viajes despachados</option>`;
  if (S.viaje_actual && S.viajes.some((v) => v.id === S.viaje_actual)) sel.value = String(S.viaje_actual);
  else S.viaje_actual = S.viajes.length ? S.viajes[0].id : null;
  pintarResumen();
}
$("sel-viaje").addEventListener("change", (e) => { S.viaje_actual = Number(e.target.value) || null; guardar(); pintarResumen(); });

async function refrescarViajes() {
  try {
    const d = await api("/api/viajes?estado=despachado");
    S.viajes = d.viajes;
    guardar();
    pintarViajes();
  } catch (err) {
    aviso(err instanceof SinRed ? "Sin señal: se muestran los viajes guardados." : err.message, !(err instanceof SinRed));
  }
}
$("btn-refrescar").addEventListener("click", refrescarViajes);

$("btn-descargar").addEventListener("click", async () => {
  if (!S.viaje_actual) return aviso("No hay viaje seleccionado.", true);
  try {
    S.manifiestos[S.viaje_actual] = await api(`/api/viajes/${S.viaje_actual}/manifiesto`);
    guardar();
    pintarResumen();
    aviso("Manifiesto descargado. Ya puede validar tiquetes sin señal.");
  } catch (err) { aviso(err instanceof SinRed ? "Necesita señal para descargar el manifiesto." : err.message, true); }
});

function pintarResumen() {
  const caja = $("resumen-viaje");
  const id = S.viaje_actual;
  if (!id) { caja.textContent = "Elija un viaje despachado."; return; }
  const m = S.manifiestos[id];
  if (!m) { caja.innerHTML = "<strong>Manifiesto no descargado.</strong><br>Descárguelo con señal antes de salir."; return; }
  const vistos = Object.keys(S.vistos[id] || {}).length;
  caja.innerHTML = `<strong>${esc(m.ruta)}</strong><br>${esc(m.placa)} · salida ${esc(m.salida_programada.replace("T", " "))}<br>` +
    `Pasajeros: <strong>${esc(m.total_pasajeros)}</strong> · Abordaron: <strong>${vistos}</strong> · Faltan: <strong>${m.total_pasajeros - vistos}</strong>`;
}

/* ---------- validación de QR ---------- */
function resultado(clase, html) { const r = $("resultado-escaneo"); r.className = `resultado ${clase}`; r.innerHTML = html; }

function validar(codigoCrudo) {
  const codigo = String(codigoCrudo || "").trim();
  if (!codigo) return;
  const id = S.viaje_actual;
  const m = id && S.manifiestos[id];
  if (!m) return resultado("mal", "<strong>Sin manifiesto.</strong> Elija un viaje y descargue su manifiesto.");
  const p = m.pasajeros.find((x) => x.codigo_qr === codigo);
  if (!p) return resultado("mal", "<strong>✖ NO VÁLIDO</strong><br>Este código no está en el manifiesto de este viaje.");
  S.vistos[id] = S.vistos[id] || {};
  if (S.vistos[id][codigo]) return resultado("med", `<strong>⚠ YA ABORDÓ</strong><br>${esc(p.pasajero_nombre)} · asiento ${esc(p.asiento)}`);
  S.vistos[id][codigo] = true;
  S.cola_abordajes.push({ id_cliente: nuevoId(), viaje_id: id, codigo_qr: codigo, fecha_escaneo: new Date().toISOString(), nombre: p.pasajero_nombre, asiento: p.asiento });
  guardar();
  pintarResumen();
  resultado("ok", `<strong>✔ VÁLIDO</strong><br>${esc(p.pasajero_nombre)} · asiento ${esc(p.asiento)}${p.es_menor ? "<br><strong>Menor de edad</strong>" : ""}`);
  if (navigator.vibrate) navigator.vibrate(120);
  sincronizar(true);
}

$("form-manual").addEventListener("submit", (e) => { e.preventDefault(); validar($("codigo-manual").value); $("codigo-manual").value = ""; });

/* ---------- cámara ---------- */
let flujo = null, temporizador = null, ultimo = { codigo: "", t: 0 };

async function iniciarCamara() {
  if (!("BarcodeDetector" in window)) {
    return aviso("Este teléfono no lee QR desde el navegador. Use el código manual.", true);
  }
  try {
    const detector = new BarcodeDetector({ formats: ["qr_code"] });
    flujo = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
    const v = $("video");
    v.srcObject = flujo;
    await v.play();
    $("camara-caja").hidden = false;
    temporizador = setInterval(async () => {
      try {
        const hallados = await detector.detect(v);
        if (!hallados.length) return;
        const c = hallados[0].rawValue;
        const ahora = Date.now();
        if (c === ultimo.codigo && ahora - ultimo.t < 3000) return;   // evita leer dos veces el mismo QR
        ultimo = { codigo: c, t: ahora };
        validar(c);
      } catch (_) { /* fotograma sin QR */ }
    }, 350);
  } catch (err) {
    aviso("No se pudo abrir la cámara (permiso denegado o no disponible). Use el código manual.", true);
  }
}
function detenerCamara() {
  clearInterval(temporizador); temporizador = null;
  if (flujo) { flujo.getTracks().forEach((t) => t.stop()); flujo = null; }
  $("camara-caja").hidden = true;
}
$("btn-camara").addEventListener("click", iniciarCamara);
$("btn-detener").addEventListener("click", detenerCamara);

/* ---------- pagos ---------- */
$("form-pago").addEventListener("submit", (e) => {
  e.preventDefault();
  if (!S.viaje_actual) return aviso("Elija un viaje primero.", true);
  S.cola_pagos.push({ id_cliente: nuevoId(), viaje_id: S.viaje_actual, valor: Number($("pago-valor").value),
    medio: $("pago-medio").value, fecha: new Date().toISOString() });
  guardar();
  e.target.reset();
  aviso("Pago guardado. Se enviará cuando haya señal.");
  sincronizar(true);
});

/* ---------- cola y sincronización ---------- */
function pintarContador() {
  const n = S.cola_abordajes.length + S.cola_pagos.length;
  const c = $("contador");
  if (c) { c.textContent = String(n); c.hidden = n === 0; }
}

function pintarCola() {
  const caja = $("lista-cola");
  const items = [
    ...S.cola_abordajes.map((a) => `<div class="item ${a.error ? "mal" : ""}">Abordaje · ${esc(a.nombre)} (asiento ${esc(a.asiento)}) · viaje #${esc(a.viaje_id)}${a.error ? `<br><strong>${esc(a.error)}</strong> <button class="chico sec" data-descartar-a="${esc(a.id_cliente)}">Descartar</button>` : ""}</div>`),
    ...S.cola_pagos.map((p) => `<div class="item ${p.error ? "mal" : ""}">Pago · ${esc(pesos(p.valor))} ${esc(p.medio)} · viaje #${esc(p.viaje_id)}${p.error ? `<br><strong>${esc(p.error)}</strong> <button class="chico sec" data-descartar-p="${esc(p.id_cliente)}">Descartar</button>` : ""}</div>`),
  ];
  caja.innerHTML = items.length ? items.join("") : "<p class='suave'>Todo sincronizado ✔</p>";
}
$("lista-cola").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.descartarA) S.cola_abordajes = S.cola_abordajes.filter((a) => a.id_cliente !== b.dataset.descartarA);
  if (b.dataset.descartarP) S.cola_pagos = S.cola_pagos.filter((p) => p.id_cliente !== b.dataset.descartarP);
  guardar();
  pintarCola();
});

let sincronizando = false;
async function sincronizar(silencioso = false) {
  if (sincronizando || !S.sesion || !(S.cola_abordajes.length || S.cola_pagos.length)) return;
  if (!navigator.onLine) { if (!silencioso) aviso("Sin señal: queda pendiente.", true); return; }
  sincronizando = true;
  let enviados = 0, rechazados = 0;
  try {
    // 1) abordajes agrupados por viaje
    const porViaje = {};
    S.cola_abordajes.forEach((a) => (porViaje[a.viaje_id] = porViaje[a.viaje_id] || []).push(a));
    for (const [viaje, lista] of Object.entries(porViaje)) {
      try {
        const r = await api("/api/abordajes/lote", { viaje_id: Number(viaje), abordajes: lista.map((a) => ({ id_cliente: a.id_cliente, codigo_qr: a.codigo_qr, fecha_escaneo: a.fecha_escaneo })) });
        const por = Object.fromEntries(r.resultados.map((x) => [x.id_cliente, x]));
        S.cola_abordajes = S.cola_abordajes.filter((a) => {
          const x = por[a.id_cliente];
          if (!x) return true;
          if (x.estado === "rechazado") { a.error = `Rechazado: ${x.motivo}`; rechazados++; return true; }
          enviados++; return false;
        });
      } catch (err) {
        if (err instanceof SinRed) throw err;
        if (err.status === 401) throw err;
        lista.forEach((a) => { const q = S.cola_abordajes.find((z) => z.id_cliente === a.id_cliente); if (q) q.error = err.message; });
      }
    }
    // 2) pagos uno a uno
    for (const p of [...S.cola_pagos]) {
      try {
        await api("/api/pagos", { viaje_id: p.viaje_id, valor: p.valor, medio: p.medio, id_cliente: p.id_cliente });
        S.cola_pagos = S.cola_pagos.filter((z) => z.id_cliente !== p.id_cliente);
        enviados++;
      } catch (err) {
        if (err instanceof SinRed || err.status === 401) throw err;
        p.error = err.message;
      }
    }
    guardar();
    if (!silencioso || enviados || rechazados) {
      aviso(rechazados ? `Sincronizado con ${rechazados} rechazado(s): revise Pendientes.` : `Sincronizado: ${enviados} registro(s) enviados.`, rechazados > 0);
    }
  } catch (err) {
    guardar();
    if (err.status === 401) aviso("Su sesión expiró. Salga e inicie sesión con señal para enviar lo pendiente.", true);
    else if (!silencioso) aviso("No hay señal estable: queda pendiente.", true);
  } finally {
    sincronizando = false;
    pintarCola();
    pintarContador();
  }
}
$("btn-sync").addEventListener("click", () => sincronizar(false));
setInterval(() => sincronizar(true), 60000);

/* ---------- arranque ---------- */
mostrar();
if (S.sesion && navigator.onLine) refrescarViajes();
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
