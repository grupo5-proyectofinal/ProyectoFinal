/**
 * Textos y reglas del historial del pool (contrato de la API, Phase 3).
 *
 * Módulo puro a propósito: sin fetch, sin runes y sin imports, para poder
 * testearlo directo con `node --test`. La página del detalle lo consume.
 */

const CAMPOS = {
	titulo: 'título',
	nombre_producto: 'producto',
	descripcion: 'descripción',
	categoria: 'categoría',
	enlace: 'enlace',
	precio_unitario: 'precio',
	cantidad_total: 'cantidad total',
	cantidad_creador: 'cantidad del creador',
	min_por_integrante: 'mínimo por integrante',
	fecha_caducidad: 'fecha de caducidad',
	tipo_pago: 'tipo de pago',
	direccion: 'dirección',
	ciudad: 'ciudad'
};

const ESTADOS = {
	listo: 'marcó el pool como listo',
	en_curso: 'confirmó el pedido',
	finalizado: 'finalizó el pool',
	cancelado: 'canceló el pool'
};

/** ¿Este usuario integra el pool? (creador o miembro; sin sesión no hay acceso) */
export function esIntegrante(pool, usuarioId) {
	if (!pool || usuarioId === null || usuarioId === undefined) return false;
	if (pool.creador?.id === usuarioId) return true;
	return (pool.miembros ?? []).some((m) => m.usuario?.id === usuarioId);
}

const FECHA_HORA = new Intl.DateTimeFormat('es-AR', {
	day: 'numeric',
	month: 'short',
	year: 'numeric',
	hour: '2-digit',
	minute: '2-digit'
});

/** Fecha y hora de un evento ISO: "5 oct 2026, 14:30". Vacío si no es válida. */
export function fechaHora(valor) {
	if (!valor) return '';
	const d = new Date(valor);
	return Number.isNaN(d.getTime()) ? '' : FECHA_HORA.format(d);
}

function quien(evento) {
	return evento?.actor?.username || 'El sistema';
}

/**
 * Texto es-AR de un evento. Solo lee `tipo`, `actor` y las claves conocidas de
 * `datos`: nunca interpola el resto (el historial no expone PII del miembro).
 */
export function textoEvento(evento) {
	const datos = evento?.datos ?? {};
	switch (evento?.tipo) {
		case 'creado':
			return `${quien(evento)} creó el pool.`;
		case 'edicion': {
			const campos = (datos.campos ?? []).map((campo) => CAMPOS[campo] ?? campo);
			return campos.length
				? `${quien(evento)} editó el pool (${campos.join(', ')}).`
				: `${quien(evento)} editó el pool.`;
		}
		case 'imagen':
			return datos.accion === 'eliminada'
				? `${quien(evento)} eliminó una imagen.`
				: `${quien(evento)} agregó una imagen.`;
		case 'union':
			return `${quien(evento)} se unió al pool (${datos.cantidad} u.).`;
		case 'salida':
			return `${quien(evento)} salió del pool (${datos.cantidad} u.).`;
		case 'cantidad':
			return `${quien(evento)} cambió su cantidad de ${datos.antes} a ${datos.despues} u.`;
		case 'estado':
			return ESTADOS[datos.estado]
				? `${quien(evento)} ${ESTADOS[datos.estado]}.`
				: `${quien(evento)} cambió el estado del pool.`;
		case 'expirado':
			return 'El pool venció y se canceló automáticamente.';
		case 'solicitud_eliminacion':
			return `${quien(evento)} solicitó eliminar el pool.`;
		case 'voto_eliminacion':
			return datos.acepta
				? `${quien(evento)} votó a favor de eliminar el pool.`
				: `${quien(evento)} votó en contra de eliminar el pool.`;
		default:
			return `${quien(evento)} hizo un cambio en el pool.`;
	}
}
