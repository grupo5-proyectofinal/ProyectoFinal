import assert from 'node:assert/strict';
import test from 'node:test';

import { debeRedirigirPorMejoras, esRutaDeMejoras } from '../src/lib/mejoras.js';

test('reconoce las rutas de mayoristas y comparador, incluido el backoffice', () => {
	for (const ruta of ['/mayoristas', '/mayoristas/3', '/comparar', '/comparar/7', '/admin/mayoristas']) {
		assert.equal(esRutaDeMejoras(ruta), true, ruta);
	}
	for (const ruta of ['/', '/pools', '/pools/3', '/admin/usuarios', '/ayuda', '/mayoristas-no']) {
		assert.equal(esRutaDeMejoras(ruta), false, ruta);
	}
});

test('con las mejoras apagadas redirige; encendidas, no', () => {
	assert.equal(debeRedirigirPorMejoras('/comparar', false), true);
	assert.equal(debeRedirigirPorMejoras('/comparar', true), false);
	assert.equal(debeRedirigirPorMejoras('/pools', false), false);
});
