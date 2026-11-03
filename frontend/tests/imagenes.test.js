import { test } from 'node:test';
import assert from 'node:assert/strict';

import { motivoImagen } from '../src/lib/imagenes.js';

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
