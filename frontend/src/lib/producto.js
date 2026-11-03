/**
 * Autocompletado del producto desde el enlace al crear un pool (Iteración 2).
 *
 * Módulo puro (sin runes ni fetch). `POST /pools/previsualizar-enlace/`
 * devuelve `{encontrado, nombre_producto, precio_unitario, imagen, descripcion}`;
 * acá se decide qué campos del formulario se pisan y se hacen las cuentas de
 * precio total ⇄ precio unitario.
 */

const LARGO_TITULO = 200;

/** Redondeo a centavos como string para un `<input type="number">`. */
function centavos(n) {
	return (Math.round(n * 100) / 100).toFixed(2);
}

/** Precio total = unitario × cantidad, o '' si falta alguno. */
export function precioTotal(unitario, cantidad) {
	const u = Number(unitario);
	const c = Number(cantidad);
	if (!unitario || !cantidad || !Number.isFinite(u) || !Number.isFinite(c) || u <= 0 || c <= 0) {
		return '';
	}
	return centavos(u * c);
}

/** Precio unitario = total ÷ cantidad, o '' si falta alguno. */
export function precioUnitarioDesdeTotal(total, cantidad) {
	const t = Number(total);
	const c = Number(cantidad);
	if (!total || !cantidad || !Number.isFinite(t) || !Number.isFinite(c) || t <= 0 || c <= 0) {
		return '';
	}
	return centavos(t / c);
}

/**
 * Valores a escribir en el formulario a partir de la vista previa.
 *
 * Nombre y precio vienen del enlace recién pegado, así que se pisan. Título y
 * descripción son del usuario: solo se completan si están vacíos.
 */
export function camposDesdeVistaPrevia(vista, actuales = {}) {
	if (!vista?.encontrado) return {};
	const campos = {};
	if (vista.nombre_producto) {
		campos.nombre_producto = vista.nombre_producto;
		if (!actuales.titulo?.trim()) campos.titulo = vista.nombre_producto.slice(0, LARGO_TITULO);
	}
	if (vista.precio_unitario) campos.precio_unitario = vista.precio_unitario;
	if (vista.descripcion && !actuales.descripcion?.trim()) campos.descripcion = vista.descripcion;
	return campos;
}

/** ¿Vale la pena pedir la vista previa? Solo enlaces http(s) con host. */
export function enlaceAnalizable(valor) {
	try {
		const url = new URL((valor ?? '').trim());
		return (url.protocol === 'http:' || url.protocol === 'https:') && Boolean(url.hostname);
	} catch {
		return false;
	}
}
