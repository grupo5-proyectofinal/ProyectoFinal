import { test } from 'node:test';
import assert from 'node:assert/strict';

import { fecha, iniciales, moneda, vistas } from '../src/lib/formato.js';
import { TONOS, etiquetaEstado, etiquetaPago, tonoCategoria, tonoNombre } from '../src/lib/estados.js';

test('moneda: formatea números en pesos es-AR', () => {
	assert.equal(moneda(1500), '$ 1.500');
	assert.equal(moneda('1500.00'), '$ 1.500');
	assert.equal(moneda(0), '$ 0');
});

test('moneda: valores vacíos o inválidos devuelven "—"', () => {
	assert.equal(moneda(null), '—');
	assert.equal(moneda(undefined), '—');
	assert.equal(moneda(''), '—');
	assert.equal(moneda('no-es-un-numero'), '—');
});

test('fecha: formatea una fecha ISO en formato local es-AR', () => {
	const valor = fecha('2026-10-05');
	assert.match(valor, /^\d+\s/);
	assert.match(valor, /oct/i);
	assert.match(valor, /2026/);
});

test('fecha: valores vacíos devuelven "—" y una fecha inválida se conserva', () => {
	assert.equal(fecha(null), '—');
	assert.equal(fecha(undefined), '—');
	assert.equal(fecha(''), '—');
	assert.equal(fecha('no-es-fecha'), 'no-es-fecha');
});

test('vistas: singular y plural', () => {
	assert.equal(vistas(1), '1 vista');
	assert.equal(vistas(0), '0 vistas');
	assert.equal(vistas(5), '5 vistas');
	assert.equal(vistas(undefined), '0 vistas');
});

test('iniciales: arma el monograma y tolera vacíos', () => {
	assert.equal(iniciales('ana perez'), 'AP');
	assert.equal(iniciales(''), '?');
	assert.equal(iniciales(undefined), '?');
});

test('etiquetaEstado: cubre los cinco estados', () => {
	assert.equal(etiquetaEstado('abierto'), 'Abierto');
	assert.equal(etiquetaEstado('listo'), 'Listo');
	assert.equal(etiquetaEstado('en_curso'), 'En curso');
	assert.equal(etiquetaEstado('finalizado'), 'Finalizado');
	assert.equal(etiquetaEstado('cancelado'), 'Cancelado');
});

test('etiquetaPago: traduce los tipos de pago', () => {
	assert.equal(etiquetaPago('efectivo'), 'Efectivo');
	assert.equal(etiquetaPago('transferencia'), 'Transferencia');
	assert.equal(etiquetaPago('sin_especificar'), 'Sin especificar');
	assert.equal(etiquetaPago('otro'), 'otro');
});

test('tonoCategoria: es determinista y devuelve un tono válido', () => {
	assert.equal(tonoCategoria(7), tonoCategoria(7));
	assert.ok(TONOS.includes(tonoCategoria(1)));
	assert.ok(TONOS.includes(tonoCategoria(999)));
	assert.equal(tonoCategoria('3'), tonoCategoria(3));
});

test('tonoNombre: es determinista y devuelve un tono válido', () => {
	assert.equal(tonoNombre('ana perez'), tonoNombre('ana perez'));
	assert.ok(TONOS.includes(tonoNombre('ana perez')));
	assert.ok(TONOS.includes(tonoNombre('')));
});
