import { ApiError, api } from './api.js';

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

export async function login(email, password) {
	const data = await api('/auth/login/', {
		method: 'POST',
		body: { email, password },
		auth: false
	});
	applyTokens(data);
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
		if (error instanceof ApiError && error.status === 401) logout();
		else console.error(error);
	} finally {
		session.loading = false;
	}
}

export async function updateMe(payload, form = false) {
	const updated = await api('/auth/me/', { method: 'PATCH', body: payload, form });
	session.user = { ...session.user, ...updated };
}

export function logout() {
	session.user = null;
	session.access = null;
	session.refresh = null;
	if (typeof localStorage !== 'undefined') localStorage.removeItem(KEY);
}
