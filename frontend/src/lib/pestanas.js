/**
 * Secciones del listado de pools, cada una con su ruta: Explorar (`/pools`, pools abiertos de
 * otras personas), Mis pools (`/mis-pools`) y Mis reservas (`/mis-reservas`).
 */

export const TABS = [
	{ id: 'todos', texto: 'Explorar' },
	{ id: 'mios', texto: 'Mis pools' },
	{ id: 'unidos', texto: 'Mis reservas' }
];

const AUTENTICADAS = ['mios', 'unidos'];

const ENDPOINTS = {
	todos: '/pools/',
	mios: '/pools/mios/',
	unidos: '/pools/unidos/'
};

const RUTAS = { todos: '/pools', mios: '/mis-pools', unidos: '/mis-reservas' };

const CONTEXTOS = { mios: 'mis-pools', unidos: 'unidos' };

/** Normaliza `?tab=`: cualquier valor fuera de los tres tabs cae en "todos". */
export function normalizarTab(valor) {
	return TABS.some((tab) => tab.id === valor) ? valor : 'todos';
}

/** Endpoint del API que sirve el dataset de la pestaña. */
export function endpointDeTab(tab) {
	return ENDPOINTS[tab] ?? ENDPOINTS.todos;
}

/** ¿La pestaña requiere sesión? (guard del layout para deep-links) */
export function esTabAutenticada(tab) {
	return AUTENTICADAS.includes(tab);
}

/** Ruta de la sección (`/pools`, `/mis-pools` o `/mis-reservas`) sin filtros. */
export function rutaDeTab(tab) {
	return RUTAS[tab] ?? RUTAS.todos;
}

/**
 * URL de la sección `destino` conservando filtros y orden.
 * Al cambiar de sección descarta `page`; repetir la activa la conserva.
 * Los enlaces viejos con `?tab=` se traducen: el parámetro ya no viaja.
 */
export function rutaTab(destino, params = new URLSearchParams(), actual = destino) {
	const query = new URLSearchParams(params);
	query.delete('tab');
	if (destino !== actual) query.delete('page');
	const texto = query.toString();
	return texto ? `${rutaDeTab(destino)}?${texto}` : rutaDeTab(destino);
}

/** Query para `api()`: el estado de URL de la pestaña, sin el param `tab`. */
export function queryDeApi(params) {
	const query = Object.fromEntries(params);
	delete query.tab;
	return query;
}

/** Página de la URL normalizada a entero ≥ 1 (`?page=abc`, `?page=` o negativos caen en la 1). */
export function paginaDeParams(params) {
	const pagina = Number.parseInt(params.get('page') ?? '', 10);
	return Number.isInteger(pagina) && pagina > 0 ? pagina : 1;
}

/** Filtros del formulario como query (la sección ya está en la ruta). */
export function paramsDeFiltros(filtros) {
	const params = new URLSearchParams();
	for (const [key, value] of Object.entries(filtros)) {
		if (value) params.set(key, value);
	}
	return params;
}

/** Contexto de `PoolCard` que conserva el estilo de las páginas viejas. */
export function contextoDeTab(tab) {
	return CONTEXTOS[tab] ?? null;
}

/**
 * ¿La entrada de nav está activa para el pathname actual?
 * Explorar, Mis pools y Mis reservas son secciones aparte. El detalle de un pool cuelga de
 * la sección desde la que la persona lo mira (`desde`: 'mios' si lo organiza, 'unidos' si
 * reservó); sin relación con el pool, de Explorar.
 */
export function navActiva(enlace, pathname, desde = null) {
	if (enlace.exacto) return pathname === enlace.href;
	if (enlace.prefijo) return pathname === enlace.href || pathname.startsWith(`${enlace.href}/`);
	const esDetalle = pathname.startsWith('/pools/') && pathname !== '/pools/nuevo';
	if (enlace.desde) return pathname === enlace.href || (esDetalle && desde === enlace.desde);
	if (enlace.href === '/pools') return pathname === '/pools' || (esDetalle && !desde);
	return pathname === enlace.href;
}
