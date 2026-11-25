/**
 * Entradas de navegación del header. Explorar (pools abiertos de otras personas),
 * Mis pools y Mis reservas son secciones aparte; las dos últimas son solo con sesión.
 */
export const NAV = [
	{ href: '/', texto: 'Inicio', exacto: true, publico: true },
	{ href: '/pools', texto: 'Explorar', publico: true },
	{ href: '/mis-pools', texto: 'Mis pools', desde: 'mios' },
	{ href: '/mis-reservas', texto: 'Mis reservas', desde: 'unidos' },
	{ href: '/ayuda', texto: 'Ayuda', publico: true },
	{ href: '/admin/usuarios', texto: 'Admin', staff: true, prefijo: true }
];
