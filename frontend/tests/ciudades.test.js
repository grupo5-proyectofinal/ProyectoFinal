import { test } from 'node:test';
import assert from 'node:assert/strict';

import { ciudadSeleccionada, opcionesCiudad } from '../src/lib/ciudades.js';

test('opcionesCiudad normaliza espacios, deduplica sin distinguir mayúsculas y ordena en español', () => {
	const resultado = opcionesCiudad([
		'  rosario ',
		'Rosario',
		'Corrientes',
		'Córdoba',
		'  Buenos   Aires ',
		'buenos aires',
		'   ',
		null
	]);
	assert.deepEqual(resultado, ['Buenos Aires', 'Córdoba', 'Corrientes', 'Rosario']);
});

test('opcionesCiudad incluye la ciudad activa de la URL si no vino del servidor', () => {
	assert.deepEqual(opcionesCiudad(['Buenos Aires', 'Rosario'], '  Mendoza  '), [
		'Buenos Aires',
		'Mendoza',
		'Rosario'
	]);
});

test('opcionesCiudad no duplica la ciudad activa si ya está en la lista', () => {
	assert.deepEqual(opcionesCiudad(['Buenos Aires', 'Rosario'], 'rosario'), [
		'Buenos Aires',
		'Rosario'
	]);
});

test('opcionesCiudad tolera listas faltantes o vacías', () => {
	assert.deepEqual(opcionesCiudad(undefined, ''), []);
	assert.deepEqual(opcionesCiudad(null, 'Córdoba'), ['Córdoba']);
});

test('ciudadSeleccionada ajusta el casing al de la opción existente', () => {
	assert.equal(ciudadSeleccionada(['Buenos Aires', 'Rosario'], 'rosario'), 'Rosario');
	assert.equal(ciudadSeleccionada(['Buenos Aires', 'Rosario'], '  buenos   aires '), 'Buenos Aires');
	assert.equal(ciudadSeleccionada(['Buenos Aires', 'Rosario'], 'Mendoza'), 'Mendoza');
	assert.equal(ciudadSeleccionada(['Buenos Aires', 'Rosario'], ''), '');
});
