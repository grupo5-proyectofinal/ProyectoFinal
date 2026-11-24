import { redirect } from '@sveltejs/kit';
import { rutaTab } from '$lib/pestanas.js';

// Los enlaces viejos `/pools?tab=mios|unidos` (guardados, de notificaciones) llevan a la
// sección que ahora tiene su propia ruta, conservando los filtros.
export function load({ url }) {
	const tab = url.searchParams.get('tab');
	if (tab === 'mios' || tab === 'unidos') redirect(307, rutaTab(tab, url.searchParams));
}
