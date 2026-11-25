/**
 * Pool guardado como borrador en el servidor (módulo puro: sin fetch ni runes).
 * Un borrador se puede guardar a medias: solo piden el título y la categoría; el resto se
 * completa después, y el servidor revisa que esté todo recién al publicar.
 */

/** `{campo: mensaje}` de lo que falta para poder guardar un borrador. */
export function faltantesParaGuardar({ titulo, categoria } = {}) {
	const faltan = {};
	if (!String(titulo ?? '').trim()) faltan.titulo = 'Poné un título para reconocer el borrador.';
	if (!categoria) faltan.categoria = 'Elegí una categoría.';
	return faltan;
}

/** Quita del FormData los campos de texto vacíos: el servidor les pone un valor neutro. */
export function sinCamposVacios(formData) {
	for (const [clave, valor] of [...formData.entries()]) {
		if (typeof valor === 'string' && !valor.trim()) formData.delete(clave);
	}
	return formData;
}

/**
 * `{campo: mensaje}` de lo que le falta a un borrador para publicarse. Espeja
 * `faltantes_para_publicar` del backend (que es el que decide): sirve para mostrar la lista
 * y habilitar o no "Publicar" sin ir al servidor.
 */
export function faltantesParaPublicar(pool, hoy = new Date()) {
	const faltan = {};
	if (!String(pool?.nombre_producto ?? '').trim()) faltan.nombre_producto = 'El producto';
	if (!String(pool?.enlace ?? '').trim()) faltan.enlace = 'El enlace de la tienda';
	if (!(Number(pool?.precio_unitario) > 0)) faltan.precio_unitario = 'El precio por unidad';
	if (!(Number(pool?.cantidad_total) > Number(pool?.cantidad_creador ?? 1))) {
		faltan.cantidad_total = 'Una cantidad total mayor a tu reserva';
	}
	if (!String(pool?.direccion ?? '').trim()) faltan.direccion = 'La dirección';
	if (!String(pool?.ciudad ?? '').trim()) faltan.ciudad = 'La ciudad';
	const hoyISO = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}-${String(hoy.getDate()).padStart(2, '0')}`;
	if (pool?.fecha_caducidad && pool.fecha_caducidad < hoyISO) {
		faltan.fecha_caducidad = 'Una fecha de caducidad nueva (la anterior ya pasó)';
	}
	if (
		pool?.tipo_pago === 'transferencia' &&
		!(String(pool?.alias_cbu ?? '').trim() && String(pool?.titular_cuenta ?? '').trim())
	) {
		faltan.alias_cbu = 'El alias o CBU y el titular para cobrar';
	}
	return faltan;
}
