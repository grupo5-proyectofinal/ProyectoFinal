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

export async function register(payload, form = false) {
	const data = await api('/auth/register/', { method: 'POST', body: payload, auth: false, form });
	applyTokens(data);
	session.user = data.user;
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
