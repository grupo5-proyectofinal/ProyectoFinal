import { test } from 'node:test';
import assert from 'node:assert/strict';

import { consultaDireccion, moverActivo } from '../src/lib/direcciones.js';

test('consultaDireccion no busca con menos de 4 letras', () => {
	assert.equal(consultaDireccion(''), '');
	assert.equal(consultaDireccion('  co '), '');
	assert.equal(consultaDireccion(undefined), '');
});

test('consultaDireccion suma la ciudad solo si todavía no está en el texto', () => {
	assert.equal(consultaDireccion('Colón 100'), 'Colón 100');
	assert.equal(consultaDireccion('Colón 100', 'Córdoba'), 'Colón 100, Córdoba');
	assert.equal(consultaDireccion('Colón 100, Córdoba', 'córdoba'), 'Colón 100, Córdoba');
});

test('moverActivo recorre las opciones y da la vuelta', () => {
	assert.equal(moverActivo(-1, 3, 'ArrowDown'), 0);
	assert.equal(moverActivo(2, 3, 'ArrowDown'), 0);
	assert.equal(moverActivo(0, 3, 'ArrowUp'), 2);
	assert.equal(moverActivo(-1, 3, 'ArrowUp'), 2);
	assert.equal(moverActivo(1, 0, 'ArrowDown'), -1);
	assert.equal(moverActivo(1, 3, 'Home'), 1);
});
