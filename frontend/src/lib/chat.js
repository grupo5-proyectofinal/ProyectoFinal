/**
 * Reglas del chat por pool (contrato de la API, Phase 4).
 *
 * Módulo puro a propósito: sin fetch y sin runes, para poder testearlo directo
 * con `node --test`. El panel de chat lo consume.
 */

import { esIntegrante } from './historial.js';

/** Cada cuánto se pide lo nuevo (DW-5.3: ≤10 s). */
export const INTERVALO_CHAT = 5000;

/** Mensajes por lote en la carga inicial (máximo del contrato). */
export const LIMITE_INICIAL = 200;

const MAX_TEXTO = 1000;

// Espeja ESTADOS_CON_CHAT del backend: ERS 2.3, el chat nace en "listo".
const ESTADOS_CON_ESCRITURA = ['listo', 'en_curso', 'finalizado'];

const AVISOS = {
	abierto: 'El chat se habilita cuando el pool está listo para comprar.',
	cancelado: 'Este pool fue cancelado: el chat quedó en solo lectura.'
};

/** ¿El estado del pool permite escribir? */
export function puedeEscribirMensajes(estado) {
	return ESTADOS_CON_ESCRITURA.includes(estado);
}

/** Modo del panel para este usuario: `oculto` | `lectura` | `escritura`. */
export function estadoChat(pool, usuarioId) {
	if (!esIntegrante(pool, usuarioId)) return 'oculto';
	return puedeEscribirMensajes(pool.estado) ? 'escritura' : 'lectura';
}

/** Aviso es-AR cuando la escritura está bloqueada por estado; vacío si se puede escribir. */
export function avisoEscritura(estado) {
	if (puedeEscribirMensajes(estado)) return '';
	return AVISOS[estado] ?? 'En este estado el chat es de solo lectura.';
}

/** Mezcla mensajes sin duplicar por id, en orden ascendente. */
export function fusionarMensajes(previos = [], nuevos = []) {
	const porId = new Map(previos.map((mensaje) => [mensaje.id, mensaje]));
	for (const mensaje of nuevos) porId.set(mensaje.id, mensaje);
	return [...porId.values()].sort((a, b) => a.id - b.id);
}

/** Cursor `desde` del polling: el id más alto visto (0 si no hay mensajes). */
export function cursorMensajes(mensajes = []) {
	return mensajes.reduce((maximo, mensaje) => Math.max(maximo, mensaje.id), 0);
}

/** ¿Se puede enviar este borrador? (no vacío tras recortar, máximo 1000) */
export function puedeEnviar(texto) {
	const limpio = String(texto ?? '').trim();
	return limpio.length > 0 && limpio.length <= MAX_TEXTO;
}
