import { necesitaRenovar } from './sesion.js';
import { renovarSesion, session, sesionExpirada } from './session.svelte.js';

export { fieldErrors } from './errores.js';

const BASE = '/api/v1';

export class ApiError extends Error {
	constructor(status, data) {
		super('Error de API');
		this.status = status;
		this.data = data;
	}
}

function aQueryString(query) {
	const params = new URLSearchParams();
	for (const [key, value] of Object.entries(query ?? {})) {
		if (value !== undefined && value !== null && value !== '') params.set(key, value);
	}
	return params.toString();
}

function pedir(path, { method = 'GET', body, auth = true, form = false, query } = {}) {
	const headers = {};
	if (!form && body !== undefined) headers['Content-Type'] = 'application/json';
	if (auth && session.access) headers.Authorization = `Bearer ${session.access}`;

	const search = aQueryString(query);
	return fetch(`${BASE}${path}${search ? `?${search}` : ''}`, {
		method,
		headers,
		body: body === undefined ? undefined : form ? body : JSON.stringify(body)
	});
}

/**
 * Hace el pedido manteniendo viva la sesión: renueva el access si está por vencer
 * y, ante un 401, renueva una sola vez (compartida entre pedidos) y reintenta. Si
 * el refresh también venció, avisa "Tu sesión expiró" y reintenta sin token: los
 * endpoints públicos siguen andando y los privados devuelven su 401.
 */
async function pedirConSesion(path, opciones = {}) {
	const auth = opciones.auth ?? true;
	if (auth && session.access && necesitaRenovar(session.access)) {
		// false = el refresh también venció: se avisa ya y el pedido sale sin token
		// (sin un segundo refresh ni reenviar el cuerpo dos veces).
		if ((await renovarSesion().catch(() => null)) === false) sesionExpirada();
	}

	const response = await pedir(path, opciones);
	if (response.status !== 401 || !auth || !session.refresh) return response;

	const renovado = await renovarSesion().catch(() => null);
	if (renovado === null) return response; // sin red: no se cierra la sesión por esto
	if (renovado) return pedir(path, opciones);
	sesionExpirada();
	return pedir(path, { ...opciones, auth: false });
}

export async function api(path, opciones = {}) {
	const response = await pedirConSesion(path, opciones);
	const data = response.status === 204 ? null : await response.json().catch(() => null);
	if (!response.ok) throw new ApiError(response.status, data);
	return data;
}

/** GET autenticado que devuelve el archivo como Blob (comprobantes privados). */
export async function apiBlob(path) {
	const response = await pedirConSesion(path);
	if (!response.ok) {
		const data = await response.json().catch(() => null);
		throw new ApiError(response.status, data);
	}
	return response.blob();
}
