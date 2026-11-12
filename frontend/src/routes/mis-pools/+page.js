import { redirect } from '@sveltejs/kit';
import { rutaTab } from '$lib/pestanas.js';

// Redirección real (no un efecto en el cliente): no hay un frame en blanco.
export function load() {
	redirect(307, rutaTab('mios'));
}
