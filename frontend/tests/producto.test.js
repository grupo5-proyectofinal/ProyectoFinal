import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
	camposDesdeVistaPrevia,
	enlaceAnalizable,
	precioTotal,
	precioUnitarioDesdeTotal
} from '../src/lib/producto.js';

test('IT2-P.1: precio total ⇄ unitario según la cantidad', () => {
	assert.equal(precioTotal('1500', '10'), '15000.00');
	assert.equal(precioTotal('99.99', 3), '299.97');
	assert.equal(precioTotal('', 10), '');
	assert.equal(precioTotal('100', 0), '');
	assert.equal(precioUnitarioDesdeTotal('1000', '3'), '333.33');
	assert.equal(precioUnitarioDesdeTotal('15000', 10), '1500.00');
	assert.equal(precioUnitarioDesdeTotal('abc', 10), '');
});

test('IT2-P.2: la vista previa pisa nombre y precio, y completa título vacío', () => {
	const vista = {
		encontrado: true,
		nombre_producto: 'Yerba Playadito 1kg',
		precio_unitario: '4599.90',
		imagen: 'https://cdn/x.jpg',
		descripcion: 'Con palo'
	};
	assert.deepEqual(camposDesdeVistaPrevia(vista, { titulo: '', descripcion: '' }), {
		nombre_producto: 'Yerba Playadito 1kg',
		titulo: 'Yerba Playadito 1kg',
		precio_unitario: '4599.90',
		descripcion: 'Con palo'
	});
	assert.deepEqual(camposDesdeVistaPrevia(vista, { titulo: 'Mi pool', descripcion: 'Mía' }), {
		nombre_producto: 'Yerba Playadito 1kg',
		precio_unitario: '4599.90'
	});
	assert.deepEqual(camposDesdeVistaPrevia({ encontrado: false }), {});
	assert.deepEqual(camposDesdeVistaPrevia(null), {});
});

test('IT2-P.3: solo se analizan enlaces http(s)', () => {
	assert.equal(enlaceAnalizable('https://tienda.com/p/1'), true);
	assert.equal(enlaceAnalizable(' http://tienda.com '), true);
	assert.equal(enlaceAnalizable('ftp://tienda.com'), false);
	assert.equal(enlaceAnalizable('tienda'), false);
	assert.equal(enlaceAnalizable(''), false);
});
