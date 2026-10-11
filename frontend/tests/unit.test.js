import { test } from 'node:test';
import assert from 'node:assert/strict';

import { diasHasta, fecha, iniciales, moneda, vistas } from '../src/lib/formato.js';
import { TONOS, etiquetaEstado, etiquetaPago, puedeEditar, puedeUnirse, tonoCategoria, tonoNombre } from '../src/lib/estados.js';
import { coordsValidas } from '../src/lib/ubicacion.js';
import { payloadUnion } from '../src/lib/union.js';
import {
	TABS,
	contextoDeTab,
	endpointDeTab,
	esTabAutenticada,
	navActiva,
	normalizarTab,
	paginaDeParams,
	paramsDeFiltros,
	queryDeApi,
	rutaTab
} from '../src/lib/pestanas.js';
import {
	conConfirmacion,
	desenlaceEliminacion,
	mensajeError,
	miVotoEliminacion,
	puedeEliminarDirecto,
	puedeSolicitarEliminacion,
	puedeVotarEliminacion
} from '../src/lib/eliminacion.js';

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

test('DW-1.4: payloadUnion arma el payload de unirse con cantidad numérica y textos recortados', () => {
	assert.deepEqual(payloadUnion('3', ' 351 555 ', '  Hola, me sumo!  '), {
		cantidad: 3,
		telefono: '351 555',
		mensaje: 'Hola, me sumo!'
	});
	// Prefill sin datos: no rompe; manda vacíos (el servidor valida el teléfono).
	assert.deepEqual(payloadUnion(1, undefined, undefined), {
		cantidad: 1,
		telefono: '',
		mensaje: ''
	});
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

const POOL_LISTO = {
	estado: 'listo',
	creador: { id: 1 },
	miembros: [{ usuario: { id: 2 } }, { usuario: { id: 3 } }],
	disponible: 0,
	min_por_integrante: 1
};

const SOLICITUD_PENDIENTE = {
	id: 7,
	estado: 'pendiente',
	total: 2,
	aceptaron: 1,
	votos: [{ usuario: { id: 2, username: 'miembro0' }, acepta: true }]
};

test('DW-5.1: el creador solo ve "Solicitar eliminación" en listo/en_curso y sin pendiente', () => {
	assert.equal(puedeSolicitarEliminacion(POOL_LISTO, 1), true);
	assert.equal(puedeSolicitarEliminacion({ ...POOL_LISTO, estado: 'en_curso' }, 1), true);
	for (const estado of ['abierto', 'finalizado', 'cancelado']) {
		assert.equal(puedeSolicitarEliminacion({ ...POOL_LISTO, estado }, 1), false, estado);
	}
	assert.equal(puedeSolicitarEliminacion(POOL_LISTO, 2), false, 'no creador');
	assert.equal(puedeSolicitarEliminacion(POOL_LISTO, undefined), false, 'sin sesión');
	assert.equal(puedeSolicitarEliminacion(null, 1), false, 'pool inexistente');
	assert.equal(puedeSolicitarEliminacion(POOL_LISTO, 1, SOLICITUD_PENDIENTE), false, 'ya hay pendiente');
	assert.equal(
		puedeSolicitarEliminacion(POOL_LISTO, 1, { ...SOLICITUD_PENDIENTE, estado: 'rechazada' }),
		true,
		're-solicitar tras rechazo'
	);
});

test('DW-5.1/DW-5.4: cancelar la confirmación no llama a la API', async () => {
	let llamadas = 0;
	let mensajeVisto = '';
	const accion = () => {
		llamadas += 1;
		return 'ok';
	};
	const pedir = (mensaje) => {
		mensajeVisto = mensaje;
		return false;
	};

	const cancelada = await conConfirmacion('¿Eliminar este pool?', pedir, accion);
	assert.deepEqual(cancelada, { confirmada: false });
	assert.equal(llamadas, 0, 'la acción no se ejecuta si se cancela');
	assert.equal(mensajeVisto, '¿Eliminar este pool?', 'el texto de confirmación llega al diálogo');

	const aceptada = await conConfirmacion('¿Eliminar este pool?', () => true, accion);
	assert.deepEqual(aceptada, { confirmada: true, resultado: 'ok' });
	assert.equal(llamadas, 1);

	const borrado = await conConfirmacion('¿?', () => true, () => null);
	assert.equal(borrado.confirmada, true);
	assert.equal(borrado.resultado, null, 'un DELETE 204 no se confunde con cancelado');
});

test('DW-5.2: el miembro vota una sola vez y ve su voto registrado', () => {
	assert.equal(puedeVotarEliminacion(POOL_LISTO, SOLICITUD_PENDIENTE, 3), true, 'integrante sin votar');
	assert.equal(puedeVotarEliminacion(POOL_LISTO, SOLICITUD_PENDIENTE, 2), false, 'ya votó: no puede cambiarlo');
	assert.deepEqual(miVotoEliminacion(SOLICITUD_PENDIENTE, 2), SOLICITUD_PENDIENTE.votos[0]);
	assert.equal(miVotoEliminacion(SOLICITUD_PENDIENTE, 3), null, 'sin voto propio');
	assert.equal(puedeVotarEliminacion(POOL_LISTO, SOLICITUD_PENDIENTE, 1), false, 'el creador no vota');
	assert.equal(puedeVotarEliminacion(POOL_LISTO, SOLICITUD_PENDIENTE, 99), false, 'no integrante');
	assert.equal(puedeVotarEliminacion(POOL_LISTO, SOLICITUD_PENDIENTE, undefined), false, 'sin sesión');
	assert.equal(
		puedeVotarEliminacion(POOL_LISTO, { ...SOLICITUD_PENDIENTE, estado: 'rechazada' }, 3),
		false,
		'solicitud cerrada'
	);
	assert.equal(puedeVotarEliminacion(POOL_LISTO, null, 3), false, 'sin solicitud');
});

test('DW-5.3: aprobada → borrado (toast + redirect); rechazada → pool intacto', () => {
	assert.equal(desenlaceEliminacion('aprobada'), 'borrado');
	assert.equal(desenlaceEliminacion('rechazada'), 'rechazada');
	assert.equal(desenlaceEliminacion('pendiente'), 'seguir');
	assert.equal(desenlaceEliminacion(undefined), 'seguir');
});

test('DW-5.4: el eliminar directo sigue siendo del creador y solo en abierto', () => {
	assert.equal(puedeEliminarDirecto(POOL_ABIERTO, 1), true);
	assert.equal(puedeEliminarDirecto(POOL_ABIERTO, 2), false);
	assert.equal(puedeEliminarDirecto(POOL_ABIERTO, undefined), false);
	assert.equal(puedeEliminarDirecto({ ...POOL_ABIERTO, estado: 'listo' }, 1), false);
	assert.equal(puedeEliminarDirecto({ ...POOL_ABIERTO, estado: 'cancelado' }, 1), false);
	assert.equal(puedeEliminarDirecto(null, 1), false);
});

test('eliminación: errores 400/403 del API y caída de red', () => {
	assert.equal(
		mensajeError({ status: 403, data: { detail: 'Solo los integrantes pueden votar.' } }),
		'Solo los integrantes pueden votar.'
	);
	assert.equal(
		mensajeError({ status: 400, data: ['Hay una solicitud de eliminación pendiente.'] }),
		'Hay una solicitud de eliminación pendiente.'
	);
	assert.equal(
		mensajeError({ status: 400, data: { non_field_errors: ['Ya votaste esta solicitud.'] } }),
		'Ya votaste esta solicitud.'
	);
	assert.match(mensajeError(new TypeError('Failed to fetch')), /conectar/);
	assert.equal(mensajeError({ status: 500, data: null }), 'No se pudo completar la acción.');
});

test('DW-6.1: normalizarTab acepta los tres tabs y cae en "todos"', () => {
	assert.equal(normalizarTab('todos'), 'todos');
	assert.equal(normalizarTab('mios'), 'mios');
	assert.equal(normalizarTab('unidos'), 'unidos');
	for (const invalido of [null, undefined, '', 'otro', 'MIOS', 'todos,unidos']) {
		assert.equal(normalizarTab(invalido), 'todos', String(invalido));
	}
});

test('DW-6.1: cada tab apunta a su endpoint de datasets', () => {
	assert.equal(endpointDeTab('todos'), '/pools/');
	assert.equal(endpointDeTab('mios'), '/pools/mios/');
	assert.equal(endpointDeTab('unidos'), '/pools/unidos/');
	assert.equal(endpointDeTab('raro'), '/pools/');
	assert.deepEqual(
		TABS.map((t) => t.id),
		['todos', 'mios', 'unidos']
	);
});

test('DW-6.1: solo mios/unidos requieren sesión', () => {
	assert.equal(esTabAutenticada('mios'), true);
	assert.equal(esTabAutenticada('unidos'), true);
	assert.equal(esTabAutenticada('todos'), false);
	assert.equal(esTabAutenticada(null), false);
});

test('DW-6.2: rutaTab arma el destino de cada redirección', () => {
	assert.equal(rutaTab('mios'), '/pools?tab=mios');
	assert.equal(rutaTab('unidos'), '/pools?tab=unidos');
	assert.equal(rutaTab('todos'), '/pools?tab=todos');
});

test('DW-6.3: los filtros viajan entre pestañas y el tab sobrevive al filtrar', () => {
	const params = paramsDeFiltros({ q: 'yerba', categoria: '3', estado: '', ordering: '' }, 'mios');
	assert.equal(params.toString(), 'q=yerba&categoria=3&tab=mios');
	assert.equal(rutaTab('unidos', params), '/pools?q=yerba&categoria=3&tab=unidos');
});

test('DW-6.3: cambiar de pestaña conserva filtros/orden y resetea la página', () => {
	const params = new URLSearchParams('tab=todos&q=yerba&ordering=-precio_unitario&page=3');
	assert.equal(
		rutaTab('mios', params, 'todos'),
		'/pools?tab=mios&q=yerba&ordering=-precio_unitario'
	);
	assert.equal(
		rutaTab('mios', params, 'mios'),
		'/pools?tab=mios&q=yerba&ordering=-precio_unitario&page=3',
		'repetir la pestaña activa conserva la página'
	);
});

test('DW-6.3: la consulta al API conserva filtros/orden/página y no manda tab', () => {
	assert.deepEqual(
		queryDeApi(new URLSearchParams('tab=mios&q=yerba&ordering=-vistas&page=2&estado=')),
		{ q: 'yerba', ordering: '-vistas', page: '2', estado: '' }
	);
	assert.deepEqual(queryDeApi(new URLSearchParams('tab=todos')), {});
});

test('?page=abc no rompe la paginación: cae en la página 1', () => {
	assert.equal(paginaDeParams(new URLSearchParams('page=abc')), 1, 'NaN → 1');
	assert.equal(paginaDeParams(new URLSearchParams('page=')), 1, 'vacío → 1');
	assert.equal(paginaDeParams(new URLSearchParams('page=0')), 1, 'cero → 1');
	assert.equal(paginaDeParams(new URLSearchParams('page=-3')), 1, 'negativo → 1');
	assert.equal(paginaDeParams(new URLSearchParams('')), 1, 'sin param → 1');
	assert.equal(paginaDeParams(new URLSearchParams('page=2.9')), 2, 'decimal → entero');
	assert.equal(paginaDeParams(new URLSearchParams('page=3')), 3);
});

test('DW-6.3: nav marca activo el enlace que corresponde a la pestaña', () => {
	assert.equal(navActiva({ href: '/pools' }, '/pools', 'todos'), true);
	assert.equal(navActiva({ href: '/pools' }, '/pools', 'mios'), false);
	assert.equal(navActiva({ href: '/pools?tab=mios', tab: 'mios' }, '/pools', 'mios'), true);
	assert.equal(navActiva({ href: '/pools?tab=mios', tab: 'mios' }, '/pools', 'todos'), false);
	assert.equal(navActiva({ href: '/pools?tab=unidos', tab: 'unidos' }, '/pools', 'mios'), false);
	assert.equal(navActiva({ href: '/pools' }, '/pools/12', 'todos'), true, 'detalle bajo Pools');
	assert.equal(navActiva({ href: '/pools' }, '/pools/nuevo', 'todos'), false);
	assert.equal(navActiva({ href: '/pools/nuevo' }, '/pools/nuevo', 'todos'), true);
	assert.equal(navActiva({ href: '/', exacto: true }, '/pools', 'todos'), false);
	assert.equal(navActiva({ href: '/perfil' }, '/perfil', 'todos'), true);
	assert.equal(navActiva({ href: '/admin/usuarios', prefijo: true }, '/admin/usuarios', 'todos'), true);
	assert.equal(navActiva({ href: '/admin/usuarios', prefijo: true }, '/admin/usuarios/7', 'todos'), true);
	assert.equal(navActiva({ href: '/admin/usuarios', prefijo: true }, '/admin/otra', 'todos'), false);
});

test('DW-6.2: el contexto de tarjeta conserva el estilo de las páginas viejas', () => {
	assert.equal(contextoDeTab('mios'), 'mis-pools');
	assert.equal(contextoDeTab('unidos'), 'unidos');
	assert.equal(contextoDeTab('todos'), null);
});
