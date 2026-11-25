/**
 * Autocompletado de direcciones (módulo puro: sin fetch ni runes, se testea con `node --test`).
 * Espeja el mínimo de `/pools/buscar-direccion/`: con menos letras el backend no consulta.
 */

export const MIN_CARACTERES = 4;
export const DEMORA_MS = 450;

/** Texto a buscar: lo escrito, si ya alcanza para consultar. */
export function consultaDireccion(direccion) {
	const calle = (direccion ?? '').trim();
	return calle.length < MIN_CARACTERES ? '' : calle;
}

/**
 * Parámetros del pedido: la ciudad del formulario y, si el navegador ya tiene permiso,
 * la ubicación, para que las sugerencias de la zona aparezcan primero.
 */
export function parametrosBusqueda(direccion, ciudad = '', coords = null) {
	const q = consultaDireccion(direccion);
	if (!q) return null;
	const parametros = { q };
	const lugar = (ciudad ?? '').trim();
	if (lugar) parametros.ciudad = lugar;
	if (coords && Number.isFinite(coords.lat) && Number.isFinite(coords.lon)) {
		parametros.lat = coords.lat.toFixed(4);
		parametros.lon = coords.lon.toFixed(4);
	}
	return parametros;
}

/**
 * Lo que queda escrito al elegir una sugerencia. Si es solo la calle, se deja un espacio
 * para que siga con la altura (como en un buscador de mapas).
 */
export function textoAlElegir(sugerencia) {
	const direccion = (sugerencia?.direccion ?? '').trim();
	return sugerencia?.con_altura === false && direccion ? `${direccion} ` : direccion;
}

/** Mueve la opción activa con las flechas, dando la vuelta al llegar al borde. */
export function moverActivo(activo, cantidad, tecla) {
	if (cantidad <= 0) return -1;
	if (tecla === 'ArrowDown') return activo + 1 >= cantidad ? 0 : activo + 1;
	if (tecla === 'ArrowUp') return activo <= 0 ? cantidad - 1 : activo - 1;
	return activo;
}
