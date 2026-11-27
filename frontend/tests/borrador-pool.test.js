import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
	armarCuerpoEdicion,
	faltantesParaGuardar,
	pasoConError,
	sinCamposVacios
} from '../src/lib/borradorPool.js';

test('un borrador solo pide título y categoría', () => {
	assert.deepEqual(faltantesParaGuardar({ titulo: 'Perfume', categoria: '3' }), {});
	assert.deepEqual(Object.keys(faltantesParaGuardar({ titulo: '  ', categoria: '' })), [
		'titulo',
		'categoria'
	]);
	assert.deepEqual(Object.keys(faltantesParaGuardar()), ['titulo', 'categoria']);
});

test('sinCamposVacios deja lo completado y quita lo vacío', () => {
	const fd = new FormData();
	fd.append('titulo', 'Perfume');
	fd.append('precio_unitario', '');
	fd.append('ciudad', '   ');
	fd.append('cantidad_creador', '1');
	sinCamposVacios(fd);
	assert.deepEqual([...fd.keys()], ['titulo', 'cantidad_creador']);
});

test('faltantesParaPublicar lista lo que le falta a un borrador', async () => {
	const { faltantesParaPublicar } = await import('../src/lib/borradorPool.js');
	const hoy = new Date(2026, 10, 24);
	const vacio = {
		nombre_producto: '',
		enlace: '',
		precio_unitario: '0.00',
		cantidad_total: 1,
		cantidad_creador: 1,
		direccion: '',
		ciudad: '',
		fecha_caducidad: '2026-12-20',
		tipo_pago: 'sin_especificar'
	};
	assert.deepEqual(Object.keys(faltantesParaPublicar(vacio, hoy)), [
		'nombre_producto',
		'enlace',
		'precio_unitario',
		'cantidad_total',
		'direccion',
		'ciudad'
	]);
	const completo = {
		...vacio,
		nombre_producto: 'Perfume',
		enlace: 'https://t.example/p',
		precio_unitario: '1000.00',
		cantidad_total: 10,
		direccion: 'Calle 1',
		ciudad: 'Córdoba'
	};
	assert.deepEqual(faltantesParaPublicar(completo, hoy), {});
	assert.ok(faltantesParaPublicar({ ...completo, fecha_caducidad: '2026-11-01' }, hoy).fecha_caducidad);
	assert.ok(faltantesParaPublicar({ ...completo, tipo_pago: 'transferencia' }, hoy).alias_cbu);
});

const VALORES_BASE = {
	titulo: 'Mate imperial',
	enlace: 'https://tienda.example/mate',
	nombre_producto: 'Mate',
	descripcion: 'Cuero',
	categoria: '4',
	atributos: '{"Color":["Negro"]}',
	precio_unitario: '15000',
	cantidad_total: '10',
	cantidad_creador: '2',
	min_por_integrante: '1',
	fecha_caducidad: '2026-12-20',
	tipo_pago: 'transferencia',
	alias_cbu: 'mate.pool',
	titular_cuenta: 'Juan Pérez',
	direccion: 'Av. Colón 100',
	ciudad: 'Córdoba'
};

test('armarCuerpoEdicion incluye cantidad_creador y campos editables', () => {
	const cuerpo = armarCuerpoEdicion(VALORES_BASE, { esBorrador: false, hayOtrosIntegrantes: false });
	assert.equal(cuerpo.cantidad_creador, 2);
	assert.equal(cuerpo.min_por_integrante, 1);
	assert.equal(cuerpo.cantidad_total, 10);
	assert.equal(cuerpo.categoria, 4);
	assert.deepEqual(cuerpo.atributos, { Color: ['Negro'] });
	assert.equal(cuerpo.alias_cbu, 'mate.pool');
	assert.equal('enlace' in cuerpo, false);
});

test('armarCuerpoEdicion con otros integrantes omite inmutables pero conserva cantidad_creador', () => {
	const cuerpo = armarCuerpoEdicion(VALORES_BASE, { esBorrador: false, hayOtrosIntegrantes: true });
	assert.equal(cuerpo.cantidad_creador, 2);
	assert.equal(cuerpo.min_por_integrante, 1);
	assert.equal('titulo' in cuerpo, false);
	assert.equal('cantidad_total' in cuerpo, false);
	assert.equal('precio_unitario' in cuerpo, false);
});

test('armarCuerpoEdicion en borrador incluye enlace y omite numéricos vacíos o <= 0', () => {
	const cuerpo = armarCuerpoEdicion(
		{
			...VALORES_BASE,
			precio_unitario: '',
			cantidad_total: '0',
			cantidad_creador: '',
			min_por_integrante: '0',
			fecha_caducidad: ''
		},
		{ esBorrador: true, hayOtrosIntegrantes: false }
	);
	assert.equal(cuerpo.enlace, 'https://tienda.example/mate');
	assert.equal('precio_unitario' in cuerpo, false);
	assert.equal('cantidad_total' in cuerpo, false);
	assert.equal('cantidad_creador' in cuerpo, false);
	assert.equal('min_por_integrante' in cuerpo, false);
	assert.equal('fecha_caducidad' in cuerpo, false);
});

test('pasoConError devuelve el primer paso con error o -1', () => {
	const pasos = [
		{ id: 'producto', campos: ['titulo', 'enlace', 'nombre_producto'] },
		{ id: 'precio', campos: ['precio_unitario', 'cantidad_total', 'cantidad_creador'] },
		{ id: 'entrega', campos: ['fecha_caducidad', 'alias_cbu', 'direccion'] }
	];
	assert.equal(pasoConError({ cantidad_creador: 'Supera el total' }, pasos), 1);
	assert.equal(pasoConError({ alias_cbu: 'Falta', titulo: 'Falta' }, pasos), 0);
	assert.equal(pasoConError({ direccion: 'Falta' }, pasos), 2);
	assert.equal(pasoConError({ detail: 'Error general' }, pasos), -1);
	assert.equal(pasoConError({}, pasos), -1);
});
