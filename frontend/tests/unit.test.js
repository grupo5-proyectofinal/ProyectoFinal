import { test } from 'node:test';
import assert from 'node:assert/strict';

import { diasHasta, fecha, iniciales, moneda, vistas } from '../src/lib/formato.js';
import { TONOS, etiquetaEstado, etiquetaPago, puedeEditar, puedeUnirse, tonoCategoria, tonoNombre } from '../src/lib/estados.js';
import { coordsValidas } from '../src/lib/ubicacion.js';

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

test('diasHasta: cuenta días enteros desde hoy', () => {
	const iso = (d) =>
		`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

	assert.equal(diasHasta(iso(new Date())), 0);

	const manana = new Date();
	manana.setDate(manana.getDate() + 1);
	assert.equal(diasHasta(iso(manana)), 1);

	const ayer = new Date();
	ayer.setDate(ayer.getDate() - 1);
	assert.equal(diasHasta(iso(ayer)), -1);
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

const POOL_ABIERTO = {
	estado: 'abierto',
	creador: { id: 1 },
	miembros: [],
	disponible: 5,
	min_por_integrante: 1
};

test('DW-3.5: puedeUnirse rechaza los estados que no son abierto', () => {
	for (const estado of ['cancelado', 'listo', 'en_curso', 'finalizado']) {
		assert.equal(puedeUnirse({ ...POOL_ABIERTO, estado }, 2), false, estado);
	}
	assert.equal(puedeUnirse(POOL_ABIERTO, 2), true);
});

test('DW-3.5: puedeUnirse exige no ser creador ni miembro y disponible suficiente', () => {
	assert.equal(puedeUnirse(POOL_ABIERTO, 1), false);
	assert.equal(puedeUnirse({ ...POOL_ABIERTO, miembros: [{ usuario: { id: 2 } }] }, 2), false);
	assert.equal(puedeUnirse({ ...POOL_ABIERTO, disponible: 0 }, 2), false);
	assert.equal(puedeUnirse({ ...POOL_ABIERTO, disponible: 1, min_por_integrante: 2 }, 2), false);
	assert.equal(puedeUnirse(null, 2), false);
	// Sin sesión la UI muestra "Ingresá para unirte"; la guarda evalúa estado, rol y disponible.
	assert.equal(puedeUnirse(POOL_ABIERTO, undefined), true);
});

test('DW-3.5: puedeEditar solo el creador y solo en abierto', () => {
	assert.equal(puedeEditar(POOL_ABIERTO, 1), true);
	assert.equal(puedeEditar(POOL_ABIERTO, 2), false);
	assert.equal(puedeEditar({ ...POOL_ABIERTO, estado: 'cancelado' }, 1), false);
	assert.equal(puedeEditar({ ...POOL_ABIERTO, estado: 'listo' }, 1), false);
	assert.equal(puedeEditar(null, 1), false);
});

test('DW-2.3: coordsValidas acepta decimales del API (string o número) dentro de rango', () => {
	assert.equal(coordsValidas('-31.416700', '-64.183300'), true);
	assert.equal(coordsValidas(-34.6, -58.4), true);
	assert.equal(coordsValidas(0, 0), true);
	assert.equal(coordsValidas('90', '180'), true);
});

test('DW-2.3: coordsValidas rechaza null, vacío y fuera de rango', () => {
	assert.equal(coordsValidas(null, null), false);
	assert.equal(coordsValidas(undefined, undefined), false);
	assert.equal(coordsValidas('', ''), false);
	assert.equal(coordsValidas('91', '0'), false);
	assert.equal(coordsValidas('0', '181'), false);
	assert.equal(coordsValidas('-90.000001', '0'), false);
	assert.equal(coordsValidas('no-es-numero', '0'), false);
});
