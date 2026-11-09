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

/**
 * Reinicia una animación CSS de una sola vez: saca la clase, fuerza el reflow y
 * la vuelve a poner. Se limpia sola al terminar para poder repetirla.
 */
export function animarUnaVez(elemento, clase) {
	if (!elemento) return;
	elemento.classList.remove(clase);
	void elemento.offsetWidth;
	elemento.classList.add(clase);
	// animationend burbujea: solo cuenta el del propio elemento.
	const alTerminar = (evento) => {
		if (evento.target !== elemento) return;
		elemento.classList.remove(clase);
		elemento.removeEventListener('animationend', alTerminar);
	};
	elemento.addEventListener('animationend', alTerminar);
}
