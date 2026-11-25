import assert from 'node:assert/strict';
import test from 'node:test';

import { accionesBaja, etiquetaBaja, hayBajas, puedePedirBaja } from '../src/lib/bajas.js';

const pool = (estado = 'listo') => ({ estado, creador: { id: 1 } });
const miembro = (pago = 'enviado') => ({ pago_estado: pago });

test('pide la baja con pool listo o en curso y el pago ya enviado', () => {
	assert.equal(puedePedirBaja(pool('listo'), miembro('enviado')), true);
	assert.equal(puedePedirBaja(pool('en_curso'), miembro('confirmado')), true);
});

test('no pide la baja sin pago, fuera de listo/en curso ni con un pedido pendiente', () => {
	assert.equal(puedePedirBaja(pool('listo'), miembro('pendiente')), false);
	assert.equal(puedePedirBaja(pool('listo'), miembro('rechazado')), false);
	assert.equal(puedePedirBaja(pool('abierto'), miembro('enviado')), false);
	assert.equal(puedePedirBaja(pool('finalizado'), miembro('confirmado')), false);
	assert.equal(puedePedirBaja(pool('listo'), null), false);
	assert.equal(puedePedirBaja(pool('listo'), miembro(), [{ estado: 'pendiente' }]), false);
	// Una rechazada anterior no impide volver a pedirla.
	assert.equal(puedePedirBaja(pool('listo'), miembro(), [{ estado: 'rechazada' }]), true);
});

test('el creador resuelve y marca la devolución; el dueño la confirma', () => {
	const de = (estado) => ({ estado, usuario: { id: 2 } });
	assert.deepEqual(accionesBaja(de('pendiente'), 1, 1), {
		resolver: true,
		marcarDevuelta: false,
		confirmarRecibida: false
	});
	assert.equal(accionesBaja(de('aprobada'), 1, 1).marcarDevuelta, true);
	assert.equal(accionesBaja(de('devuelta'), 2, 1).confirmarRecibida, true);
	assert.equal(accionesBaja(de('devuelta'), 1, 1).confirmarRecibida, false);
	assert.equal(accionesBaja(de('pendiente'), 2, 1).resolver, false);
});

test('etiquetas por estado, con pendiente como respaldo', () => {
	assert.equal(etiquetaBaja('aprobada').texto, 'Esperando devolución');
	assert.equal(etiquetaBaja('confirmada').texto, 'Devolución recibida');
	assert.equal(etiquetaBaja('nada').texto, 'Esperando respuesta');
	assert.equal(hayBajas([]), false);
	assert.equal(hayBajas([{}]), true);
});
