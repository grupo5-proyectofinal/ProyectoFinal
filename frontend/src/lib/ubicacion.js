/** Decide si un pool tiene coordenadas utilizables para mostrar el mapa. */
export function coordsValidas(lat, lng) {
	if (
		lat === null ||
		lat === undefined ||
		lat === '' ||
		lng === null ||
		lng === undefined ||
		lng === ''
	) {
		return false;
	}
	const y = Number(lat);
	const x = Number(lng);
	return Number.isFinite(y) && Number.isFinite(x) && y >= -90 && y <= 90 && x >= -180 && x <= 180;
}

/**
 * Link a Google Maps del pool: por coordenadas si las hay; si no (Nominatim no
 * encontró la dirección), por el texto "dirección, ciudad". null si no hay nada.
 */
export function enlaceMaps(pool) {
	const base = 'https://www.google.com/maps/search/?api=1&query=';
	if (coordsValidas(pool?.latitud, pool?.longitud)) {
		return `${base}${pool.latitud},${pool.longitud}`;
	}
	const texto = [pool?.direccion, pool?.ciudad]
		.map((parte) => (parte ?? '').trim())
		.filter(Boolean)
		.join(', ');
	return texto ? `${base}${encodeURIComponent(texto)}` : null;
}
