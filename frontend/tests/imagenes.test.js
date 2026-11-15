import { test } from 'node:test';
import assert from 'node:assert/strict';

import { motivoImagen, sumarImagenes } from '../src/lib/imagenes.js';

test('motivoImagen usa el mensaje del campo que manda la API', () => {
	assert.equal(
		motivoImagen({ status: 400, data: { imagen: ['Subí una imagen válida (JPG, PNG, HEIC o WEBP).'] } }),
		'Subí una imagen válida (JPG, PNG, HEIC o WEBP).'
	);
	assert.equal(motivoImagen({ status: 400, data: { detail: 'Máximo 10 imágenes.' } }), 'Máximo 10 imágenes.');
});

test('motivoImagen explica los casos sin cuerpo', () => {
	assert.equal(motivoImagen({ status: 413, data: null }), 'el archivo es demasiado grande.');
	assert.equal(motivoImagen({ status: 401, data: null }), 'tu sesión expiró.');
	assert.match(motivoImagen({ status: 500, data: null }), /servidor/);
	assert.match(motivoImagen(undefined), /servidor/);
});

// Regresión: elegir fotos de nuevo pisaba la selección anterior.
test('sumarImagenes conserva las ya elegidas y suma las nuevas', () => {
	const a = { name: 'a.jpg', size: 1, lastModified: 1 };
	const b = { name: 'b.jpg', size: 2, lastModified: 2 };
	const { lista, excedidas } = sumarImagenes([a], [b], 10);
	assert.deepEqual(lista, [a, b]);
	assert.equal(excedidas, 0);
});

test('sumarImagenes ignora repetidas y respeta el máximo', () => {
	const fotos = [1, 2, 3].map((n) => ({ name: `${n}.jpg`, size: n, lastModified: n }));
	assert.deepEqual(sumarImagenes([fotos[0]], [fotos[0], fotos[1]], 10).lista, [fotos[0], fotos[1]]);
	const recortada = sumarImagenes([fotos[0], fotos[1]], [fotos[2]], 2);
	assert.equal(recortada.lista.length, 2);
	assert.equal(recortada.excedidas, 1);
});
