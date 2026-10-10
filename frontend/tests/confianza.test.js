import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

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

test('DW-2.2: el detalle gatea el panel con mostrarAnalisis', () => {
	const detalle = fuente(DETALLE);
	assert.match(detalle, /import PanelEnlace from '\$lib\/PanelEnlace\.svelte'/);
	assert.match(detalle, /import \{ mostrarAnalisis \} from '\$lib\/confianza\.js'/);
	assert.match(detalle, /\{#if mostrarAnalisis\(pool\)\}/);
	assert.match(detalle, /<PanelEnlace analisis=\{pool\.analisis_enlace\} \/>/);
});

test('DW-2.2: el panel muestra validaciones, nivel y aclara que es análisis propio', () => {
	assert.ok(existsSync(new URL(PANEL, RAIZ)));
	const panel = fuente(PANEL);
	assert.match(panel, /Validaciones del enlace/);
	assert.match(panel, /[Aa]nálisis propio/);
	assert.match(panel, /etiquetaNivel\(analisis\.nivel\)/);
	assert.match(panel, /tonoNivel\(analisis\.nivel\)/);
	assert.match(panel, /\{#each analisis\.validaciones as validacion/);
	assert.match(panel, /estadoValidacion\(validacion\)/);
	assert.match(panel, /etiquetaClave\(validacion\.clave\)/);
	assert.match(panel, /\{validacion\.detalle\}/);
	// El panel es solo presentación: no hace fetch de nada (DW-2.4).
	assert.doesNotMatch(panel, /fetch\(/);
});
