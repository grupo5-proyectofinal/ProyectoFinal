/**
 * Baja de un integrante que ya pagó, con devolución coordinada fuera de la app
 * (módulo puro: sin fetch ni runes, se testea con `node --test`).
 *
 * Espeja `SolicitudBaja` del backend: pendiente → aprobada → devuelta →
 * confirmada, o pendiente → rechazada.
 */

export const ESTADOS_BAJA = {
	pendiente: { texto: 'Esperando respuesta', variante: 'en_curso' },
	rechazada: { texto: 'Rechazada', variante: 'cancelado' },
	aprobada: { texto: 'Esperando devolución', variante: 'en_curso' },
	devuelta: { texto: 'Devolución realizada', variante: 'listo' },
	confirmada: { texto: 'Devolución recibida', variante: 'finalizado' }
};

export function etiquetaBaja(estado) {
	return ESTADOS_BAJA[estado] ?? ESTADOS_BAJA.pendiente;
}

/** ¿Este integrante puede pedir la baja? Con el pool listo o en curso y el pago ya enviado. */
export function puedePedirBaja(pool, miembro, solicitudes = []) {
	if (!miembro) return false;
	if (pool?.estado !== 'listo' && pool?.estado !== 'en_curso') return false;
	if (miembro.pago_estado !== 'enviado' && miembro.pago_estado !== 'confirmado') return false;
	return !solicitudes.some((s) => s.estado === 'pendiente');
}

/** Qué puede hacer el usuario con una solicitud: resolver, marcar la devolución o confirmarla. */
export function accionesBaja(solicitud, usuarioId, creadorId) {
	const esCreador = usuarioId === creadorId;
	const esDuenio = solicitud?.usuario?.id === usuarioId;
	return {
		resolver: esCreador && solicitud?.estado === 'pendiente',
		marcarDevuelta: esCreador && solicitud?.estado === 'aprobada',
		confirmarRecibida: esDuenio && solicitud?.estado === 'devuelta'
	};
}

/** ¿Hay algo para mostrar en el panel? (pedidos propios o, para el creador, de cualquiera) */
export function hayBajas(solicitudes = []) {
	return solicitudes.length > 0;
}
