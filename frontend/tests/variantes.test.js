import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
	atributosDe,
	atributosElegidos,
	csvVariantes,
	detalleDesdeFilas,
	etiquetaVariante,
	filaVacia,
	filasIniciales,
	hijas,
	raices,
	resumenVariantes,
	separarCategoria,
	sumaFilas
} from '../src/lib/variantes.js';

const CATEGORIAS = [
	{ id: 1, nombre: 'Ropa', padre: null, atributos: [{ nombre: 'Color', opciones: ['Negro', 'Blanco'] }] },
	{
		id: 2,
		nombre: 'Remera',
		padre: 1,
		atributos: [
			{ nombre: 'Talle', opciones: ['S', 'M', 'L'] },
			{ nombre: 'Color', opciones: ['Negro', 'Blanco'] }
		]
	},
	{ id: 3, nombre: 'Bebidas', padre: null, atributos: [] }
];
const VARIANTES = [
	{ nombre: 'Talle', opciones: ['S', 'M'] },
	{ nombre: 'Color', opciones: ['Negro'] }
];

test('raices, hijas y separarCategoria arman los dos selects', () => {
	assert.deepEqual(raices(CATEGORIAS).map((c) => c.nombre), ['Ropa', 'Bebidas']);
	assert.deepEqual(hijas(CATEGORIAS, '1').map((c) => c.nombre), ['Remera']);
	assert.deepEqual(hijas(CATEGORIAS, ''), []);
	assert.deepEqual(separarCategoria(CATEGORIAS, 2), { raiz: '1', sub: '2' });
	assert.deepEqual(separarCategoria(CATEGORIAS, 3), { raiz: '3', sub: '' });
	assert.deepEqual(separarCategoria(CATEGORIAS, 99), { raiz: '', sub: '' });
});

test('atributosElegidos respeta el orden de la categoría y descarta lo que ya no existe', () => {
	const atributos = atributosDe(CATEGORIAS, 2);
	assert.deepEqual(
		atributosElegidos(atributos, { Talle: ['L', 'S', 'XXL'], Color: [], Sabor: ['Menta'] }),
		{ Talle: ['S', 'L'] }
	);
	assert.deepEqual(atributosElegidos([], { Talle: ['S'] }), {});
});

test('filas: vacía, iniciales, suma y payload', () => {
	assert.deepEqual(filaVacia(VARIANTES, 2), { atributos: { Talle: 'S', Color: 'Negro' }, cantidad: 2 });
	assert.deepEqual(filasIniciales([], [{ atributos: {}, cantidad: 1 }]), []);
	assert.deepEqual(filasIniciales(VARIANTES, null, 3), [filaVacia(VARIANTES, 3)]);
	const propias = [{ atributos: { Talle: 'M', Color: 'Negro' }, cantidad: 2 }];
	const copia = filasIniciales(VARIANTES, propias);
	copia[0].atributos.Talle = 'S';
	assert.equal(propias[0].atributos.Talle, 'M'); // no comparte objetos con el pool
	const filas = [
		{ atributos: { Talle: 'S', Color: 'Negro' }, cantidad: '2' },
		{ atributos: { Talle: 'M', Color: 'Negro' }, cantidad: '' }
	];
	assert.equal(sumaFilas(filas), 2);
	assert.deepEqual(detalleDesdeFilas(filas), [{ atributos: { Talle: 'S', Color: 'Negro' }, cantidad: 2 }]);
});

test('resumenVariantes suma por variante y csvVariantes exporta', () => {
	const miembros = [
		{ detalle: [{ atributos: { Color: 'Negro', Talle: 'M' }, cantidad: 2 }] },
		{ detalle: [{ atributos: { Talle: 'M', Color: 'Negro' }, cantidad: 1 }, { atributos: { Talle: 'S', Color: 'Negro' }, cantidad: 1 }] },
		{ detalle: [] },
		{}
	];
	const resumen = resumenVariantes(miembros, VARIANTES);
	assert.deepEqual(
		resumen.map((r) => [r.etiqueta, r.cantidad]),
		[
			['M · Negro', 3],
			['S · Negro', 1]
		]
	);
	assert.equal(csvVariantes(resumen, VARIANTES), 'Talle,Color,Cantidad\nM,Negro,3\nS,Negro,1');
	assert.equal(etiquetaVariante({ Color: 'Negro', Talle: 'M' }, VARIANTES), 'M · Negro');
	assert.equal(
		csvVariantes([{ atributos: { Talle: 'M, ancho' }, cantidad: 1 }], [{ nombre: 'Talle' }]),
		'Talle,Cantidad\n"M, ancho",1'
	);
});
