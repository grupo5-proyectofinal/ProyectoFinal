export function etiquetaEstado(estado) {
	return estado.replace('_', ' ').replace(/^./, (c) => c.toUpperCase());
}

const PAGOS = {
	efectivo: 'Efectivo',
	transferencia: 'Transferencia',
	sin_especificar: 'Sin especificar'
};

export function etiquetaPago(valor) {
	return PAGOS[valor] ?? valor;
}

export const TONOS = ['azul', 'verde', 'ambar', 'coral', 'violeta', 'teal'];

/** Tono estable a partir del id de una categoría. */
export function tonoCategoria(id) {
	return TONOS[Math.abs(Math.trunc(Number(id))) % TONOS.length || 0];
}

/** Tono estable a partir de un texto (avatares/monogramas). */
export function tonoNombre(texto) {
	const suma = [...(texto ?? '').toLowerCase()].reduce((s, c) => s + c.codePointAt(0), 0);
	return TONOS[suma % TONOS.length];
}
