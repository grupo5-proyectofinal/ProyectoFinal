export function etiquetaEstado(estado) {
	return estado.replace('_', ' ').replace(/^./, (c) => c.toUpperCase());
}

const PAGOS = {
	efectivo: 'Efectivo',
	transferencia: 'Transferencia',
	sin_especificar: 'Sin especificar'
};

export function etiquetaPago(valor) {
	return PAGOS[valor] ?? valor;
}

export const TONOS = ['azul', 'verde', 'ambar', 'coral', 'violeta', 'teal'];

/** Tono estable a partir del id de una categoría. */
export function tonoCategoria(id) {
	return TONOS[Math.abs(Math.trunc(Number(id))) % TONOS.length || 0];
}

/** Tono estable a partir de un texto (avatares/monogramas). */
export function tonoNombre(texto) {
	const suma = [...(texto ?? '').toLowerCase()].reduce((s, c) => s + c.codePointAt(0), 0);
	return TONOS[suma % TONOS.length];
}

/** ¿Este usuario puede unirse al pool? Solo abierto, sin ser creador ni miembro y con disponible. */
export function puedeUnirse(pool, usuarioId) {
	if (!pool || pool.estado !== 'abierto') return false;
	if (pool.creador?.id === usuarioId) return false;
	if ((pool.miembros ?? []).some((m) => m.usuario?.id === usuarioId)) return false;
	return (pool.disponible ?? 0) >= (pool.min_por_integrante ?? 1);
}

/** ¿Este usuario puede editar el pool? Solo el creador, y solo en abierto. */
export function puedeEditar(pool, usuarioId) {
	return pool?.estado === 'abierto' && pool.creador?.id === usuarioId;
}
