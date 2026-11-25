// Mensajes de error al subir imágenes (módulo puro, testeable con node --test).

/**
 * Suma las imágenes recién elegidas a las que ya estaban, sin repetir las que
 * son iguales y sin pasar de `maximo`. Antes, elegir fotos de nuevo pisaba la
 * selección anterior.
 */
export function sumarImagenes(actuales, nuevas, maximo) {
	const clave = (a) => `${a.name}|${a.size}|${a.lastModified}`;
	const vistas = new Set(actuales.map(clave));
	const lista = [...actuales];
	for (const archivo of nuevas) {
		if (vistas.has(clave(archivo))) continue;
		vistas.add(clave(archivo));
		lista.push(archivo);
	}
	return { lista: lista.slice(0, maximo), excedidas: Math.max(lista.length - maximo, 0) };
}

/** Motivo legible de por qué una imagen no se subió. */
export function motivoImagen(error) {
	const imagen = error?.data?.imagen ?? error?.data?.foto;
	if (imagen) return Array.isArray(imagen) ? imagen.join(' ') : String(imagen);
	if (error?.data?.detail) return String(error.data.detail);
	if (error?.status === 413) return 'el archivo es demasiado grande.';
	if (error?.status === 401) return 'tu sesión expiró.';
	return 'error del servidor. Probá de nuevo en un rato.';
}
