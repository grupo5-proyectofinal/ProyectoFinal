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

const CINCO_MINUTOS = 5 * 60 * 1000;
const formateadorDia = new Intl.DateTimeFormat('es-AR', { day: 'numeric', month: 'long' });
const formateadorDiaConAnio = new Intl.DateTimeFormat('es-AR', {
	day: 'numeric',
	month: 'long',
	year: 'numeric'
});

function claveLocal(fecha) {
	return `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, '0')}-${String(
		fecha.getDate()
	).padStart(2, '0')}`;
}

function etiquetaDiaDe(clave, claveHoy, claveAyer, anioHoy) {
	if (clave === claveHoy) return 'Hoy';
	if (clave === claveAyer) return 'Ayer';
	const [anio, mes, dia] = clave.split('-').map(Number);
	if (!anio || !mes || !dia) return '';
	const fecha = new Date(anio, mes - 1, dia);
	return (anio === anioHoy ? formateadorDia : formateadorDiaConAnio).format(fecha);
}

/**
 * Prepara el chat para renderizar: separadores de día y agrupación de mensajes
 * consecutivos del mismo autor (hasta 5 minutos). `hoy` se puede fijar en tests.
 */
export function agruparPorDia(mensajes = [], hoy = new Date()) {
	const claveHoy = claveLocal(hoy);
	const ayer = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 1);
	const claveAyer = claveLocal(ayer);
	const anioHoy = hoy.getFullYear();

	const filas = [];
	let diaActual = '';
	let autorPrevio = null;
	let instantePrevio = Number.NaN;

	for (const mensaje of mensajes) {
		const clave = String(mensaje.creado ?? '').slice(0, 10);
		if (clave && clave !== diaActual) {
			filas.push({
				tipo: 'dia',
				clave: `dia-${clave}`,
				etiqueta: etiquetaDiaDe(clave, claveHoy, claveAyer, anioHoy)
			});
			diaActual = clave;
			autorPrevio = null;
			instantePrevio = Number.NaN;
		}

		const instante = Date.parse(mensaje.creado);
		const mismoAutor = mensaje.autor?.id != null && mensaje.autor.id === autorPrevio;
		const cerca =
			Number.isFinite(instante) &&
			Number.isFinite(instantePrevio) &&
			instante - instantePrevio <= CINCO_MINUTOS;

		filas.push({
			tipo: 'mensaje',
			clave: mensaje.id,
			mensaje,
			primero: !mismoAutor || !cerca
		});

		autorPrevio = mensaje.autor?.id ?? null;
		instantePrevio = instante;
	}

	return filas;
}
