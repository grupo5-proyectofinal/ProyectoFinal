import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
	MAX_COMPROBANTE,
	etiquetaEstadoPago,
	faltanPagos,
	faltanRecepciones,
	monto,
	puedeConfirmarPedido,
	puedeConfirmarRecepcion,
	puedeFinalizar,
	puedeSubirComprobante,
	resumenMontos,
	resumenPagos,
	resumenRecepcion,
	tieneDatosCobro,
	validarComprobante
} from '../src/lib/pagos.js';

function miembro(id, extra = {}) {
	return { id, usuario: { id }, cantidad: 2, pago_estado: 'pendiente', recepcion_confirmada: null, ...extra };
}

function pool(estado, miembros) {
	return { estado, precio_unitario: '150.50', miembros };
}

test('etiquetaEstadoPago: texto y variante por estado, pendiente por defecto', () => {
	assert.deepEqual(etiquetaEstadoPago('confirmado'), { texto: 'Pago confirmado', variante: 'abierto' });
	assert.equal(etiquetaEstadoPago('rechazado').texto, 'Rechazado');
	assert.equal(etiquetaEstadoPago(undefined).texto, 'Sin comprobante');
});

test('monto: usa el de la API y si falta lo calcula', () => {
	const p = pool('listo', []);
	assert.equal(monto(p, { monto: '300.00', cantidad: 2 }), 300);
	assert.equal(monto(p, { cantidad: 2 }), 301);
});

test('resumenPagos y resumenRecepcion cuentan por estado', () => {
	const p = pool('en_curso', [
		miembro(1, { pago_estado: 'confirmado', recepcion_confirmada: '2026-11-02T10:00:00Z' }),
		miembro(2, { pago_estado: 'enviado' }),
		miembro(3)
	]);
	assert.deepEqual(resumenPagos(p), { confirmados: 1, enviados: 1, total: 3 });
	assert.deepEqual(resumenRecepcion(p), { recibieron: 1, total: 3 });
});

test('puedeConfirmarPedido: solo en listo y con todos los pagos confirmados', () => {
	const pagados = [miembro(1, { pago_estado: 'confirmado' })];
	assert.equal(puedeConfirmarPedido(pool('listo', pagados)), true);
	assert.equal(puedeConfirmarPedido(pool('listo', [])), true);
	assert.equal(puedeConfirmarPedido(pool('listo', [...pagados, miembro(2)])), false);
	assert.equal(puedeConfirmarPedido(pool('abierto', pagados)), false);
});

test('puedeFinalizar: solo en curso y con todas las recepciones', () => {
	const recibido = miembro(1, { recepcion_confirmada: '2026-11-02T10:00:00Z' });
	assert.equal(puedeFinalizar(pool('en_curso', [recibido])), true);
	assert.equal(puedeFinalizar(pool('en_curso', [recibido, miembro(2)])), false);
	assert.equal(puedeFinalizar(pool('listo', [recibido])), false);
});

test('puedeSubirComprobante y puedeConfirmarRecepcion', () => {
	assert.equal(puedeSubirComprobante(pool('listo', []), miembro(1)), true);
	assert.equal(puedeSubirComprobante(pool('listo', []), miembro(1, { pago_estado: 'rechazado' })), true);
	assert.equal(puedeSubirComprobante(pool('listo', []), miembro(1, { pago_estado: 'confirmado' })), false);
	assert.equal(puedeSubirComprobante(pool('en_curso', []), miembro(1)), false);
	assert.equal(puedeSubirComprobante(pool('listo', []), null), false);
	assert.equal(puedeConfirmarRecepcion(pool('en_curso', []), miembro(1)), true);
	assert.equal(
		puedeConfirmarRecepcion(pool('en_curso', []), miembro(1, { recepcion_confirmada: 'x' })),
		false
	);
	assert.equal(puedeConfirmarRecepcion(pool('listo', []), miembro(1)), false);
});

test('faltanPagos y faltanRecepciones: singular y plural', () => {
	assert.equal(faltanPagos(pool('listo', [miembro(1)])), 'Falta confirmar 1 pago.');
	assert.equal(faltanPagos(pool('listo', [miembro(1), miembro(2)])), 'Faltan confirmar 2 pagos.');
	assert.equal(
		faltanRecepciones(pool('en_curso', [miembro(1)])),
		'Falta que 1 participante confirme la recepción.'
	);
});

test('validarComprobante: tipo y tamaño como el backend', () => {
	assert.equal(validarComprobante({ type: 'image/png', size: 100 }), '');
	assert.equal(validarComprobante({ type: 'application/pdf', size: MAX_COMPROBANTE }), '');
	assert.match(validarComprobante({ type: 'image/gif', size: 100 }), /JPEG, PNG o PDF/);
	assert.match(validarComprobante({ type: 'image/jpeg', size: MAX_COMPROBANTE + 1 }), /5 MB/);
	assert.match(validarComprobante(null), /Elegí/);
});

test('resumenMontos: recaudado confirmado contra lo que deben los integrantes', () => {
	const p = pool('listo', [
		miembro(1, { pago_estado: 'confirmado', monto: '301.00' }),
		miembro(2, { pago_estado: 'enviado' }),
		miembro(3, { pago_estado: 'rechazado', cantidad: 1 })
	]);
	// 301 + 2×150.50 + 1×150.50
	assert.deepEqual(resumenMontos(p), { confirmado: 301, esperado: 752.5 });
	assert.deepEqual(resumenMontos({ miembros: [] }), { confirmado: 0, esperado: 0 });
});

test('tieneDatosCobro: solo con alias o CBU cargado', () => {
	assert.equal(tieneDatosCobro({ alias_cbu: 'ana.mp' }), true);
	assert.equal(tieneDatosCobro({ alias_cbu: '  ' }), false);
	assert.equal(tieneDatosCobro({}), false);
});
