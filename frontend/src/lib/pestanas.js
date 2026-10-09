/** Pestañas del listado de pools (`/pools?tab=todos|mios|unidos`), dirigidas por URL. */

export const TABS = [
	{ id: 'todos', texto: 'Todos' },
	{ id: 'mios', texto: 'Mis pools' },
	{ id: 'unidos', texto: 'Unidos' }
];

const AUTENTICADAS = ['mios', 'unidos'];

// ponytail: `mios`/`unidos` paginan pero ignoran filtros/orden (custom actions de DRF sin
// filter_queryset); el front los reenvía igual para no bifurcar el camino de datos.
// Fix de backend: ~2 líneas por action (aplicar `self.filter_queryset(...)`).
const ENDPOINTS = {
	todos: '/pools/',
	mios: '/pools/mios/',
	unidos: '/pools/unidos/'
};

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

/**
 * URL de la pestaña `destino` conservando filtros y orden.
 * Al cambiar de pestaña descarta `page`; repetir la activa la conserva.
 */
export function rutaTab(destino, params = new URLSearchParams(), actual = destino) {
	const query = new URLSearchParams(params);
	query.set('tab', destino);
	if (destino !== actual) query.delete('page');
	return `/pools?${query}`;
}

/** Query para `api()`: el estado de URL de la pestaña, sin el param `tab`. */
export function queryDeApi(params) {
	const query = Object.fromEntries(params);
	delete query.tab;
	return query;
}

/** Filtros del formulario como query, sin perder la pestaña activa. */
export function paramsDeFiltros(filtros, tab) {
	const params = new URLSearchParams();
	for (const [key, value] of Object.entries(filtros)) {
		if (value) params.set(key, value);
	}
	params.set('tab', tab);
	return params;
}

/** Contexto de `PoolCard` que conserva el estilo de las páginas viejas. */
export function contextoDeTab(tab) {
	return CONTEXTOS[tab] ?? null;
}

/** ¿La entrada de nav está activa para el pathname y la pestaña actuales? */
export function navActiva(enlace, pathname, tab) {
	if (enlace.tab) return pathname === '/pools' && tab === enlace.tab;
	if (enlace.exacto) return pathname === enlace.href;
	if (enlace.href === '/pools') {
		if (pathname === '/pools') return tab === 'todos';
		return pathname.startsWith('/pools/') && pathname !== '/pools/nuevo';
	}
	return pathname === enlace.href;
}
