import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
	estrellas,
	etiquetaRol,
	formatoPuntaje,
	payloadResena,
	pendientesDeCalificar,
	textoResenas
} from '../src/lib/resenas.js';

const POOL = {
	estado: 'finalizado',
	creador: { id: 1, username: 'ana' },
	miembros: [
		{ id: 10, usuario: { id: 2, username: 'beto' } },
		{ id: 11, usuario: { id: 3, username: 'caro' } }
	]
};

test('IT2-R.1: puntaje y cantidad de reseñas en es-AR', () => {
	assert.equal(formatoPuntaje(4.5), '4,5');
	assert.equal(formatoPuntaje(5), '5,0');
	assert.equal(formatoPuntaje(null), '—');
	assert.equal(textoResenas(0), 'Sin reseñas');
	assert.equal(textoResenas(1), '1 reseña');
	assert.equal(textoResenas(38), '38 reseñas');
});

test('IT2-R.2: estrellas redondeadas y acotadas a 0..5', () => {
	assert.deepEqual(estrellas(4.6), [true, true, true, true, true]);
	assert.deepEqual(estrellas(2.2), [true, true, false, false, false]);
	assert.deepEqual(estrellas(9), [true, true, true, true, true]);
	assert.deepEqual(estrellas(null), [false, false, false, false, false]);
});

test('IT2-R.3: a quién falta calificar', () => {
	const deBeto = pendientesDeCalificar(POOL, 2, [{ destinatario: 3 }]);
	assert.deepEqual(
		deBeto.map((p) => [p.id, p.rol]),
		[[1, 'administrador']]
	);
	assert.deepEqual(
		pendientesDeCalificar(POOL, 1).map((p) => p.id),
		[2, 3]
	);
	assert.deepEqual(pendientesDeCalificar({ ...POOL, estado: 'en_curso' }, 2), []);
	assert.deepEqual(pendientesDeCalificar(null, 2), []);
});

test('IT2-R.4: payload y rol', () => {
	assert.deepEqual(payloadResena(1, '4', '  Muy bien '), {
		destinatario: 1,
		puntaje: 4,
		comentario: 'Muy bien'
	});
	assert.equal(etiquetaRol('administrador'), 'Como administrador');
	assert.equal(etiquetaRol('participante'), 'Como participante');
});
