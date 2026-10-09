/**
 * Reglas de la eliminación con aprobación (contrato de la API, Phase 4).
 *
 * Módulo puro a propósito: sin fetch, sin runes y sin imports, para poder
 * testearlo directo con `node --test`. La página del detalle lo consume.
 */

/** ¿Puede este usuario pedir la eliminación con aprobación? (creador, listo/en_curso, sin pendiente) */
export function puedeSolicitarEliminacion(pool, usuarioId, solicitud = null) {
	if (!pool || pool.creador?.id !== usuarioId) return false;
	if (pool.estado !== 'listo' && pool.estado !== 'en_curso') return false;
	return solicitud?.estado !== 'pendiente';
}

/** El voto del usuario en la solicitud, o null si todavía no votó. */
export function miVotoEliminacion(solicitud, usuarioId) {
	return (solicitud?.votos ?? []).find((voto) => voto.usuario?.id === usuarioId) ?? null;
}

/** ¿Puede votar? Solo integrantes (no el creador) y una sola vez por solicitud. */
export function puedeVotarEliminacion(pool, solicitud, usuarioId) {
	if (!solicitud || solicitud.estado !== 'pendiente') return false;
	if (pool?.creador?.id === usuarioId) return false;
	const esIntegrante = (pool?.miembros ?? []).some((m) => m.usuario?.id === usuarioId);
	if (!esIntegrante) return false;
	return miVotoEliminacion(solicitud, usuarioId) === null;
}

/** ¿Puede eliminar el pool directamente? Creador y solo en abierto. */
export function puedeEliminarDirecto(pool, usuarioId) {
	return pool?.estado === 'abierto' && pool.creador?.id === usuarioId;
}

/** Desenlace de una respuesta de eliminación: borrado | rechazada | seguir. */
export function desenlaceEliminacion(estado) {
	if (estado === 'aprobada') return 'borrado';
	if (estado === 'rechazada') return 'rechazada';
	return 'seguir';
}

/** Mensaje es-AR para el error de una acción: detalle del API o aviso de red. */
export function mensajeError(error) {
	const data = error?.data;
	const detalle = Array.isArray(data)
		? data.join(' ')
		: (data?.detail ?? data?.non_field_errors ?? '');
	if (detalle) return Array.isArray(detalle) ? detalle.join(' ') : String(detalle);
	return data === undefined
		? 'No se pudo conectar con el servidor. Revisá tu conexión e intentá de nuevo.'
		: 'No se pudo completar la acción.';
}

/** Pide confirmación y ejecuta la acción solo si se acepta. */
export async function conConfirmacion(mensaje, pedirConfirmacion, accion) {
	if (!pedirConfirmacion(mensaje)) return { confirmada: false };
	return { confirmada: true, resultado: await accion() };
}
