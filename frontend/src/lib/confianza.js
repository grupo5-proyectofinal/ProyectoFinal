/**
 * Helpers puros del panel de análisis del enlace (Plan 3, Fase 2).
 *
 * Módulo sin runes ni fetch para poder testearlo con `node --test`: traduce el
 * contrato del backend (`{nivel, validaciones: [{clave, ok, detalle}]}`) a
 * etiquetas, tonos y estados de UI.
 */

const NIVELES = {
	alto: { etiqueta: 'Confianza alta', tono: 'verde' },
	medio: { etiqueta: 'Confianza media', tono: 'ambar' },
	bajo: { etiqueta: 'Confianza baja', tono: 'coral' }
};

const CLAVES = {
	formato: 'Formato',
	https: 'HTTPS',
	longitud: 'Longitud',
	ip_literal: 'Dirección IP',
	acortador: 'Acortador',
	tld: 'Dominio',
	uso: 'Uso en PoolShop'
};

/** Etiqueta es-AR del nivel de confianza; un nivel desconocido no rompe la UI. */
export function etiquetaNivel(nivel) {
	return NIVELES[nivel]?.etiqueta ?? 'Sin analizar';
}

/** Tono visual del nivel (clases `tono-*` de app.css). */
export function tonoNivel(nivel) {
	return NIVELES[nivel]?.tono ?? 'azul';
}

/** Etiqueta visible de una clave del contrato. */
export function etiquetaClave(clave) {
	return CLAVES[clave] ?? clave;
}

/**
 * Estado de UI de una validación: `ok` (pasó), `atencion` (no pasó) o `neutro`.
 * La señal de uso no es una advertencia: no haber visto el dominio antes no es
 * un riesgo.
 */
export function estadoValidacion(validacion) {
	if (validacion?.ok) return 'ok';
	return validacion?.clave === 'uso' ? 'neutro' : 'atencion';
}

/** ¿Este pool tiene análisis para mostrar? Sin enlace el backend devuelve null. */
export function mostrarAnalisis(pool) {
	return Boolean(pool?.analisis_enlace);
}
