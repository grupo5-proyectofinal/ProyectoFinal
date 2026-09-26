export function etiquetaEstado(estado) {
	return estado.replace('_', ' ').replace(/^./, (c) => c.toUpperCase());
}
