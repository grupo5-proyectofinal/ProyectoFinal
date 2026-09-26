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
