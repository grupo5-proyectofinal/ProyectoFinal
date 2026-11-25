import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
	consultaDireccion,
	moverActivo,
	parametrosBusqueda,
	textoAlElegir
} from '../src/lib/direcciones.js';

test('consultaDireccion no busca con menos de 4 letras', () => {
	assert.equal(consultaDireccion(''), '');
	assert.equal(consultaDireccion('  co '), '');
	assert.equal(consultaDireccion(undefined), '');
});

test('parametrosBusqueda manda la ciudad y la ubicación aparte de lo escrito', () => {
	assert.equal(parametrosBusqueda('Bel', 'Corrientes'), null);
	assert.deepEqual(parametrosBusqueda('Belgrano 740'), { q: 'Belgrano 740' });
	assert.deepEqual(parametrosBusqueda(' Belgrano 740 ', ' Corrientes '), {
		q: 'Belgrano 740',
		ciudad: 'Corrientes'
	});
	assert.deepEqual(parametrosBusqueda('Belgrano', '', { lat: -27.471234, lon: -58.839876 }), {
		q: 'Belgrano',
		lat: '-27.4712',
		lon: '-58.8399'
	});
	assert.deepEqual(parametrosBusqueda('Belgrano', '', { lat: NaN, lon: 1 }), { q: 'Belgrano' });
});

test('textoAlElegir deja lugar para la altura si se eligió solo la calle', () => {
	assert.equal(textoAlElegir({ direccion: 'Belgrano', con_altura: false }), 'Belgrano ');
	assert.equal(textoAlElegir({ direccion: 'Belgrano 740', con_altura: true }), 'Belgrano 740');
	assert.equal(textoAlElegir({ direccion: 'Belgrano 740' }), 'Belgrano 740');
});

test('moverActivo recorre las opciones y da la vuelta', () => {
	assert.equal(moverActivo(-1, 3, 'ArrowDown'), 0);
	assert.equal(moverActivo(2, 3, 'ArrowDown'), 0);
	assert.equal(moverActivo(0, 3, 'ArrowUp'), 2);
	assert.equal(moverActivo(-1, 3, 'ArrowUp'), 2);
	assert.equal(moverActivo(1, 0, 'ArrowDown'), -1);
	assert.equal(moverActivo(1, 3, 'Home'), 1);
});
