// Preferencia de "reducir movimiento" del sistema.
// La regla global de app.css solo apaga animaciones CSS: las transiciones de
// Svelte (Web Animations API) y las View Transitions hay que cortarlas desde JS.

export function prefiereMenosMovimiento() {
	return (
		typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches
	);
}

/** Duración en ms para transiciones de Svelte: 0 si se pidió menos movimiento. */
export function duracion(ms) {
	return prefiereMenosMovimiento() ? 0 : ms;
}
