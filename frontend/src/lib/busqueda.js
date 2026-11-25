/**
 * Búsqueda del header (módulo puro). Explorar solo lista pools abiertos de otras
 * personas, así que lo propio se busca aparte en Mis pools y Mis reservas.
 */

/**
 * Une los resultados de "Mis pools" y "Mis reservas" en una lista sin repetidos,
 * marcando qué relación tiene la persona con cada uno.
 */
export function propiosDeBusqueda(mios = [], unidos = []) {
	const vistos = new Set();
	const lista = [];
	for (const [pools, relacion] of [
		[mios, 'Organizás vos'],
		[unidos, 'Reservaste']
	]) {
		for (const pool of pools ?? []) {
			if (vistos.has(pool.id)) continue;
			vistos.add(pool.id);
			lista.push({ ...pool, relacion });
		}
	}
	return lista;
}
