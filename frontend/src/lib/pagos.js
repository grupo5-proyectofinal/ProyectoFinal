/**
 * Reglas y textos de los pagos con comprobante y de la confirmación de
 * recepción (contrato de la API: `miembros[].pago_estado`, `monto`,
 * `recepcion_confirmada`, `pago_motivo_rechazo`, `tiene_comprobante`).
 *
 * Módulo puro: sin fetch ni runes, para testearlo con `node --test`.
 */

/** Texto y variante de `Badge` por estado de pago. */
export const ESTADOS_PAGO = {
	pendiente: { texto: 'Sin comprobante', variante: 'neutro' },
	enviado: { texto: 'Por revisar', variante: 'en_curso' },
	confirmado: { texto: 'Pago confirmado', variante: 'abierto' },
	rechazado: { texto: 'Rechazado', variante: 'cancelado' }
};

export function etiquetaEstadoPago(estado) {
	return ESTADOS_PAGO[estado] ?? ESTADOS_PAGO.pendiente;
}

/** Monto que le toca pagar al miembro (la API lo manda; si falta, se calcula). */
export function monto(pool, miembro) {
	if (miembro?.monto !== undefined && miembro?.monto !== null) return Number(miembro.monto);
	return Number(pool?.precio_unitario ?? 0) * Number(miembro?.cantidad ?? 0);
}

/** `{confirmados, enviados, total}` de los pagos de los miembros. */
export function resumenPagos(pool) {
	const miembros = pool?.miembros ?? [];
	return {
		confirmados: miembros.filter((m) => m.pago_estado === 'confirmado').length,
		enviados: miembros.filter((m) => m.pago_estado === 'enviado').length,
		total: miembros.length
	};
}

/** `{recibieron, total}` de las confirmaciones de recepción. */
export function resumenRecepcion(pool) {
	const miembros = pool?.miembros ?? [];
	return {
		recibieron: miembros.filter((m) => Boolean(m.recepcion_confirmada)).length,
		total: miembros.length
	};
}

/** ¿El creador puede confirmar el pedido? Listo y con todos los pagos confirmados. */
export function puedeConfirmarPedido(pool) {
	if (pool?.estado !== 'listo') return false;
	const { confirmados, total } = resumenPagos(pool);
	return confirmados === total;
}

/** ¿El creador puede finalizar? En curso y con todas las recepciones confirmadas. */
export function puedeFinalizar(pool) {
	if (pool?.estado !== 'en_curso') return false;
	const { recibieron, total } = resumenRecepcion(pool);
	return recibieron === total;
}

/** ¿El miembro puede subir/reemplazar su comprobante? */
export function puedeSubirComprobante(pool, miembro) {
	return pool?.estado === 'listo' && Boolean(miembro) && miembro.pago_estado !== 'confirmado';
}

/** ¿El miembro puede confirmar que recibió el producto? */
export function puedeConfirmarRecepcion(pool, miembro) {
	return pool?.estado === 'en_curso' && Boolean(miembro) && !miembro.recepcion_confirmada;
}

/** "1 pago" / "N pagos" — para los avisos de qué falta. */
export function faltanPagos(pool) {
	const { confirmados, total } = resumenPagos(pool);
	const faltan = total - confirmados;
	return faltan === 1 ? 'Falta confirmar 1 pago.' : `Faltan confirmar ${faltan} pagos.`;
}

export function faltanRecepciones(pool) {
	const { recibieron, total } = resumenRecepcion(pool);
	const faltan = total - recibieron;
	return faltan === 1
		? 'Falta que 1 participante confirme la recepción.'
		: `Falta que ${faltan} participantes confirmen la recepción.`;
}

export const TIPOS_COMPROBANTE = ['image/jpeg', 'image/png', 'application/pdf'];
export const MAX_COMPROBANTE = 5 * 1024 * 1024;

/** Mensaje de error del archivo elegido, o '' si es válido (mismos límites que el backend). */
export function validarComprobante(archivo) {
	if (!archivo) return 'Elegí el archivo del comprobante.';
	if (!TIPOS_COMPROBANTE.includes(archivo.type)) {
		return 'Solo se aceptan comprobantes JPEG, PNG o PDF.';
	}
	if (archivo.size > MAX_COMPROBANTE) return 'El comprobante no puede superar los 5 MB.';
	return '';
}
