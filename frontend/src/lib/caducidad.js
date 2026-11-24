/**
 * Reglas de un pool caducado y de la reconfirmación tras extender el plazo
 * (módulo puro: sin fetch ni runes, se testea con `node --test`).
 *
 * Espeja el backend: DIAS_RECONFIRMACION y el máximo de 30 días de
 * `ExtensionSerializer`.
 */

export const DIAS_RECONFIRMACION = 3;
export const MAX_DIAS_EXTENSION = 30;

const MS_DIA = 24 * 60 * 60 * 1000;

// Estados en los que la fecha de caducidad todavía rige. Con el cupo completo (listo), el
// pedido en curso, o el pool finalizado o cancelado, "caduca en…" ya no significa nada.
const ESTADOS_CON_PLAZO = ['borrador', 'abierto', 'caducado', 'reconfirmacion'];

/** ¿Tiene sentido mostrar cuándo caduca un pool en este estado? */
export function muestraPlazo(estado) {
	return ESTADOS_CON_PLAZO.includes(estado);
}

function iso(fecha) {
	const y = fecha.getFullYear();
	const m = String(fecha.getMonth() + 1).padStart(2, '0');
	const d = String(fecha.getDate()).padStart(2, '0');
	return `${y}-${m}-${d}`;
}

/** Rango de fechas (ISO yyyy-mm-dd) que acepta el backend para extender. */
export function rangoExtension(hoy = new Date()) {
	const base = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
	return {
		min: iso(new Date(base.getTime() + (DIAS_RECONFIRMACION + 1) * MS_DIA)),
		max: iso(new Date(base.getTime() + MAX_DIAS_EXTENSION * MS_DIA))
	};
}

/** Rango de fechas (ISO yyyy-mm-dd) que acepta el backend para reabrir un pool cancelado. */
export function rangoReapertura(hoy = new Date()) {
	const base = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
	return {
		min: iso(new Date(base.getTime() + MS_DIA)),
		max: iso(new Date(base.getTime() + MAX_DIAS_EXTENSION * MS_DIA))
	};
}

/** ¿El creador puede extender el plazo? Solo con el pool caducado. */
export function puedeExtender(pool, usuarioId) {
	return pool?.estado === 'caducado' && pool.creador?.id === usuarioId;
}

/** La membresía del usuario si todavía tiene que responder la reconfirmación. */
export function reconfirmacionPendiente(pool, usuarioId) {
	if (pool?.estado !== 'reconfirmacion') return null;
	const mia = (pool.miembros ?? []).find((m) => m.usuario?.id === usuarioId);
	return mia && !mia.reconfirmado ? mia : null;
}

/** Cuántos participantes ya respondieron y cuántos faltan. */
export function resumenReconfirmacion(pool) {
	const miembros = pool?.miembros ?? [];
	const respondieron = miembros.filter((m) => m.reconfirmado).length;
	return { respondieron, faltan: miembros.length - respondieron };
}

/** Días (enteros, hacia arriba) hasta el cierre de la reconfirmación; 0 si ya pasó. */
export function diasParaResponder(pool, ahora = new Date()) {
	if (!pool?.reconfirmacion_hasta) return 0;
	const ms = new Date(pool.reconfirmacion_hasta).getTime() - ahora.getTime();
	return ms > 0 ? Math.ceil(ms / MS_DIA) : 0;
}
