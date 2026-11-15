/**
 * Mapeo de errores de la API a mensajes por campo (contrato DRF).
 *
 * Módulo puro a propósito: sin runes, sin fetch y sin imports, para poder
 * testearlo directo con `node --test`. `api.js` lo re-exporta y las páginas lo
 * importan de ahí.
 */

/** Normaliza el body de un error DRF a `{campo: mensaje}` (strings planos). */
export function fieldErrors(data) {
	if (Array.isArray(data)) return { detail: data.join(' ') };
	if (!data || typeof data !== 'object') return {};
	const result = {};
	for (const [key, value] of Object.entries(data)) {
		result[key] = Array.isArray(value) ? value.join(' ') : String(value);
	}
	return result;
}

/** Mensaje es-AR para el error de una acción: detalle del API o aviso de red. */
export function mensajeError(error) {
	const data = error?.data;
	const detalle = Array.isArray(data)
		? data.join(' ')
		: (data?.detail ?? data?.non_field_errors ?? '');
	if (detalle) return Array.isArray(detalle) ? detalle.join(' ') : String(detalle);
	return data === undefined
		? 'No se pudo conectar con el servidor. Revisá tu conexión e intentá de nuevo.'
		: 'No se pudo completar la acción.';
}

/** Pide confirmación (sincrónica o con promesa) y ejecuta la acción solo si se acepta. */
export async function conConfirmacion(mensaje, pedirConfirmacion, accion) {
	if (!(await pedirConfirmacion(mensaje))) return { confirmada: false };
	return { confirmada: true, resultado: await accion() };
}
