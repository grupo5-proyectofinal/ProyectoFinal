/**
 * Lógica del flujo de recuperación de contraseña (contrato de la API, Phase 1).
 *
 * Módulo puro a propósito: sin fetch, sin runes y sin imports de `api.js`, para
 * poder testearlo directo con `node --test`. Lo consumen /recuperar y /restablecer.
 */

import { mensajeError } from './eliminacion.js';

/** Texto de confirmación de /recuperar: nunca revela si la cuenta existe. */
export const CONFIRMACION_NEUTRAL =
	'Si el email corresponde a una cuenta, te enviamos un enlace para restablecer la contraseña.';

/** Lee `uid` y `token` del query string. Entrada externa: se valida su presencia. */
export function parametrosDeReset(search) {
	const params = new URLSearchParams(search ?? '');
	const uid = (params.get('uid') ?? '').trim();
	const token = (params.get('token') ?? '').trim();
	return { uid, token, completo: uid !== '' && token !== '' };
}

/** Confirmación tras el 200: usa el `detail` del API solo si es texto válido. */
export function confirmacionDeSolicitud(data) {
	const detalle = typeof data?.detail === 'string' ? data.detail.trim() : '';
	return detalle || CONFIRMACION_NEUTRAL;
}

/** ¿El error indica enlace inválido/expirado? El contrato es 400 con `detail`. */
export function enlaceInvalido(error) {
	return (
		error?.status === 400 &&
		typeof error?.data?.detail === 'string' &&
		error.data.detail.trim() !== ''
	);
}

/** Mensaje es-AR del error. El throttle de DRF responde en inglés: se reemplaza. */
export function mensajeReset(error) {
	if (error?.status === 429) {
		return 'Demasiados intentos. Esperá unos minutos y volvé a probar.';
	}
	return mensajeError(error);
}
