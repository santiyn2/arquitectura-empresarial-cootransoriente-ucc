"use strict";
/* Portal web Cootransoriente Tayrona — taquilla y despacho.
   Sin dependencias ni paso de compilación. El token vive en sessionStorage
   (se borra al cerrar la pestaña). Todo texto del servidor se escapa. */

const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pesos = (n) => new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(n);

let sesion = null;          // {token, nombre, rol, usuario}
let asientoElegido = null;
let qrUrlActual = null;

function guardar(clave, valor) { try { sessionStorage.setItem(clave, valor); } catch (_) {} }
function leer(clave) { try { return sessionStorage.getItem(clave); } catch (_) { return null; } }
function borrar(clave) { try { sessionStorage.removeItem(clave); } catch (_) {} }

function aviso(texto, malo = false) {
  const p = $("mensaje");
  p.textContent = texto;
  p.className = "aviso" + (malo ? " mal" : "");
  p.hidden = !texto;
  if (texto) window.scrollTo({ top: 0, behavior: "smooth" });
}

function detalleError(d) {
  if (Array.isArray(d)) return d.map((e) => `${(e.loc || []).slice(1).join(".")}: ${e.msg}`).join(" · ");
  return d || "Error desconocido";
}

async function api(ruta, opciones = {}) {
  const cab = { ...(opciones.headers || {}) };
  if (opciones.json !== undefined) cab["Content-Type"] = "application/json";
  if (sesion) cab.Authorization = `Bearer ${sesion.token}`;
  const r = await fetch(ruta, {
    method: opciones.method || (opciones.json !== undefined ? "POST" : "GET"),
    headers: cab,
    body: opciones.json !== undefined ? JSON.stringify(opciones.json) : undefined,
  });
  if (r.status === 401 && sesion && ruta !== "/api/auth/login") {
    cerrarSesion("Su sesión expiró. Ingrese de nuevo.");
    throw new Error("Sesión expirada");
  }
  if (opciones.blob) {
    if (!r.ok) throw new Error(`Error ${r.status}`);
    return r.blob();
  }
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(detalleError(datos.detail));
  return datos;
}

/* ---------- sesión ---------- */
function mostrarLogin() {
  $("vista-login").hidden = false;
  $("app").hidden = true;
}

function cerrarSesion(msg = "") {
  sesion = null;
  borrar("ct_sesion");
  mostrarLogin();
  $("error-login").textContent = msg;
}

$("form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("error-login").textContent = "";
  const f = new FormData(e.target);
  try {
    const d = await api("/api/auth/login", { json: { usuario: f.get("usuario"), password: f.get("password") } });
    sesion = { token: d.access_token, nombre: d.nombre, rol: d.rol, usuario: d.usuario };
    guardar("ct_sesion", JSON.stringify(sesion));
    e.target.reset();
    iniciarApp();
  } catch (err) {
    $("error-login").textContent = err.message;
  }
});
$("salir").addEventListener("click", () => cerrarSesion());

/* ---------- navegación por rol ---------- */
const SECCIONES = {
  venta:     { texto: "Vender tiquete", roles: ["TAQUILLERO", "ADMIN_DESPACHO"], cargar: cargarVenta },
  viajes:    { texto: "Viajes y despacho", roles: ["ADMIN_DESPACHO"], cargar: cargarViajes },
  flota:     { texto: "Flota", roles: ["ADMIN_DESPACHO"], cargar: cargarFlota },
  usuarios:  { texto: "Usuarios", roles: ["ADMIN_DESPACHO"], cargar: cargarUsuarios },
  auditoria: { texto: "Auditoría", roles: ["ADMIN_DESPACHO"], cargar: cargarAuditoria },
};

function iniciarApp() {
  $("vista-login").hidden = true;
  $("app").hidden = false;
  $("quien").textContent = `${sesion.nombre} (${sesion.rol})`;
  const menu = $("menu");
  menu.replaceChildren();
  const visibles = Object.entries(SECCIONES).filter(([, s]) => s.roles.includes(sesion.rol));
  if (!visibles.length) {
    aviso("Su rol (CONDUCTOR) usa la app móvil: /movil/", false);
  }
  visibles.forEach(([clave, s]) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = s.texto;
    b.dataset.clave = clave;
    b.addEventListener("click", () => ir(clave));
    menu.appendChild(b);
  });
  if (visibles.length) ir(visibles[0][0]);
}

async function ir(clave) {
  aviso("");
  Object.keys(SECCIONES).forEach((k) => { $(`vista-${k}`).hidden = k !== clave; });
  document.querySelectorAll("#menu button").forEach((b) =>
    b.setAttribute("aria-current", b.dataset.clave === clave ? "page" : "false"));
  try { await SECCIONES[clave].cargar(); } catch (err) { aviso(err.message, true); }
}

/* ---------- tablas ---------- */
function pintarTabla(id, columnas, filas) {
  const t = $(id);
  const cab = `<thead><tr>${columnas.map((c) => `<th>${esc(c.t)}</th>`).join("")}</tr></thead>`;
  const cuerpo = filas.length
    ? filas.map((f, i) => `<tr>${columnas.map((c) => `<td>${c.html ? c.html(f, i) : esc(c.v(f))}</td>`).join("")}</tr>`).join("")
    : `<tr><td colspan="${columnas.length}" class="suave">Sin registros</td></tr>`;
  t.innerHTML = `${cab}<tbody>${cuerpo}</tbody>`;
}

/* ---------- venta ---------- */
let privacidadCargada = false;

async function cargarVenta() {
  if (!privacidadCargada) {
    const p = await api("/api/privacidad");
    $("aviso-texto").textContent = `${p.aviso_privacidad.trim()}\n\nContacto: ${p.canal_contacto}`;
    privacidadCargada = true;
  }
  const { viajes } = await api("/api/viajes?estado=programado");
  const sel = $("venta-viaje");
  const previo = sel.value;
  sel.innerHTML = viajes.length
    ? viajes.map((v) => `<option value="${esc(v.id)}">${esc(v.ruta)} · ${esc(v.salida_programada.replace("T", " "))} · ${esc(v.placa)} · ${esc(pesos(v.tarifa))}</option>`).join("")
    : `<option value="">No hay viajes programados</option>`;
  if (previo && viajes.some((v) => String(v.id) === previo)) sel.value = previo;
  await pintarAsientos();
}

async function pintarAsientos() {
  const caja = $("asientos");
  caja.replaceChildren();
  asientoElegido = null;
  const id = $("venta-viaje").value;
  if (!id) return;
  const v = await api(`/api/viajes/${encodeURIComponent(id)}`);
  const ocupados = new Set(v.asientos_ocupados);
  for (let n = 1; n <= v.capacidad; n++) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = String(n);
    b.setAttribute("role", "radio");
    b.setAttribute("aria-checked", "false");
    b.disabled = ocupados.has(String(n));
    b.setAttribute("aria-label", `Asiento ${n}${b.disabled ? " ocupado" : ""}`);
    b.addEventListener("click", () => {
      asientoElegido = String(n);
      caja.querySelectorAll("button").forEach((x) => x.setAttribute("aria-checked", String(x === b)));
    });
    caja.appendChild(b);
  }
}
$("venta-viaje").addEventListener("change", () => pintarAsientos().catch((e) => aviso(e.message, true)));
$("venta-menor").addEventListener("change", (e) => {
  $("fila-representante").hidden = !e.target.checked;
  $("venta-representante").required = e.target.checked;
});

$("form-venta").addEventListener("submit", async (e) => {
  e.preventDefault();
  aviso("");
  if (!$("venta-viaje").value) return aviso("Seleccione un viaje.", true);
  if (!asientoElegido) return aviso("Seleccione un asiento.", true);
  if (!$("venta-autoriza").checked) return aviso("Sin la autorización del pasajero (Ley 1581) no se puede emitir el tiquete.", true);
  const cuerpo = {
    viaje_id: Number($("venta-viaje").value),
    pasajero_nombre: $("venta-nombre").value,
    documento: $("venta-documento").value,
    es_menor: $("venta-menor").checked,
    asiento: asientoElegido,
    autorizacion_ley1581: true,
  };
  if (cuerpo.es_menor) cuerpo.representante_documento = $("venta-representante").value;
  if ($("venta-pago").value) cuerpo.medio_pago = $("venta-pago").value;
  try {
    const t = await api("/api/tiquetes", { json: cuerpo });
    await mostrarTiquete(t);
    e.target.reset();
    $("fila-representante").hidden = true;
    $("venta-autoriza").checked = false;       // la autorización se da por cada pasajero
    await pintarAsientos();
    aviso(`Tiquete #${t.id} emitido.`);
  } catch (err) {
    aviso(err.message, true);
  }
});

async function mostrarTiquete(t) {
  $("tiquete-datos").innerHTML =
    `<p><strong>Tiquete #${esc(t.id)}</strong><br>${esc(t.pasajero_nombre)} · doc. ${esc(t.documento)}<br>` +
    `${esc(t.ruta)} · asiento ${esc(t.asiento)} · ${esc(pesos(t.valor))}</p>`;
  const blob = await api(`/api/tiquetes/${t.id}/qr.svg`, { blob: true });   // lleva el token: no se puede abrir como <img src>
  if (qrUrlActual) URL.revokeObjectURL(qrUrlActual);
  qrUrlActual = URL.createObjectURL(blob);
  $("tiquete-qr").src = qrUrlActual;
  $("resultado-tiquete").hidden = false;
}
$("imprimir").addEventListener("click", () => window.print());

/* ---------- flota ---------- */
async function cargarFlota() {
  const { vehiculos } = await api("/api/vehiculos");
  pintarTabla("tabla-vehiculos", [
    { t: "Placa", v: (x) => x.placa }, { t: "Capacidad", v: (x) => x.capacidad },
    { t: "Estado", v: (x) => (x.activo ? "Activo" : "Inactivo") },
  ], vehiculos);
}
$("form-vehiculo").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/vehiculos", { json: { placa: $("veh-placa").value, capacidad: Number($("veh-capacidad").value) } });
    e.target.reset();
    aviso("Vehículo agregado.");
    await cargarFlota();
  } catch (err) { aviso(err.message, true); }
});

/* ---------- usuarios ---------- */
async function cargarUsuarios() {
  const { usuarios } = await api("/api/admin/usuarios");
  pintarTabla("tabla-usuarios", [
    { t: "Usuario", v: (x) => x.usuario }, { t: "Nombre", v: (x) => x.nombre },
    { t: "Rol", v: (x) => x.rol }, { t: "Activo", v: (x) => (x.activo ? "Sí" : "No") },
  ], usuarios);
}
$("form-usuario").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/admin/usuarios", { json: {
      usuario: $("usr-usuario").value, nombre: $("usr-nombre").value,
      password: $("usr-clave").value, rol: $("usr-rol").value } });
    e.target.reset();
    aviso("Usuario creado.");
    await cargarUsuarios();
  } catch (err) { aviso(err.message, true); }
});

/* ---------- auditoría ---------- */
async function cargarAuditoria() {
  const { registros } = await api("/api/admin/auditoria");
  pintarTabla("tabla-auditoria", [
    { t: "#", v: (x) => x.id }, { t: "Fecha (UTC)", v: (x) => x.timestamp },
    { t: "Acción", v: (x) => x.accion }, { t: "Usuario", v: (x) => `${x.usuario} (${x.rol})` },
    { t: "Detalle", v: (x) => x.detalle },
  ], registros.slice().reverse());
}

/* ---------- viajes, despacho, manifiesto, conciliación ---------- */
async function cargarViajes() {
  const [{ vehiculos }, { usuarios }, { viajes }] = await Promise.all([
    api("/api/vehiculos"), api("/api/admin/usuarios?rol=CONDUCTOR"), api("/api/viajes"),
  ]);
  $("viaje-vehiculo").innerHTML = vehiculos.filter((v) => v.activo)
    .map((v) => `<option value="${esc(v.id)}">${esc(v.placa)} (${esc(v.capacidad)})</option>`).join("");
  $("viaje-conductor").innerHTML = usuarios.filter((u) => u.activo)
    .map((u) => `<option value="${esc(u.usuario)}">${esc(u.nombre)}</option>`).join("");
  const clase = { programado: "med", despachado: "ok", cerrado: "" };
  pintarTabla("tabla-viajes", [
    { t: "#", v: (v) => v.id }, { t: "Ruta", v: (v) => v.ruta },
    { t: "Salida", v: (v) => v.salida_programada.replace("T", " ") },
    { t: "Vehículo", v: (v) => `${v.placa}` }, { t: "Conductor", v: (v) => v.conductor_usuario },
    { t: "Tarifa", v: (v) => pesos(v.tarifa) },
    { t: "Tiquetes", v: (v) => `${v.tiquetes}/${v.capacidad}` },
    { t: "Abordaron", v: (v) => v.abordajes },
    { t: "Estado", html: (v) => `<span class="etiqueta ${clase[v.estado] || ""}">${esc(v.estado)}</span>` },
    { t: "Acciones", html: (v) =>
      `<button class="sec" data-ver="${esc(v.id)}">Ver</button> ` +
      (v.estado === "programado" ? `<button data-despachar="${esc(v.id)}">Despachar</button>` : "") +
      (v.estado === "despachado" ? `<button class="peligro" data-cerrar="${esc(v.id)}">Cerrar</button>` : "") },
  ], viajes);
}

$("form-viaje").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/viajes", { json: {
      ruta: $("viaje-ruta").value, vehiculo_id: Number($("viaje-vehiculo").value),
      conductor_usuario: $("viaje-conductor").value, salida_programada: $("viaje-salida").value,
      tarifa: Number($("viaje-tarifa").value) } });
    aviso("Viaje programado.");
    await cargarViajes();
  } catch (err) { aviso(err.message, true); }
});

$("tabla-viajes").addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  try {
    if (b.dataset.ver) return await verDetalle(b.dataset.ver);
    if (b.dataset.despachar) {
      if (!confirm("Al despachar se genera el manifiesto y ya no se venden más tiquetes. ¿Continuar?")) return;
      await api(`/api/viajes/${b.dataset.despachar}/despacho`, { method: "POST" });
      aviso("Viaje despachado y manifiesto generado.");
      await cargarViajes();
      return await verDetalle(b.dataset.despachar);
    }
    if (b.dataset.cerrar) {
      if (!confirm("¿Cerrar el viaje? Ya no se registrarán pagos.")) return;
      await api(`/api/viajes/${b.dataset.cerrar}/cierre`, { method: "POST" });
      aviso("Viaje cerrado.");
      await cargarViajes();
      return await verDetalle(b.dataset.cerrar);
    }
  } catch (err) { aviso(err.message, true); }
});

async function verDetalle(id) {
  const caja = $("detalle");
  const v = await api(`/api/viajes/${id}`);
  let html = `<h3>Viaje #${esc(v.id)} · ${esc(v.ruta)}</h3>` +
    `<p>${esc(v.placa)} · salida ${esc(v.salida_programada.replace("T", " "))} · estado <strong>${esc(v.estado)}</strong></p>`;
  if (v.estado === "programado") {
    html += `<p>Asientos vendidos: ${esc(v.asientos_ocupados.join(", ") || "ninguno")}. El manifiesto se genera al despachar.</p>`;
  } else {
    const m = await api(`/api/viajes/${id}/manifiesto`);
    html += `<h4>Manifiesto digital (${esc(m.total_pasajeros)} pasajeros)</h4>` +
      `<p class="suave">Generado por ${esc(m.generado_por)} el ${esc(m.fecha_generacion)}</p>` +
      `<div class="tabla-caja"><table><thead><tr><th>Asiento</th><th>Pasajero</th><th>Documento</th><th>Menor</th></tr></thead><tbody>` +
      m.pasajeros.map((p) => `<tr><td>${esc(p.asiento)}</td><td>${esc(p.pasajero_nombre)}</td><td>${esc(p.documento)}</td><td>${p.es_menor ? "Sí" : "No"}</td></tr>`).join("") +
      `</tbody></table></div>`;
    const c = await api(`/api/viajes/${id}/conciliacion`);
    const cls = { cuadra: "ok", sobrante: "med", faltante: "mal" }[c.resultado];
    html += `<h4>Conciliación de recaudo <span class="etiqueta ${cls}">${esc(c.resultado)}</span></h4>` +
      `<div class="tabla-caja"><table><tbody>` +
      `<tr><th>Valor esperado (tiquetes)</th><td>${esc(pesos(c.valor_esperado))}</td></tr>` +
      `<tr><th>Recaudado (efectivo / digital)</th><td>${esc(pesos(c.recaudado_total))} (${esc(pesos(c.recaudado_efectivo))} / ${esc(pesos(c.recaudado_digital))})</td></tr>` +
      `<tr><th>Diferencia</th><td>${esc(pesos(c.diferencia))}</td></tr>` +
      `<tr><th>Abordajes validados / tiquetes</th><td>${esc(c.abordajes_validados)} / ${esc(c.tiquetes_emitidos)}</td></tr>` +
      `<tr><th>Pagos sin tiquete asociado</th><td>${esc(c.pagos_sin_tiquete)}</td></tr></tbody></table></div>`;
  }
  caja.innerHTML = html;
  caja.hidden = false;
  caja.scrollIntoView({ behavior: "smooth" });
}

/* ---------- arranque ---------- */
(function arrancar() {
  const previa = leer("ct_sesion");
  if (previa) {
    try { sesion = JSON.parse(previa); iniciarApp(); return; } catch (_) { borrar("ct_sesion"); }
  }
  mostrarLogin();
})();
