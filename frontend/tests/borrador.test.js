import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
	aplicarBorrador,
	borrarBorrador,
	borrarBorradores,
	guardarBorrador,
	leerBorrador
} from '../src/lib/borrador.js';

function memoria() {
	const datos = new Map();
	return {
		getItem: (k) => (datos.has(k) ? datos.get(k) : null),
		setItem: (k, v) => datos.set(k, String(v)),
		removeItem: (k) => datos.delete(k),
		key: (i) => [...datos.keys()][i] ?? null,
		get length() {
			return datos.size;
		},
		datos
	};
}

test('guarda y recupera solo los campos de texto', () => {
	const storage = memoria();
	guardarBorrador('nuevo', { titulo: 'Perfumes', imagenes: { name: 'a.jpg' } }, storage);
	assert.deepEqual(leerBorrador('nuevo', storage), { titulo: 'Perfumes' });
});

test('un form vacío no deja borrador', () => {
	const storage = memoria();
	guardarBorrador('nuevo', { titulo: 'x' }, storage);
	guardarBorrador('nuevo', { titulo: '  ', descripcion: '' }, storage);
	assert.equal(leerBorrador('nuevo', storage), null);
});

test('borrarBorrador lo elimina y un JSON roto no rompe', () => {
	const storage = memoria();
	guardarBorrador('nuevo', { titulo: 'x' }, storage);
	borrarBorrador('nuevo', storage);
	assert.equal(leerBorrador('nuevo', storage), null);
	storage.setItem('poolshop.borrador.nuevo', '{roto');
	assert.equal(leerBorrador('nuevo', storage), null);
});

test('aplicarBorrador vuelca valores y saltea archivos y campos inexistentes', () => {
	const elementos = {
		titulo: { type: 'text', value: '' },
		imagenes: { type: 'file', value: '' },
		acepta: { type: 'checkbox', checked: false }
	};
	const n = aplicarBorrador(elementos, {
		titulo: 'Perfumes',
		imagenes: 'C:\\fakepath\\a.jpg',
		acepta: 'on',
		borrado: 'x'
	});
	assert.equal(n, 2);
	assert.equal(elementos.titulo.value, 'Perfumes');
	assert.equal(elementos.imagenes.value, '');
	assert.equal(elementos.acepta.checked, true);
});

test('borrarBorradores limpia solo los borradores de PoolShop', () => {
	const storage = memoria();
	guardarBorrador('pool-nuevo', { titulo: 'x' }, storage);
	guardarBorrador('otro', { titulo: 'y' }, storage);
	storage.setItem('ajeno', '1');
	borrarBorradores(storage);
	assert.equal(leerBorrador('pool-nuevo', storage), null);
	assert.equal(leerBorrador('otro', storage), null);
	assert.equal(storage.getItem('ajeno'), '1');
});
