import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
	INTERVALO_CHAT,
	LIMITE_INICIAL,
	avisoEscritura,
	cursorMensajes,
	estadoChat,
	fusionarMensajes,
	puedeEnviar,
	puedeEscribirMensajes
} from '../src/lib/chat.js';

const ANA = { id: 1, username: 'ana' };

const POOL = {
	estado: 'listo',
	creador: { id: 1 },
	miembros: [{ usuario: { id: 2 } }]
};

const mensaje = (id, texto = `m${id}`) => ({ id, texto, autor: ANA, creado: '2026-10-10T12:00:00-03:00' });

// --- DW-5.1: el panel es solo para integrantes ---

test('DW-5.1: estadoChat oculta el panel a quien no es integrante', () => {
	assert.equal(estadoChat(POOL, 1), 'escritura', 'creador');
	assert.equal(estadoChat(POOL, 2), 'escritura', 'miembro');
	assert.equal(estadoChat(POOL, 3), 'oculto', 'tercero');
	assert.equal(estadoChat(POOL, undefined), 'oculto', 'sin sesión');
	assert.equal(estadoChat(null, 1), 'oculto', 'pool inexistente');
});

test('DW-5.1: estadoChat decide lectura o escritura según el estado del pool', () => {
	const esperado = {
		abierto: 'lectura',
		listo: 'escritura',
		en_curso: 'escritura',
		finalizado: 'escritura',
		cancelado: 'lectura'
	};
	for (const [estado, modo] of Object.entries(esperado)) {
		assert.equal(estadoChat({ ...POOL, estado }, 1), modo, `creador en ${estado}`);
		assert.equal(estadoChat({ ...POOL, estado }, 2), modo, `miembro en ${estado}`);
		assert.equal(estadoChat({ ...POOL, estado }, 3), 'oculto', `tercero en ${estado}`);
	}
});

test('DW-5.1: puedeEscribirMensajes espeja los estados con escritura del backend', () => {
	assert.equal(puedeEscribirMensajes('listo'), true);
	assert.equal(puedeEscribirMensajes('en_curso'), true);
	assert.equal(puedeEscribirMensajes('finalizado'), true);
	assert.equal(puedeEscribirMensajes('abierto'), false);
	assert.equal(puedeEscribirMensajes('cancelado'), false);
	assert.equal(puedeEscribirMensajes(undefined), false);
});

test('avisoEscritura: explica el bloqueo por estado y calla cuando se puede escribir', () => {
	assert.equal(avisoEscritura('listo'), '');
	assert.equal(avisoEscritura('en_curso'), '');
	assert.equal(avisoEscritura('finalizado'), '');
	assert.match(avisoEscritura('abierto'), /listo para comprar/);
	assert.match(avisoEscritura('cancelado'), /solo lectura/);
	assert.ok(avisoEscritura('exotico'), 'un estado desconocido no deja el panel sin aviso');
});

// --- DW-5.2: envío ---

test('DW-5.2: puedeEnviar bloquea vacíos, solo espacios y más de 1000', () => {
	assert.equal(puedeEnviar('Hola, ¿cómo va?'), true);
	assert.equal(puedeEnviar('  Hola  '), true, 'recorta como el backend');
	assert.equal(puedeEnviar(''), false);
	assert.equal(puedeEnviar('   '), false);
	assert.equal(puedeEnviar('\n\t '), false);
	assert.equal(puedeEnviar(null), false);
	assert.equal(puedeEnviar(undefined), false);
	assert.equal(puedeEnviar('a'.repeat(1000)), true, 'el límite exacto entra');
	assert.equal(puedeEnviar('a'.repeat(1001)), false);
	assert.equal(puedeEnviar(`${'a'.repeat(1000)}  `), true, 'los espacios no cuentan tras recortar');
});

// --- DW-5.3: polling incremental ---

test('DW-5.3: cursorMensajes es el id más alto visto (el `desde` del polling)', () => {
	assert.equal(cursorMensajes([]), 0, 'sin mensajes se pide todo');
	assert.equal(cursorMensajes([mensaje(7)]), 7);
	assert.equal(cursorMensajes([mensaje(1), mensaje(2), mensaje(3)]), 3);
	assert.equal(cursorMensajes([mensaje(3), mensaje(9), mensaje(4)]), 9, 'no depende del orden');
});

test('DW-5.3: un ciclo de polling agrega solo lo nuevo y avanza el cursor', () => {
	let vistos = [mensaje(1), mensaje(2), mensaje(3)];

	// Lo que el servidor devuelve para desde=cursor.
	const lote = [mensaje(4), mensaje(5)];
	vistos = fusionarMensajes(vistos, lote);

	assert.deepEqual(
		vistos.map((m) => m.id),
		[1, 2, 3, 4, 5]
	);
	assert.equal(cursorMensajes(vistos), 5, 'el próximo pedido arranca en 5');
});

test('DW-5.3: el intervalo del polling entra en el límite de 10 s', () => {
	assert.ok(INTERVALO_CHAT > 0 && INTERVALO_CHAT <= 10000, `intervalo: ${INTERVALO_CHAT} ms`);
	assert.ok(LIMITE_INICIAL <= 200, 'el contrato clampea limit en 200');
});

// --- DW-5.4: sin duplicados ---

test('DW-5.4: fusionar no duplica ids repetidos y es idempotente', () => {
	const lote = [mensaje(1), mensaje(2)];
	const unaVez = fusionarMensajes(lote, lote);
	assert.deepEqual(
		unaVez.map((m) => m.id),
		[1, 2]
	);
	assert.deepEqual(fusionarMensajes(unaVez, lote), unaVez, 'repetir el lote no cambia nada');

	const solapado = fusionarMensajes([mensaje(1), mensaje(2), mensaje(3)], [mensaje(2), mensaje(3), mensaje(4)]);
	assert.deepEqual(
		solapado.map((m) => m.id),
		[1, 2, 3, 4]
	);
});

test('DW-5.4: el dedupe es por id, no por texto', () => {
	const repetidos = fusionarMensajes([mensaje(1, 'ok')], [mensaje(2, 'ok')]);
	assert.deepEqual(
		repetidos.map((m) => m.id),
		[1, 2],
		'dos mensajes distintos con el mismo texto sobreviven'
	);
});

test('DW-5.4: fusionar ordena ascendente aunque llegue desordenado', () => {
	const mezcla = fusionarMensajes([mensaje(3), mensaje(1)], [mensaje(2), mensaje(10)]);
	assert.deepEqual(
		mezcla.map((m) => m.id),
		[1, 2, 3, 10]
	);
	assert.deepEqual(fusionarMensajes(), [], 'sin argumentos no rompe');
	assert.deepEqual(fusionarMensajes([mensaje(1)]), [mensaje(1)], 'sin nuevos conserva los previos');
});
