import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
	COLORES_CONFETI,
	avanceLinea,
	clave,
	debeFestejar,
	leerVistos,
	marcarVisto,
	piezasConfeti
} from '../src/lib/festejo.js';

function almacenFalso(inicial = {}) {
	const datos = { ...inicial };
	return {
		getItem: (k) => datos[k] ?? null,
		setItem: (k, v) => {
			datos[k] = String(v);
		}
	};
}

const pool = {
	id: 7,
	estado: 'en_curso',
	creador: { id: 1 },
	miembros: [{ usuario: { id: 2 } }]
};

test('debeFestejar: creador y miembro de un pool en curso', () => {
	assert.equal(debeFestejar(pool, 1, []), true);
	assert.equal(debeFestejar(pool, 2, []), true);
});

test('debeFestejar: no para quien no participa, sin sesión u otro estado', () => {
	assert.equal(debeFestejar(pool, 3, []), false);
	assert.equal(debeFestejar(pool, null, []), false);
	assert.equal(debeFestejar({ ...pool, estado: 'listo' }, 1, []), false);
	assert.equal(debeFestejar({ ...pool, estado: 'finalizado' }, 1, []), false);
	assert.equal(debeFestejar(null, 1, []), false);
});

test('debeFestejar: una sola vez por pool y usuario', () => {
	assert.equal(debeFestejar(pool, 1, [clave(7, 1)]), false);
	// Otro usuario en el mismo navegador todavía no lo vio.
	assert.equal(debeFestejar(pool, 2, [clave(7, 1)]), true);
});

test('marcarVisto guarda y leerVistos recupera', () => {
	const almacen = almacenFalso();
	marcarVisto(almacen, 7, 1);
	marcarVisto(almacen, 7, 1);
	assert.deepEqual(leerVistos(almacen), ['1:7']);
});

test('leerVistos tolera datos rotos o almacenamiento ausente', () => {
	assert.deepEqual(leerVistos(almacenFalso({ 'poolshop:festejos': '{no json' })), []);
	assert.deepEqual(leerVistos(almacenFalso({ 'poolshop:festejos': '{"a":1}' })), []);
	assert.deepEqual(leerVistos(undefined), []);
});

test('marcarVisto no rompe si el almacenamiento falla al escribir', () => {
	const almacen = {
		getItem: () => null,
		setItem: () => {
			throw new Error('QuotaExceededError');
		}
	};
	assert.deepEqual(marcarVisto(almacen, 7, 1), ['1:7']);
});

test('marcarVisto conserva solo los últimos 200', () => {
	const almacen = almacenFalso();
	for (let i = 0; i < 205; i++) marcarVisto(almacen, i, 1);
	const vistos = leerVistos(almacen);
	assert.equal(vistos.length, 200);
	assert.equal(vistos[0], '1:5');
	assert.equal(vistos.at(-1), '1:204');
});

test('piezasConfeti arma piezas dentro de rango con los colores de la marca', () => {
	const piezas = piezasConfeti(12, () => 0.5);
	assert.equal(piezas.length, 12);
	for (const p of piezas) {
		assert.ok(p.x >= 0 && p.x <= 100);
		assert.ok(COLORES_CONFETI.includes(p.color));
		assert.ok(p.duracion >= 1400 && p.duracion <= 2300);
	}
	assert.equal(piezas[0].forma, 'tira');
	assert.equal(piezas[1].forma, 'cuadro');
});

test('avanceLinea', () => {
	assert.equal(avanceLinea(0, 4), 0);
	assert.equal(avanceLinea(2, 4), 67);
	assert.equal(avanceLinea(3, 4), 100);
	assert.equal(avanceLinea(-1, 4), 0);
	assert.equal(avanceLinea(5, 4), 100);
	assert.equal(avanceLinea(0, 1), 0);
});
