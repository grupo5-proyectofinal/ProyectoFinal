/**
 * Lógica del backoffice de usuarios (contrato de la API, Phase 3).
 *
 * Módulo puro a propósito: sin fetch, sin runes y sin imports, para poder
 * testearlo directo con `node --test`. Lo consumen las páginas `/admin/**` y el
 * guard del layout.
 */

/** Aviso es-AR cuando la sesión perdió el rol de staff en runtime (403). */
export const SIN_ACCESO = 'Tu cuenta ya no tiene acceso al panel.';

/** ¿El usuario tiene rol de staff? `is_staff` llega del API: se exige booleano. */
export function esStaff(user) {
	return user?.is_staff === true;
}

/**
 * Destino del guard para las rutas `/admin`: `'/login'` sin sesión, `'/'` para
 * autenticado sin rol, `null` para seguir (staff o usuario aún cargando).
 */
export function destinoGuardAdmin(access, user) {
	if (!access) return '/login';
	if (user && !esStaff(user)) return '/';
	return null;
}

/** Filtros del listado leídos de la URL. Entrada externa: se normaliza. */
export function filtrosDeListado(search) {
	const params = new URLSearchParams(search ?? '');
	const is_active = params.get('is_active');
	const pagina = Number.parseInt(params.get('page') ?? '', 10);
	return {
		q: (params.get('q') ?? '').trim(),
		is_active: is_active === 'true' || is_active === 'false' ? is_active : '',
		pagina: Number.isInteger(pagina) && pagina > 0 ? pagina : 1
	};
}

/** Query para `api()`: omite filtros vacíos y manda `page` solo cuando aplica. */
export function queryDeListado({ q, is_active, pagina } = {}) {
	const query = {};
	if (q) query.q = q;
	if (is_active) query.is_active = is_active;
	if (pagina > 1) query.page = pagina;
	return query;
}

/** URL del listado con los filtros del form; siempre resetea la página. */
export function rutaListado(filtros) {
	const params = new URLSearchParams();
	const q = (filtros?.q ?? '').trim();
	const is_active = filtros?.is_active;
	if (q) params.set('q', q);
	if (is_active === 'true' || is_active === 'false') params.set('is_active', is_active);
	const query = params.toString();
	return query ? `/admin/usuarios?${query}` : '/admin/usuarios';
}

/** URL del listado en la página `n` conservando los filtros actuales. */
export function rutaPagina(search, n) {
	const params = new URLSearchParams(search ?? '');
	if (n > 1) params.set('page', String(n));
	else params.delete('page');
	const query = params.toString();
	return query ? `/admin/usuarios?${query}` : '/admin/usuarios';
}

/** ¿Se puede activar/desactivar a este usuario? Nunca la propia cuenta. */
export function puedeToggle(usuario, sesion) {
	return Boolean(usuario?.id) && Boolean(sesion?.id) && usuario.id !== sesion.id;
}

/**
 * Aplica la respuesta parcial del PATCH sobre el usuario en pantalla: el
 * update-serializer no devuelve email/dni/username, que deben conservarse.
 */
export function fusionarUsuario(usuario, cambios) {
	return { ...usuario, ...(cambios ?? {}) };
}

/** Nombre para mostrar: nombre y apellido, o el usuario. */
export function nombreUsuario(usuario) {
	return (
		[usuario?.first_name, usuario?.last_name].filter(Boolean).join(' ') ||
		usuario?.username ||
		''
	);
}
