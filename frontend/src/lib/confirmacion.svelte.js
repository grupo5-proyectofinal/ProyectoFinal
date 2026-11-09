// Confirmaciones con el Dialogo del sistema en vez del confirm() nativo.
// Un solo diálogo vive en el layout (<Confirmacion />); cualquier página pide
// confirmación con `await confirmar({...})`, que devuelve true o false.

export const confirmacion = $state({
	abierta: false,
	titulo: '',
	descripcion: '',
	confirmar: 'Confirmar',
	variante: 'peligro-suave'
});

let resolver = null;

/** Abre el diálogo y espera la respuesta. Una confirmación nueva cancela la anterior. */
export function confirmar({ titulo, descripcion = '', confirmar = 'Confirmar', variante = 'peligro-suave' }) {
	resolver?.(false);
	Object.assign(confirmacion, { abierta: true, titulo, descripcion, confirmar, variante });
	return new Promise((resolve) => (resolver = resolve));
}

/** Cierra el diálogo con la respuesta del usuario. */
export function responder(aceptada) {
	confirmacion.abierta = false;
	const pendiente = resolver;
	resolver = null;
	pendiente?.(aceptada);
}
