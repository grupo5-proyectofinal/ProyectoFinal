import { session } from './session.svelte.js';

const BASE = '/api/v1';

export class ApiError extends Error {
	constructor(status, data) {
		super('Error de API');
		this.status = status;
		this.data = data;
	}
}

export function fieldErrors(data) {
	if (!data || typeof data !== 'object' || Array.isArray(data)) return {};
	const result = {};
	for (const [key, value] of Object.entries(data)) {
		result[key] = Array.isArray(value) ? value.join(' ') : String(value);
	}
	return result;
}

export async function api(path, { method = 'GET', body, auth = true, form = false } = {}) {
	const headers = {};
	if (!form && body !== undefined) headers['Content-Type'] = 'application/json';
	if (auth && session.access) headers.Authorization = `Bearer ${session.access}`;

	const response = await fetch(`${BASE}${path}`, {
		method,
		headers,
		body: body === undefined ? undefined : form ? body : JSON.stringify(body)
	});

	const data = response.status === 204 ? null : await response.json().catch(() => null);
	if (!response.ok) throw new ApiError(response.status, data);
	return data;
}
