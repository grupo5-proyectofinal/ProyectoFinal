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
