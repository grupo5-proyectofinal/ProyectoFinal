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
