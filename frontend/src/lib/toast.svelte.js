export const toasts = $state([]);

let contador = 0;

/** Muestra un aviso breve. tipo: exito | error | aviso | info */
export function notificar(mensaje, tipo = 'exito') {
	const id = ++contador;
	toasts.push({ id, mensaje, tipo });
	setTimeout(() => cerrar(id), 4500);
	return id;
}

export function cerrar(id) {
	const i = toasts.findIndex((t) => t.id === id);
	if (i !== -1) toasts.splice(i, 1);
}
