import { test } from 'node:test';
import assert from 'node:assert/strict';

import { esIntegrante, fechaHora, textoEvento } from '../src/lib/historial.js';

const ANA = { id: 1, username: 'ana' };

function evento(tipo, datos = {}, actor = ANA) {
	return { tipo, actor, datos, creado: '2026-10-05T15:30:00-03:00' };
}

// --- DW-3.4: textos es-AR por tipo, sin datos personales ---

test('DW-3.4: textoEvento cubre cada tipo con texto es-AR', () => {
	assert.equal(textoEvento(evento('creado')), 'ana creó el pool.');
	assert.equal(
		textoEvento(evento('edicion', { campos: ['titulo', 'precio_unitario'] })),
		'ana editó el pool (título, precio).'
	);
	assert.equal(textoEvento(evento('edicion', { campos: [] })), 'ana editó el pool.');
	assert.equal(textoEvento(evento('imagen', { accion: 'agregada' })), 'ana agregó una imagen.');
	assert.equal(textoEvento(evento('imagen', { accion: 'eliminada' })), 'ana eliminó una imagen.');
	assert.equal(textoEvento(evento('union', { cantidad: 3 })), 'ana se unió al pool (3 u.).');
	assert.equal(textoEvento(evento('salida', { cantidad: 3 })), 'ana salió del pool (3 u.).');
	assert.equal(
		textoEvento(evento('cantidad', { antes: 3, despues: 6 })),
		'ana cambió su cantidad de 3 a 6 u.'
	);
	assert.equal(textoEvento(evento('estado', { estado: 'en_curso' })), 'ana confirmó el pedido.');
	assert.equal(textoEvento(evento('estado', { estado: 'cancelado' })), 'ana canceló el pool.');
	assert.equal(
		textoEvento(evento('solicitud_eliminacion')),
		'ana solicitó eliminar el pool.'
	);
	assert.equal(
		textoEvento(evento('voto_eliminacion', { acepta: true })),
		'ana votó a favor de eliminar el pool.'
	);
	assert.equal(
		textoEvento(evento('voto_eliminacion', { acepta: false })),
		'ana votó en contra de eliminar el pool.'
	);
});

test('DW-3.2: el evento del sistema se cuenta en tercera persona', () => {
	assert.equal(
		textoEvento(evento('expirado', {}, null)),
		'El pool venció y se canceló automáticamente.'
	);
	assert.equal(textoEvento(evento('creado', {}, null)), 'El sistema creó el pool.');
});

test('DW-3.4: textoEvento no interpola datos desconocidos (ni PII) aunque vengan', () => {
	const datos = { cantidad: 2, telefono: '3515551234', mensaje: 'Hola, me sumo' };
	const tipos = [
		'creado',
		'edicion',
		'imagen',
		'union',
		'salida',
		'cantidad',
		'estado',
		'expirado',
		'solicitud_eliminacion',
		'voto_eliminacion'
	];
	for (const tipo of tipos) {
		const texto = textoEvento(evento(tipo, datos));
		assert.ok(!texto.includes('3515551234'), `${tipo}: no debe filtrar el teléfono`);
		assert.ok(!texto.includes('me sumo'), `${tipo}: no debe filtrar el mensaje`);
	}
});

test('DW-3.4: textoEvento tolera eventos raros sin romper la UI', () => {
	assert.equal(textoEvento(null), 'El sistema hizo un cambio en el pool.');
	assert.equal(textoEvento(evento('desconocido')), 'ana hizo un cambio en el pool.');
	assert.equal(
		textoEvento(evento('estado', { estado: 'exotico' })),
		'ana cambió el estado del pool.'
	);
	assert.equal(textoEvento(evento('edicion', { campos: ['raro'] })), 'ana editó el pool (raro).');
});

// --- DW-3.4: el gate del timeline ---

test('DW-3.4: esIntegrante solo acepta creador o miembro con sesión', () => {
	const pool = { creador: { id: 1 }, miembros: [{ usuario: { id: 2 } }] };
	assert.equal(esIntegrante(pool, 1), true, 'creador');
	assert.equal(esIntegrante(pool, 2), true, 'miembro');
	assert.equal(esIntegrante(pool, 3), false, 'tercero');
	assert.equal(esIntegrante(pool, undefined), false, 'sin sesión');
	assert.equal(esIntegrante({ creador: { id: 1 } }, 2), false, 'sin miembros');
	assert.equal(esIntegrante(null, 1), false, 'pool inexistente');
});

test('fechaHora: formatea ISO y tolera valores inválidos', () => {
	const texto = fechaHora('2026-10-05T15:30:00-03:00');
	assert.match(texto, /oct/i);
	assert.match(texto, /2026/);
	assert.match(texto, /\d{2}:\d{2}/);
	assert.equal(fechaHora(null), '');
	assert.equal(fechaHora('no-es-fecha'), '');
});
