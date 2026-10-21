import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
	mensajeVerificacion,
	pendienteDeVerificacion,
	textoRegistroPendiente,
	tokenDeBaja
} from '../src/lib/verificacion.js';

test('IT2-V.1: el 403 del login significa email sin confirmar', () => {
	assert.equal(pendienteDeVerificacion({ status: 403 }), true);
	assert.equal(pendienteDeVerificacion({ status: 401 }), false);
	assert.equal(pendienteDeVerificacion(null), false);
});

test('IT2-V.2: token de baja desde el query string', () => {
	assert.equal(tokenDeBaja('?token=abc:123'), 'abc:123');
	assert.equal(tokenDeBaja('?otro=1'), '');
	assert.equal(tokenDeBaja(undefined), '');
});

test('IT2-V.3: mensajes de error en es-AR', () => {
	assert.equal(
		mensajeVerificacion({ status: 429, data: { detail: 'Request was throttled.' } }),
		'Demasiados intentos. Esperá unos minutos y volvé a probar.'
	);
	assert.equal(
		mensajeVerificacion({ status: 400, data: { token: ['El enlace para darte de baja no es válido.'] } }),
		'El enlace para darte de baja no es válido.'
	);
	assert.equal(
		mensajeVerificacion({ status: 400, data: { detail: ['El enlace de verificación es inválido.'] } }),
		'El enlace de verificación es inválido.'
	);
});

test('IT2-V.4: texto tras registrarse', () => {
	assert.equal(textoRegistroPendiente({ detail: 'Te enviamos un mail.' }, 'a@b.com'), 'Te enviamos un mail.');
	assert.equal(
		textoRegistroPendiente({}, 'a@b.com'),
		'Te enviamos un mail a a@b.com para confirmar tu cuenta.'
	);
});
