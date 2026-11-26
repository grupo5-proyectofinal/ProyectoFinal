/**
 * Normaliza espacios extremos y múltiples de una ciudad.
 * @param {unknown} valor
 * @returns {string}
 */
export function normalizarCiudad(valor) {
	if (typeof valor !== 'string') return '';
	return valor.trim().replace(/\s+/g, ' ');
}

/**
 * Construye la lista ordenada de opciones para el selector de ciudad.
 * Deduplica sin distinguir mayúsculas/minúsculas e incluye `actual` (si viene en la URL
 * y no está en la lista del servidor) para que el `<select>` refleje el filtro activo.
 * @param {unknown} ciudades
 * @param {string} [actual='']
 * @returns {string[]}
 */
export function opcionesCiudad(ciudades, actual = '') {
	const porClave = new Map();
	if (Array.isArray(ciudades)) {
		for (const ciudad of ciudades) {
			const limpia = normalizarCiudad(ciudad);
			if (!limpia) continue;
			const clave = limpia.toLocaleLowerCase('es');
			const existente = porClave.get(clave);
			if (
				!existente ||
				(existente === existente.toLocaleLowerCase('es') &&
					limpia !== limpia.toLocaleLowerCase('es'))
			) {
				porClave.set(clave, limpia);
			}
		}
	}

	const limpiaActual = normalizarCiudad(actual);
	if (limpiaActual) {
		const claveActual = limpiaActual.toLocaleLowerCase('es');
		if (!porClave.has(claveActual)) {
			porClave.set(claveActual, limpiaActual);
		}
	}

	return [...porClave.values()].sort((a, b) => a.localeCompare(b, 'es'));
}
