// Mensajes de error al subir imágenes (módulo puro, testeable con node --test).

/** Motivo legible de por qué una imagen no se subió. */
export function motivoImagen(error) {
	const imagen = error?.data?.imagen ?? error?.data?.foto;
	if (imagen) return Array.isArray(imagen) ? imagen.join(' ') : String(imagen);
	if (error?.data?.detail) return String(error.data.detail);
	if (error?.status === 413) return 'el archivo es demasiado grande.';
	if (error?.status === 401) return 'tu sesión expiró.';
	return 'error del servidor. Probá de nuevo en un rato.';
}
