export const toasts = $state([]);

const DURACION = { error: 8000, aviso: 6000, exito: 4000, info: 4000 };
const MAX = 3;

let contador = 0;
const temporizadores = new Map();

/** Muestra un aviso breve. tipo: exito | error | aviso | info */
export function notificar(mensaje, tipo = 'exito') {
	const id = ++contador;
	toasts.push({ id, mensaje, tipo });

	while (toasts.length > MAX) {
		limpiar(toasts[0].id);
		toasts.shift();
	}

	temporizadores.set(id, setTimeout(() => cerrar(id), DURACION[tipo] ?? 4000));
	return id;
}

function limpiar(id) {
	clearTimeout(temporizadores.get(id));
	temporizadores.delete(id);
}

export function cerrar(id) {
	limpiar(id);
	const i = toasts.findIndex((t) => t.id === id);
	if (i !== -1) toasts.splice(i, 1);
}
