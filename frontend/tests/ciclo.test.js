import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
	estadosFiltrables,
	etiquetaEstado,
	puedeCancelar,
	puedeDuplicar,
	puedeEditar,
	puedePublicar,
	puedeReabrir
} from '../src/lib/estados.js';

const creador = 7;
const pool = (estado, integrantes = 1) => ({ estado, integrantes, creador: { id: creador } });

test('el borrador tiene etiqueta y se edita y publica solo por su creador', () => {
	assert.equal(etiquetaEstado('borrador'), 'Borrador');
	assert.equal(puedeEditar(pool('borrador'), creador), true);
	assert.equal(puedeEditar(pool('borrador'), 8), false);
	assert.equal(puedePublicar(pool('borrador'), creador), true);
	assert.equal(puedePublicar(pool('abierto'), creador), false);
	assert.equal(puedePublicar(pool('borrador'), 8), false);
});

test('cancelar: solo estados activos; finalizado y cancelado son finales', () => {
	for (const estado of ['borrador', 'abierto', 'listo', 'caducado', 'reconfirmacion', 'en_curso']) {
		assert.equal(puedeCancelar(pool(estado), creador), true, estado);
	}
	for (const estado of ['finalizado', 'cancelado']) {
		assert.equal(puedeCancelar(pool(estado), creador), false, estado);
	}
	assert.equal(puedeCancelar(pool('abierto'), 8), false);
});

test('reabrir: cancelado y sin integrantes; duplicar: cancelado o finalizado', () => {
	assert.equal(puedeReabrir(pool('cancelado', 1), creador), true);
	assert.equal(puedeReabrir(pool('cancelado', 3), creador), false, 'ya tuvo integrantes');
	assert.equal(puedeReabrir(pool('abierto', 1), creador), false);
	assert.equal(puedeReabrir(pool('cancelado', 1), 8), false);
	assert.equal(puedeDuplicar(pool('cancelado', 3), creador), true);
	assert.equal(puedeDuplicar(pool('finalizado', 3), creador), true);
	assert.equal(puedeDuplicar(pool('en_curso', 3), creador), false);
	assert.equal(puedeDuplicar(pool('cancelado', 3), 8), false);
});

test('seccionDelPool: organizo → mios, reservé → unidos, si no → Explorar', async () => {
	const { seccionDelPool } = await import('../src/lib/estados.js');
	const base = { creador: { id: 7 }, miembros: [{ usuario: { id: 9 } }] };
	assert.equal(seccionDelPool(base, 7), 'mios');
	assert.equal(seccionDelPool(base, 9), 'unidos');
	assert.equal(seccionDelPool(base, 3), null);
	assert.equal(seccionDelPool(base, undefined), null);
	assert.equal(seccionDelPool(null, 7), null);
});

test('Mis reservas no ofrece filtrar por Caducado ni Borrador; Mis pools ofrece todos', () => {
	const reservas = estadosFiltrables('unidos');
	assert.ok(!reservas.includes('caducado'));
	assert.ok(!reservas.includes('borrador'));
	assert.ok(reservas.includes('reconfirmacion'));
	assert.ok(estadosFiltrables('mios').includes('caducado'));
	assert.ok(estadosFiltrables('mios').includes('borrador'));
	assert.deepEqual(estadosFiltrables('todos'), []);
});
