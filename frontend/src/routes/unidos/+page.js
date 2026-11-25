import { redirect } from '@sveltejs/kit';

// Ruta anterior de "Mis reservas": redirección real (no un efecto en el cliente).
export function load() {
	redirect(307, '/mis-reservas');
}
