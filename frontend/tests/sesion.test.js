import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
	expiraEn,
	necesitaRenovar,
	rutaSegura,
	unaVez,
	urlLogin
} from '../src/lib/sesion.js';

function jwt(payload) {
	const b64 = (obj) => Buffer.from(JSON.stringify(obj)).toString('base64url');
	return `${b64({ alg: 'HS256', typ: 'JWT' })}.${b64(payload)}.firma`;
}

test('expiraEn lee el exp del payload en milisegundos', () => {
	assert.equal(expiraEn(jwt({ exp: 1_800_000_000 })), 1_800_000_000_000);
	assert.equal(expiraEn('no-es-un-jwt'), null);
	assert.equal(expiraEn(null), null);
	assert.equal(expiraEn(jwt({ sin: 'exp' })), null);
});

test('necesitaRenovar avisa antes de que venza el access', () => {
	const ahora = 1_000_000_000_000;
	const venceEn = (ms) => jwt({ exp: (ahora + ms) / 1000 });
	assert.equal(necesitaRenovar(venceEn(60_000), ahora), true); // 1 min: renovar
	assert.equal(necesitaRenovar(venceEn(-1000), ahora), true); // vencido
	assert.equal(necesitaRenovar(venceEn(10 * 60_000), ahora), false); // 10 min: alcanza
	assert.equal(necesitaRenovar('ilegible', ahora), false); // sin exp: lo decide el 401
});

test('unaVez comparte un solo refresh entre pedidos simultáneos', async () => {
	let llamadas = 0;
	let liberar;
	const renovar = unaVez(() => {
		llamadas += 1;
		return new Promise((r) => (liberar = r));
	});
	const a = renovar();
	const b = renovar();
	await Promise.resolve();
	liberar(true);
	assert.deepEqual(await Promise.all([a, b]), [true, true]);
	assert.equal(llamadas, 1);
	// Terminado el primero, el siguiente 401 vuelve a renovar.
	const c = renovar();
	await Promise.resolve();
	liberar(false);
	assert.equal(await c, false);
	assert.equal(llamadas, 2);
});

test('rutaSegura solo acepta rutas internas', () => {
	assert.equal(rutaSegura('/pools/nuevo'), '/pools/nuevo');
	assert.equal(rutaSegura('/pools?tab=mios'), '/pools?tab=mios');
	assert.equal(rutaSegura('//evil.com'), '/');
	assert.equal(rutaSegura('https://evil.com'), '/');
	assert.equal(rutaSegura('/\\evil.com'), '/');
	assert.equal(rutaSegura('/\t/evil.com'), '/');
	assert.equal(rutaSegura('/\n/evil.com'), '/');
	assert.equal(rutaSegura('/login?next=/perfil'), '/');
	assert.equal(rutaSegura(undefined), '/');
});

test('urlLogin conserva la página para volver después del login', () => {
	assert.equal(urlLogin('/pools/nuevo'), '/login?next=%2Fpools%2Fnuevo');
	assert.equal(urlLogin('/pools', '?tab=mios'), '/login?next=%2Fpools%3Ftab%3Dmios');
	assert.equal(urlLogin('/'), '/login');
});

// Cableado (sin DOM harness): si se rompe, vuelve el bug de "la sesión se cierra sola".
const API = readFileSync(new URL('../src/lib/api.js', import.meta.url), 'utf8');
const SESION = readFileSync(new URL('../src/lib/session.svelte.js', import.meta.url), 'utf8');

test('api.js renueva el token ante un 401 y reintenta', () => {
	assert.match(API, /status !== 401/);
	assert.match(API, /renovarSesion\(\)/);
	assert.match(API, /sesionExpirada\(\)/);
});

test('session.svelte.js usa /auth/refresh/ y cierra en el servidor con /auth/logout/', () => {
	assert.match(SESION, /'\/auth\/refresh\/'/);
	assert.match(SESION, /'\/auth\/logout\/'/);
});
