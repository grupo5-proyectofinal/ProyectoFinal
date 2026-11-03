import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
	PREFERENCIAS,
	contadorCampana,
	etiquetaCampana,
	etiquetaTipo,
	textoNoLeidas,
	tiempoRelativo
} from '../src/lib/notificaciones.js';

const AHORA = new Date(2026, 9, 20, 15, 0, 0);

test('IT2-N.1: el badge muestra el estado nuevo o el tipo de aviso', () => {
	assert.equal(etiquetaTipo({ tipo: 'estado', datos: { estado: 'en_curso' } }), 'En curso');
	assert.equal(etiquetaTipo({ tipo: 'mensaje', datos: {} }), 'Mensaje nuevo');
	assert.equal(etiquetaTipo({ tipo: 'union', datos: {} }), 'Nuevo miembro');
	assert.equal(etiquetaTipo({ tipo: 'otro' }), 'Aviso');
	assert.equal(etiquetaTipo(null), 'Aviso');
});

test('IT2-N.2: fechas relativas de la bandeja', () => {
	assert.equal(tiempoRelativo(new Date(2026, 9, 20, 14, 59, 30).toISOString(), AHORA), 'Recién');
	assert.equal(tiempoRelativo(new Date(2026, 9, 20, 14, 55).toISOString(), AHORA), 'Hace 5 min');
	assert.equal(tiempoRelativo(new Date(2026, 9, 20, 13, 0).toISOString(), AHORA), 'Hace 2 h');
	assert.equal(tiempoRelativo(new Date(2026, 9, 19, 23, 0).toISOString(), AHORA), 'Ayer');
	assert.equal(tiempoRelativo(new Date(2026, 8, 28, 10, 0).toISOString(), AHORA), '28/09/2026');
	assert.equal(tiempoRelativo('no es fecha', AHORA), '');
});

test('IT2-N.3: textos de no leídas y de la campana', () => {
	assert.equal(textoNoLeidas(0), 'No tenés notificaciones sin leer.');
	assert.equal(textoNoLeidas(1), 'Tenés 1 notificación sin leer.');
	assert.equal(textoNoLeidas(5), 'Tenés 5 notificaciones sin leer.');
	assert.equal(contadorCampana(0), '');
	assert.equal(contadorCampana(3), '3');
	assert.equal(contadorCampana(12), '9+');
	assert.equal(etiquetaCampana(0), 'Notificaciones');
	assert.equal(etiquetaCampana(2), 'Notificaciones (2 sin leer)');
});

test('IT2-N.4: las preferencias son los campos que acepta /auth/me/', () => {
	assert.deepEqual(
		PREFERENCIAS.map((p) => p.clave),
		['notificar_estados', 'notificar_mensajes', 'notificar_miembros']
	);
});
