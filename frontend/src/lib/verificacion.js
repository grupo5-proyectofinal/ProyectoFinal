/**
 * Verificación de email y baja de correos (Iteración 2).
 *
 * Módulo puro (sin fetch ni runes) para testearlo con `node --test`. Lo usan
 * /registro, /login, /verificar-email y /baja-emails.
 */

import { mensajeError } from './eliminacion.js';

/** ¿El login falló porque la cuenta todavía no confirmó su email? (403 del API) */
export function pendienteDeVerificacion(error) {
	return error?.status === 403;
}

/** Lee `token` del query string del link de baja. */
export function tokenDeBaja(search) {
	return (new URLSearchParams(search ?? '').get('token') ?? '').trim();
}

/** Mensaje es-AR de un error de verificación/reenvío/baja; el 429 de DRF viene en inglés. */
export function mensajeVerificacion(error) {
	if (error?.status === 429) return 'Demasiados intentos. Esperá unos minutos y volvé a probar.';
	const token = error?.data?.token;
	if (token) return Array.isArray(token) ? token.join(' ') : String(token);
	return mensajeError(error);
}

/** Confirmación tras el registro: el `detail` del API o un texto neutro con el email. */
export function textoRegistroPendiente(data, email) {
	const detalle = typeof data?.detail === 'string' ? data.detail.trim() : '';
	return detalle || `Te enviamos un mail a ${email} para confirmar tu cuenta.`;
}
