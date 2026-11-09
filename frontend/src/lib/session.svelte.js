import { ApiError, api } from './api.js';
import { borrarBorradores } from './borrador.js';
import { MENSAJE_SESION_EXPIRADA, unaVez } from './sesion.js';
import { cerrar, notificar, toasts } from './toast.svelte.js';

const KEY = 'poolshop.session';

function readTokens() {
	if (typeof localStorage === 'undefined') return {};
	try {
		return JSON.parse(localStorage.getItem(KEY)) ?? {};
	} catch {
		return {};
	}
}

const saved = readTokens();

export const session = $state({
	user: null,
	loading: false,
	access: saved.access ?? null,
	refresh: saved.refresh ?? null
});

function persist() {
	if (typeof localStorage === 'undefined') return;
	localStorage.setItem(KEY, JSON.stringify({ access: session.access, refresh: session.refresh }));
}

function applyTokens(data) {
	session.access = data.access;
	session.refresh = data.refresh;
	persist();
}

// Otra pestaña renovó o cerró la sesión: se adoptan sus tokens. Sin esto, con el
// refresh rotativo la pestaña vieja usaría un refresh ya invalidado y se cerraría.
if (typeof window !== 'undefined') {
	window.addEventListener('storage', (event) => {
		if (event.key !== KEY) return;
		const guardados = readTokens();
		session.access = guardados.access ?? null;
		session.refresh = guardados.refresh ?? null;
		if (!session.access) session.user = null;
	});
}

async function pedirRenovacion() {
	// Si otra pestaña ya rotó el refresh, se usan sus tokens en vez de pedir otros.
	const guardados = readTokens();
	if (guardados.refresh && guardados.refresh !== session.refresh) {
		session.access = guardados.access ?? null;
		session.refresh = guardados.refresh;
		return true;
	}
	if (!session.refresh) return false;
	try {
		const data = await api('/auth/refresh/', {
			method: 'POST',
			body: { refresh: session.refresh },
			auth: false
		});
		applyTokens({ access: data.access, refresh: data.refresh ?? session.refresh });
		return true;
	} catch (error) {
		// 400/401: el refresh venció o fue invalidado. Otro error (red, 5xx) se propaga
		// para que api.js no cierre la sesión por un corte momentáneo.
		if (error instanceof ApiError && (error.status === 400 || error.status === 401)) return false;
		throw error;
	}
}

/**
 * Renueva el access con el refresh. Un solo pedido aunque lo pidan muchos a la vez
 * (unaVez) y, con varias pestañas abiertas, uno solo entre todas (Web Locks).
 * Devuelve true si quedó una sesión válida y false si hay que volver a iniciar sesión.
 */
export const renovarSesion = unaVez(() =>
	typeof navigator !== 'undefined' && navigator.locks
		? navigator.locks.request('poolshop.renovar-sesion', pedirRenovacion)
		: pedirRenovacion()
);

/** La sesión venció del todo: se limpia y se avisa (una sola vez). */
export function sesionExpirada() {
	if (!session.access && !session.refresh) return;
	limpiar();
	notificar(MENSAJE_SESION_EXPIRADA, 'aviso');
}

// El registro no inicia sesión: la cuenta queda pendiente hasta confirmar el email.
export async function register(payload, form = false) {
	return api('/auth/register/', { method: 'POST', body: payload, auth: false, form });
}

/** Confirma el email con el link del mail; el API responde con los tokens. */
export async function verificarEmail(uid, token) {
	const data = await api('/auth/verificar-email/', {
		method: 'POST',
		body: { uid, token },
		auth: false
	});
	applyTokens(data);
	session.user = data.user;
}

/** Pide otro mail de verificación (respuesta neutra del API). */
export function reenviarVerificacion(email) {
	return api('/auth/verificar-email/reenviar/', {
		method: 'POST',
		body: { email },
		auth: false
	});
}

// El API acepta nombre de usuario o email en el campo `email` (USERNAME_FIELD).
export async function login(identificador, password) {
	const data = await api('/auth/login/', {
		method: 'POST',
		body: { email: identificador, password },
		auth: false
	});
	applyTokens(data);
	// El aviso de "Tu sesión expiró" ya cumplió: no queda colgado después de ingresar.
	for (const toast of [...toasts]) if (toast.mensaje === MENSAJE_SESION_EXPIRADA) cerrar(toast.id);
	await loadMe();
}

export async function loadMe() {
	if (!session.access) {
		session.user = null;
		return;
	}
	session.loading = true;
	try {
		session.user = await api('/auth/me/');
	} catch (error) {
		// api.js ya intentó renovar: un 401 acá es una sesión vencida de verdad.
		if (error instanceof ApiError && error.status === 401) sesionExpirada();
		else console.error(error);
	} finally {
		session.loading = false;
	}
}

export async function updateMe(payload, form = false) {
	const updated = await api('/auth/me/', { method: 'PATCH', body: payload, form });
	session.user = { ...session.user, ...updated };
}

function limpiar() {
	session.user = null;
	session.access = null;
	session.refresh = null;
	if (typeof localStorage !== 'undefined') localStorage.removeItem(KEY);
}

export function logout() {
	// Invalida el refresh en el servidor (blacklist); si falla, igual se sale local.
	const refresh = session.refresh;
	if (refresh) {
		api('/auth/logout/', { method: 'POST', body: { refresh }, auth: false }).catch(() => {});
	}
	// Cierre voluntario: los borradores no quedan para el próximo que use la pestaña.
	// (Si la sesión solo venció se conservan: son para recuperar después del login.)
	borrarBorradores();
	limpiar();
}

/**
 * Da de baja la cuenta propia (pide la contraseña). El servidor ya invalida todas
 * las sesiones; acá solo se limpia lo local. Si tiene pools activos lanza un
 * ApiError 409 con `data.pools` para mostrarle cuáles cerrar.
 */
export async function eliminarCuenta(password) {
	await api('/auth/me/baja/', { method: 'POST', body: { password } });
	borrarBorradores();
	limpiar();
}
