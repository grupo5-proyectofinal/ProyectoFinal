import assert from 'node:assert/strict';
import test from 'node:test';

import {
	diasParaResponder,
	puedeExtender,
	rangoExtension,
	reconfirmacionPendiente,
	resumenReconfirmacion
} from '../src/lib/caducidad.js';

const pool = (extra = {}) => ({
	estado: 'caducado',
	creador: { id: 1 },
	miembros: [
		{ usuario: { id: 2 }, reconfirmado: null },
		{ usuario: { id: 3 }, reconfirmado: '2026-10-01T10:00:00Z' }
	],
	...extra
});

test('solo el creador extiende, y solo con el pool caducado', () => {
	assert.equal(puedeExtender(pool(), 1), true);
	assert.equal(puedeExtender(pool(), 2), false);
	assert.equal(puedeExtender(pool({ estado: 'abierto' }), 1), false);
});

test('el rango de extensión deja pasar el plazo de reconfirmación y topea a 30 días', () => {
	const { min, max } = rangoExtension(new Date(2026, 9, 1));
	assert.equal(min, '2026-10-05');
	assert.equal(max, '2026-10-31');
});

test('pendiente solo si el pool espera confirmaciones y el usuario no respondió', () => {
	const esperando = pool({ estado: 'reconfirmacion' });
	assert.equal(reconfirmacionPendiente(esperando, 2)?.usuario.id, 2);
	assert.equal(reconfirmacionPendiente(esperando, 3), null);
	assert.equal(reconfirmacionPendiente(esperando, 1), null);
	assert.equal(reconfirmacionPendiente(pool(), 2), null);
});

test('resumen de respuestas', () => {
	assert.deepEqual(resumenReconfirmacion(pool()), { respondieron: 1, faltan: 1 });
});

test('días para responder redondea hacia arriba y no baja de 0', () => {
	const ahora = new Date('2026-10-01T12:00:00Z');
	assert.equal(diasParaResponder({ reconfirmacion_hasta: '2026-10-03T13:00:00Z' }, ahora), 3);
	assert.equal(diasParaResponder({ reconfirmacion_hasta: '2026-09-30T00:00:00Z' }, ahora), 0);
	assert.equal(diasParaResponder({}, ahora), 0);
});

test('muestraPlazo: "caduca en…" solo donde la fecha todavía rige', async () => {
	const { muestraPlazo } = await import('../src/lib/caducidad.js');
	for (const estado of ['borrador', 'abierto', 'caducado', 'reconfirmacion']) {
		assert.equal(muestraPlazo(estado), true, estado);
	}
	for (const estado of ['listo', 'en_curso', 'finalizado', 'cancelado']) {
		assert.equal(muestraPlazo(estado), false, estado);
	}
});

test('rangoReapertura: desde mañana hasta 30 días', async () => {
	const { rangoReapertura } = await import('../src/lib/caducidad.js');
	assert.deepEqual(rangoReapertura(new Date(2026, 10, 24)), {
		min: '2026-11-25',
		max: '2026-12-24'
	});
});
