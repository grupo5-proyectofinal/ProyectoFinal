import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

import {
	CONFIRMACION_NEUTRAL,
	confirmacionDeSolicitud,
	enlaceInvalido,
	mensajeReset,
	parametrosDeReset
} from '../src/lib/recuperacion.js';

const RAIZ = new URL('../src/', import.meta.url);

function fuente(ruta) {
	return readFileSync(new URL(ruta, RAIZ), 'utf8');
}

// uid/token con la forma real del mail de F1: uid es base64 urlsafe de pk=1 y
// el token es `<timestamp>-<hash>` del default_token_generator de Django.
const UID = 'MQ';
const TOKEN = `1a2b3c4d-${'0f'.repeat(32)}`;

test('DW-2.1: /recuperar confirma de forma neutral exista o no la cuenta', () => {
	// Cuerpo del 200 del contrato; F1 garantiza el mismo para cuenta existente e
	// inexistente (test_DW_1_1_neutralidad_mismo_cuerpo), así que el front nunca
	// puede ramificar por existencia de cuenta.
	const respuesta = {
		detail:
			'Si el email corresponde a una cuenta, te enviamos un enlace para restablecer la contraseña.'
	};
	assert.equal(confirmacionDeSolicitud(respuesta), respuesta.detail);

	// El texto por defecto tampoco revela si la cuenta existe.
	assert.equal(confirmacionDeSolicitud(null), CONFIRMACION_NEUTRAL);
	assert.match(CONFIRMACION_NEUTRAL, /si el email corresponde a una cuenta/i);
	assert.doesNotMatch(CONFIRMACION_NEUTRAL, /no existe|inexistente|no está registrad/i);

	// Y la ruta de la pantalla existe.
	assert.ok(existsSync(new URL('routes/recuperar/+page.svelte', RAIZ)));
});

test('confirmación: bodies no confiables del API caen al texto neutral', () => {
	for (const body of [undefined, null, {}, { detail: '' }, { detail: '   ' }, { detail: 42 }, []]) {
		assert.equal(confirmacionDeSolicitud(body), CONFIRMACION_NEUTRAL, JSON.stringify(body));
	}
	assert.equal(confirmacionDeSolicitud({ detail: '  Detalle del API.  ' }), 'Detalle del API.');
});

test('DW-2.2: el link del mail abre /restablecer con uid y token', () => {
	const link = `http://localhost:5173/restablecer?uid=${UID}&token=${TOKEN}`;
	const parametros = parametrosDeReset(new URL(link).search);

	assert.equal(parametros.completo, true);
	assert.equal(parametros.uid, UID);
	assert.equal(parametros.token, TOKEN);

	// La ruta que abre el link existe (wiring del mail de F1 → página).
	assert.ok(existsSync(new URL('routes/restablecer/+page.svelte', RAIZ)));
});

test('DW-2.3: parámetros faltantes o vacíos dejan el enlace incompleto', () => {
	for (const search of [
		'?uid=MQ',
		'?token=x',
		'?uid=&token=x',
		'?uid=MQ&token=',
		'?uid=%20&token=x',
		'?uid=MQ&token=%20',
		'',
		null,
		undefined
	]) {
		assert.equal(parametrosDeReset(search).completo, false, String(search));
	}

	// La página ofrece la salida a /recuperar cuando el enlace no sirve.
	assert.match(fuente('routes/restablecer/+page.svelte'), /'\/recuperar'/);
});

test('DW-2.3: token inválido/expirado usa el mensaje es-AR del backend', () => {
	const vencido = {
		status: 400,
		data: { detail: 'El enlace de restablecimiento es inválido o expiró.' }
	};
	assert.equal(enlaceInvalido(vencido), true);
	assert.equal(mensajeReset(vencido), 'El enlace de restablecimiento es inválido o expiró.');

	// Password débil o mismatch no son enlace muerto: se corrigen en el form.
	const corta = { status: 400, data: { password: ['Esta contraseña es muy corta.'] } };
	const mismatch = { status: 400, data: { password2: ['Las contraseñas no coinciden.'] } };
	assert.equal(enlaceInvalido(corta), false);
	assert.equal(enlaceInvalido(mismatch), false);
	// Un `detail` que no venga de un 400 (p. ej. throttle) no es enlace muerto.
	assert.equal(
		enlaceInvalido({ status: 429, data: { detail: 'Request was throttled.' } }),
		false,
		'429 con detail'
	);
	assert.equal(enlaceInvalido({ status: 500, data: null }), false);
	assert.equal(enlaceInvalido(null), false);
});

test('DW-2.4: el login expone el enlace de recuperación', () => {
	const login = fuente('routes/login/+page.svelte');
	assert.match(login, /'\/recuperar'/);
	assert.match(login, /olvidaste/i);
});

test('reset: el 429 del throttle se muestra en es-AR (DRF lo manda en inglés)', () => {
	const throttled = {
		status: 429,
		data: { detail: 'Request was throttled. Expected available in 59 seconds.' }
	};
	const mensaje = mensajeReset(throttled);
	assert.match(mensaje, /demasiados intentos/i);
	assert.doesNotMatch(mensaje, /throttled/i);
});

test('reset: errores de red y 500 delegan en el mapeo general', () => {
	assert.match(mensajeReset(new TypeError('Failed to fetch')), /conectar/i);
	assert.equal(mensajeReset({ status: 500, data: null }), 'No se pudo completar la acción.');
	assert.equal(
		mensajeReset({ status: 400, data: { non_field_errors: ['Algo salió mal.'] } }),
		'Algo salió mal.'
	);
});
