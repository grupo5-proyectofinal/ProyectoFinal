/** Entradas de navegación del header. Las pestañas de /pools no se duplican acá. */
export const NAV = [
	{ href: '/', texto: 'Inicio', exacto: true, publico: true },
	{ href: '/pools', texto: 'Explorar', publico: true },
	{ href: '/ayuda', texto: 'Ayuda', publico: true },
	{ href: '/admin/usuarios', texto: 'Admin', staff: true, prefijo: true }
];
