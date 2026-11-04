import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
	avisoMinimo,
	desglose,
	enlaceCrearPool,
	faltante,
	precioEnMoneda,
	puntosTendencia,
	variacion
} from '../src/lib/comparador.js';

test('precioEnMoneda muestra la moneda de la tienda', () => {
	assert.equal(precioEnMoneda('1500', 'ARS'), '$ 1.500');
	assert.equal(precioEnMoneda('45.99', 'USD'), 'USD 45,99');
	assert.equal(precioEnMoneda(null, 'USD'), '—');
});

test('desglose solo lista lo que suma y marca la aduana como estimada', () => {
	const costo = {
		unidades: 5,
		subtotal: '50000.00',
		envio: '0.00',
		impuestos: '0.00',
		aduana: { derechos: '0.00', tasa_estadistica: '1500.00', iva: '10815.00', percepciones: '0.00' },
		total: '62315.00'
	};
	assert.deepEqual(
		desglose(costo).map((f) => [f.rotulo, f.estimado ?? false]),
		[
			['Productos (5 u.)', false],
			['Tasa estadística', true],
			['IVA de importación', true]
		]
	);
	assert.deepEqual(desglose({ total: null }), []);
});

test('faltante y avisoMinimo explican el cálculo', () => {
	assert.match(faltante({ falta: 'tipo_cambio', moneda: 'USD' }), /tipo de cambio de USD/);
	assert.equal(faltante({ total: '1' }), null);
	assert.match(avisoMinimo({ unidades: 12 }, 10), /mínimo de la tienda es 12/);
	assert.equal(avisoMinimo({ unidades: 10 }, 10), null);
});

test('puntosTendencia escala al viewBox y aplana un solo precio', () => {
	const historial = [
		{ precio: '100', fecha: 'a' },
		{ precio: '80', fecha: 'b' },
		{ precio: '120', fecha: 'c' }
	];
	const puntos = puntosTendencia(historial, 80, 24, 4);
	assert.deepEqual(
		puntos.map((p) => [p.x, p.y]),
		[
			[4, 12],
			[40, 20],
			[76, 4]
		]
	);
	assert.deepEqual(
		puntosTendencia([{ precio: '5', fecha: 'a' }]).map((p) => p.y),
		[12]
	);
	assert.deepEqual(puntosTendencia([]), []);
});

test('variacion compara el primer y el último precio', () => {
	assert.equal(variacion([{ precio: '100' }, { precio: '95' }]), 'Bajó 5 %');
	assert.equal(variacion([{ precio: '100' }, { precio: '102' }]), 'Subió 2 %');
	assert.equal(variacion([{ precio: '100' }]), 'Sin cambios');
});

test('enlaceCrearPool precarga producto, precio en pesos y cantidad', () => {
	const url = enlaceCrearPool(
		{ url: 'https://t.com/p', moneda: 'ARS', precio_unitario: '1500.00' },
		{ titulo: 'Yerba', producto: 'Yerba 1 kg', cantidad: 10 }
	);
	const params = new URL(url, 'http://x').searchParams;
	assert.equal(params.get('enlace'), 'https://t.com/p');
	assert.equal(params.get('producto'), 'Yerba 1 kg');
	assert.equal(params.get('precio'), '1500.00');
	assert.equal(params.get('cantidad'), '10');
	assert.equal(new URL(enlaceCrearPool({ moneda: 'USD', precio_unitario: '1' }, {}), 'http://x').searchParams.get('precio'), null);
});
