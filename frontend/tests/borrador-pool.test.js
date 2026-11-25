import { test } from 'node:test';
import assert from 'node:assert/strict';

import { faltantesParaGuardar, sinCamposVacios } from '../src/lib/borradorPool.js';

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
