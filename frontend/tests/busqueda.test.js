import { test } from 'node:test';
import assert from 'node:assert/strict';

import { propiosDeBusqueda } from '../src/lib/busqueda.js';

test('propiosDeBusqueda junta lo que organizo y lo que reservé, sin repetidos', () => {
	const lista = propiosDeBusqueda(
		[{ id: 1, titulo: 'A' }],
		[
			{ id: 1, titulo: 'A' },
			{ id: 2, titulo: 'B' }
		]
	);
	assert.deepEqual(
		lista.map((p) => [p.id, p.relacion]),
		[
			[1, 'Organizás vos'],
			[2, 'Reservaste']
		]
	);
});

test('propiosDeBusqueda tolera resultados faltantes', () => {
	assert.deepEqual(propiosDeBusqueda(undefined, null), []);
});
