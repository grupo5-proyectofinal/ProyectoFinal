import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
	estadoValidacion,
	etiquetaClave,
	etiquetaNivel,
	mostrarAnalisis,
	tonoNivel
} from '../src/lib/confianza.js';

const RAIZ = new URL('../src/', import.meta.url);

function fuente(ruta) {
	return readFileSync(new URL(ruta, RAIZ), 'utf8');
}

const DETALLE = 'routes/pools/[id]/+page.svelte';
const PANEL = 'lib/PanelEnlace.svelte';

// --- DW-2.2: panel con validaciones y nivel; sin enlace no aparece ---

test('DW-2.2: mostrarAnalisis solo con análisis presente (sin enlace no hay panel)', () => {
	assert.equal(mostrarAnalisis({ analisis_enlace: { nivel: 'alto', validaciones: [] } }), true);
	assert.equal(mostrarAnalisis({ analisis_enlace: null }), false);
	assert.equal(mostrarAnalisis({}), false);
	assert.equal(mostrarAnalisis(null), false);
	assert.equal(mostrarAnalisis(undefined), false);
});

test('DW-2.2: etiquetaNivel y tonoNivel cubren los tres niveles', () => {
	assert.equal(etiquetaNivel('alto'), 'Confianza alta');
	assert.equal(etiquetaNivel('medio'), 'Confianza media');
	assert.equal(etiquetaNivel('bajo'), 'Confianza baja');
	assert.equal(tonoNivel('alto'), 'verde');
	assert.equal(tonoNivel('medio'), 'ambar');
	assert.equal(tonoNivel('bajo'), 'coral');
	// Dirty: nivel ausente o desconocido no rompe la UI.
	for (const valor of [undefined, null, '', 'altísimo', 42]) {
		assert.equal(etiquetaNivel(valor), 'Sin analizar', String(valor));
		assert.equal(tonoNivel(valor), 'azul', String(valor));
	}
});

test('DW-2.2: etiquetaClave traduce las claves del contrato', () => {
	assert.equal(etiquetaClave('formato'), 'Formato');
	assert.equal(etiquetaClave('https'), 'HTTPS');
	assert.equal(etiquetaClave('longitud'), 'Longitud');
	assert.equal(etiquetaClave('ip_literal'), 'Dirección IP');
	assert.equal(etiquetaClave('acortador'), 'Acortador');
	assert.equal(etiquetaClave('tld'), 'Dominio');
	assert.equal(etiquetaClave('uso'), 'Uso en PoolShop');
	assert.equal(etiquetaClave('desconocida'), 'desconocida');
});

test('DW-2.2: estadoValidacion distingue ok, atención y uso neutro', () => {
	assert.equal(estadoValidacion({ clave: 'https', ok: true }), 'ok');
	assert.equal(estadoValidacion({ clave: 'https', ok: false }), 'atencion');
	assert.equal(estadoValidacion({ clave: 'uso', ok: false }), 'neutro');
	assert.equal(estadoValidacion({ clave: 'uso', ok: true }), 'ok');
	// Dirty: entradas ausentes o sin ok no rompen.
	assert.equal(estadoValidacion(undefined), 'atencion');
	assert.equal(estadoValidacion({ clave: 'formato' }), 'atencion');
});

test('DW-2.2: el detalle gatea el panel (sin análisis no se renderiza con undefined)', () => {
	// El gate evita el crash del panel cuando el backend devuelve analisis_enlace null.
	const detalle = fuente(DETALLE);
	assert.match(
		detalle,
		/\{#if mostrarAnalisis\(pool\)\}\s*<PanelEnlace analisis=\{pool\.analisis_enlace\} \/>/
	);
});

test('DW-2.4: el panel es solo presentación: no hace fetch propio', () => {
	// El análisis lo calcula el backend; un fetch en el panel contradiría el diseño.
	assert.doesNotMatch(fuente(PANEL), /fetch\(/);
});
