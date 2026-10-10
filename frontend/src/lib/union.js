/**
 * Contrato de unión con datos (Plan 3, Fase 1).
 *
 * Módulo puro a propósito (sin runes ni fetch) para poder testearlo con
 * `node --test`. Arma el payload `{cantidad, telefono, mensaje}` que espera
 * el endpoint `POST /pools/{id}/unirse/`: cantidad numérica y textos recortados.
 * El servidor vuelve a validar teléfono (formato/largo) en el boundary.
 */

/** Payload de unirse: cantidad numérica y campos de texto recortados. */
export function payloadUnion(cantidad, telefono, mensaje) {
	return {
		cantidad: Number(cantidad),
		telefono: (telefono ?? '').trim(),
		mensaje: (mensaje ?? '').trim()
	};
}
