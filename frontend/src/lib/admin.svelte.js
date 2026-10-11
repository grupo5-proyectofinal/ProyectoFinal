import { goto } from '$app/navigation';
import { resolve } from '$app/paths';

import { SIN_ACCESO } from './admin.js';
import { loadMe } from './session.svelte.js';
import { notificar } from './toast.svelte.js';

/** La sesión perdió el rol de staff: avisa, refresca el usuario y vuelve al inicio. */
export function alPerderAcceso() {
	notificar(SIN_ACCESO, 'error');
	loadMe();
	goto(resolve('/'));
}
