const ESTADOS = {
	borrador: 'Borrador',
	abierto: 'Abierto',
	listo: 'Listo',
	caducado: 'Caducado',
	reconfirmacion: 'Esperando confirmación',
	en_curso: 'En curso',
	finalizado: 'Finalizado',
	cancelado: 'Cancelado'
};

export function etiquetaEstado(estado) {
	return ESTADOS[estado] ?? estado.replace('_', ' ').replace(/^./, (c) => c.toUpperCase());
}

const PAGOS = {
	transferencia: 'Transferencia',
	sin_especificar: 'Sin especificar'
};

export function etiquetaPago(valor) {
	return PAGOS[valor] ?? valor;
}

/**
 * Rubro de una tarjeta de pool. Si el pool está en una subcategoría se muestra
 * con su categoría principal ("Higiene personal · Perfume"), como en el inicio y
 * los filtros, que listan las principales.
 */
export function etiquetaCategoria(pool) {
	const nombre = pool?.categoria_nombre ?? '';
	const padre = pool?.categoria_padre_nombre;
	return padre ? `${padre} · ${nombre}` : nombre;
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

/** ¿Este usuario puede editar el pool? Solo el creador, y solo en borrador o abierto. */
export function puedeEditar(pool, usuarioId) {
	return ['borrador', 'abierto'].includes(pool?.estado) && pool.creador?.id === usuarioId;
}

// Estados desde los que se puede cancelar (espeja ESTADOS_CANCELABLES del backend).
// Finalizado y cancelado son finales: no hay nada que cancelar.
const CANCELABLES = ['borrador', 'abierto', 'caducado', 'reconfirmacion', 'listo', 'en_curso'];

/** ¿El creador puede cancelar el pool en su estado actual? */
export function puedeCancelar(pool, usuarioId) {
	return CANCELABLES.includes(pool?.estado) && pool.creador?.id === usuarioId;
}

/** ¿El creador puede publicar este borrador? */
export function puedePublicar(pool, usuarioId) {
	return pool?.estado === 'borrador' && pool.creador?.id === usuarioId;
}

/** Personas que reservaron sin contar al creador (`integrantes` lo incluye). */
export function reservantes(pool) {
	return Math.max(Number(pool?.integrantes ?? 1) - 1, 0);
}

/** ¿El creador puede reabrir el pool cancelado? Solo si nadie había reservado. */
export function puedeReabrir(pool, usuarioId) {
	return pool?.estado === 'cancelado' && pool.creador?.id === usuarioId && reservantes(pool) === 0;
}

/** ¿El creador puede duplicar el pool para empezar de nuevo? Cancelado o finalizado. */
export function puedeDuplicar(pool, usuarioId) {
	return ['cancelado', 'finalizado'].includes(pool?.estado) && pool.creador?.id === usuarioId;
}

/**
 * Sección del menú a la que pertenece un pool para esta persona: 'mios' si lo organiza,
 * 'unidos' si reservó, null si lo mira desde Explorar.
 */
export function seccionDelPool(pool, usuarioId) {
	if (!pool || usuarioId == null) return null;
	if (pool.creador?.id === usuarioId) return 'mios';
	return (pool.miembros ?? []).some((m) => m.usuario?.id === usuarioId) ? 'unidos' : null;
}

const ESTADOS_FILTRO = ['borrador', 'abierto', 'listo', 'caducado', 'reconfirmacion', 'en_curso', 'finalizado', 'cancelado'];

/**
 * Estados que ofrece el filtro de cada sección. Explorar no filtra (solo hay abiertos).
 * Los borradores son solo de su creador, y en "Mis reservas" no se ofrece «Caducado»
 * (pedido del cliente: para quien reservó, esa espera no es un estado que busque).
 */
export function estadosFiltrables(tab) {
	if (tab === 'mios') return ESTADOS_FILTRO;
	if (tab === 'unidos') return ESTADOS_FILTRO.filter((e) => e !== 'borrador' && e !== 'caducado');
	return [];
}
