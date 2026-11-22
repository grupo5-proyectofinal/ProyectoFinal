/**
 * Contrato de unión con datos (Plan 3, Fase 1).
 *
 * Módulo puro a propósito (sin runes ni fetch) para poder testearlo con
 * `node --test`. Arma el payload `{cantidad, telefono, mensaje}` que espera
 * el endpoint `POST /pools/{id}/unirse/`: cantidad numérica y textos recortados.
 * El servidor vuelve a validar teléfono (formato/largo) en el boundary.
 */

/**
 * Payload de unirse: cantidad numérica y campos de texto recortados. En pools con
 * variantes (talle/color) va también `detalle`: [{atributos, cantidad}].
 */
export function payloadUnion(cantidad, telefono, mensaje, detalle) {
	return {
		cantidad: Number(cantidad),
		telefono: (telefono ?? '').trim(),
		mensaje: (mensaje ?? '').trim(),
		...(detalle ? { detalle } : {})
	};
}

const unidades = (n) => `${n} ${n === 1 ? 'unidad' : 'unidades'}`;

/**
 * Ayuda del campo "Tu reserva" para quien ya está en el pool. El tope es su
 * reserva actual + lo que falta: sin aclararlo, "hasta 13" con "Faltan 12" en la
 * barra parecía un error.
 */
export function ayudaMiReserva(actual, disponible) {
	if (disponible <= 0) return `Ya reservaste ${unidades(actual)}. El cupo está completo: podés bajarla.`;
	return `Ya reservaste ${unidades(actual)} y quedan ${disponible} libres: tu reserva puede llegar a ${actual + disponible}.`;
}
