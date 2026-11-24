/**
 * Autocompletado de direcciones (módulo puro: sin fetch ni runes, se testea con `node --test`).
 * Espeja el mínimo de `/pools/buscar-direccion/`: con menos letras el backend no consulta.
 */

export const MIN_CARACTERES = 4;
export const DEMORA_MS = 450;

/** Texto a buscar: lo que se escribió más la ciudad (si ya la completó) para acotar. */
export function consultaDireccion(direccion, ciudad = '') {
	const calle = (direccion ?? '').trim();
	if (calle.length < MIN_CARACTERES) return '';
	const lugar = (ciudad ?? '').trim();
	return lugar && !calle.toLowerCase().includes(lugar.toLowerCase()) ? `${calle}, ${lugar}` : calle;
}

/** Mueve la opción activa con las flechas, dando la vuelta al llegar al borde. */
export function moverActivo(activo, cantidad, tecla) {
	if (cantidad <= 0) return -1;
	if (tecla === 'ArrowDown') return activo + 1 >= cantidad ? 0 : activo + 1;
	if (tecla === 'ArrowUp') return activo <= 0 ? cantidad - 1 : activo - 1;
	return activo;
}
