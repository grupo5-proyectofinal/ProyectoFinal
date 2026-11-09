/** Entradas de navegación del header. Las pestañas de /pools no se duplican acá. */
export const NAV = [
	{ href: '/', texto: 'Inicio', exacto: true, publico: true },
	{ href: '/pools', texto: 'Explorar', publico: true },
	{ href: '/mayoristas', texto: 'Mayoristas', publico: true, prefijo: true },
	{ href: '/admin/usuarios', texto: 'Admin', staff: true, prefijo: true }
];
