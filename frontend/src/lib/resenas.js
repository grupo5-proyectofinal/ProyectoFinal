/**
 * Puntuación y reseñas entre participantes (Iteración 2).
 *
 * Módulo puro (sin runes ni fetch). El servidor valida las reglas (pool
 * finalizado, sin autocalificarse ni repetir); acá se decide a quién mostrar
 * en "Calificar participantes" y cómo se leen los puntajes.
 */

const NUMERO = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** 4.5 -> "4,5"; sin reseñas -> "—". */
export function formatoPuntaje(promedio) {
	if (promedio === null || promedio === undefined || promedio === '') return '—';
	const n = Number(promedio);
	return Number.isFinite(n) ? NUMERO.format(n) : '—';
}

/** "Sin reseñas", "1 reseña", "N reseñas". */
export function textoResenas(n) {
	const total = Number(n) || 0;
	if (!total) return 'Sin reseñas';
	return total === 1 ? '1 reseña' : `${total} reseñas`;
}

/** Cinco posiciones: true = estrella llena (redondeo al entero más cercano). */
export function estrellas(puntaje) {
	const llenas = Math.max(0, Math.min(5, Math.round(Number(puntaje) || 0)));
	return Array.from({ length: 5 }, (_, i) => i < llenas);
}

/** "Como administrador" / "Como participante" (rol del destinatario en el pool). */
export function etiquetaRol(rol) {
	return rol === 'administrador' ? 'Como administrador' : 'Como participante';
}

/**
 * Participantes que `usuarioId` todavía puede calificar en el pool: todos
 * (creador + miembros) menos él mismo y los que ya calificó.
 */
export function pendientesDeCalificar(pool, usuarioId, propias = []) {
	if (!pool || pool.estado !== 'finalizado' || usuarioId == null) return [];
	const calificados = new Set(propias.map((r) => r.destinatario));
	const participantes = [
		{ ...pool.creador, rol: 'administrador' },
		...(pool.miembros ?? []).map((m) => ({ ...m.usuario, rol: 'participante' }))
	];
	return participantes.filter((p) => p.id !== usuarioId && !calificados.has(p.id));
}

/** Payload de `POST /pools/{id}/resenas/`: puntaje numérico y comentario recortado. */
export function payloadResena(destinatario, puntaje, comentario) {
	return {
		destinatario,
		puntaje: Number(puntaje),
		comentario: (comentario ?? '').trim()
	};
}
