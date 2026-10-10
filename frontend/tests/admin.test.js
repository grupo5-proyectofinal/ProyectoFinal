import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

import {
	SIN_ACCESO,
	destinoGuardAdmin,
	esStaff,
	filtrosDeListado,
	fusionarUsuario,
	nombreUsuario,
	puedeToggle,
	queryDeListado,
	rutaListado,
	rutaPagina
} from '../src/lib/admin.js';
import { fieldErrors } from '../src/lib/errores.js';

const RAIZ = new URL('../src/', import.meta.url);

function fuente(ruta) {
	return readFileSync(new URL(ruta, RAIZ), 'utf8');
}

const LISTA = 'routes/admin/usuarios/+page.svelte';
const DETALLE = 'routes/admin/usuarios/[id]/+page.svelte';
const ALTA = 'routes/admin/usuarios/nuevo/+page.svelte';

// --- DW-4.1: guard de rol y entrada Admin ---

test('DW-4.1: esStaff solo con is_staff === true (entrada externa estricta)', () => {
	assert.equal(esStaff({ is_staff: true }), true);
	for (const user of [
		{ is_staff: false },
		{ is_staff: 'true' },
		{ is_staff: 1 },
		{},
		null,
		undefined
	]) {
		assert.equal(esStaff(user), false, JSON.stringify(user));
	}
});

test('DW-4.1: el guard manda anónimo a login y no-staff a inicio', () => {
	// Sin sesión: al login (mismo destino que el resto de rutas protegidas).
	assert.equal(destinoGuardAdmin(null, null), '/login');
	assert.equal(destinoGuardAdmin(undefined, { is_staff: true }), '/login');

	// Con sesión y usuario cargado: staff sigue, no-staff vuelve al inicio.
	assert.equal(destinoGuardAdmin('token', { is_staff: true }), null);
	assert.equal(destinoGuardAdmin('token', { is_staff: false }), '/');
	// Dirty: un user sin el campo (o con valor no booleano) no es staff.
	assert.equal(destinoGuardAdmin('token', {}), '/');
	assert.equal(destinoGuardAdmin('token', { is_staff: 'true' }), '/');

	// Usuario aún cargando (loadMe pendiente): no se redirige; la página espera.
	assert.equal(destinoGuardAdmin('token', null), null);
});

test('DW-4.1: el layout gatea la entrada Admin y usa el guard', () => {
	const layout = fuente('routes/+layout.svelte');

	// La entrada existe y solo se muestra con rol (escritorio y móvil usan `visibles`).
	assert.match(layout, /'\/admin\/usuarios'/);
	assert.match(layout, /staff: true/);
	assert.match(layout, /esStaff\(session\.user\)/);
	// El guard de la rama /admin delega en la decisión pura.
	assert.match(layout, /destinoGuardAdmin\(session\.access, session\.user\)/);

	// Las tres rutas del panel existen.
	assert.ok(existsSync(new URL(LISTA, RAIZ)));
	assert.ok(existsSync(new URL(DETALLE, RAIZ)));
	assert.ok(existsSync(new URL(ALTA, RAIZ)));
});

test('DW-4.1: si el staff pierde el rol, las páginas avisan y vuelven al inicio', () => {
	const accion = fuente('lib/admin.svelte.js');
	assert.match(accion, /notificar\(SIN_ACCESO, 'error'\)/);
	assert.match(accion, /loadMe\(\)/);
	assert.match(accion, /goto\(resolve\('\/'\)\)/);

	for (const ruta of [LISTA, DETALLE, ALTA]) {
		assert.match(fuente(ruta), /alPerderAcceso\(\)/, ruta);
	}
	assert.match(SIN_ACCESO, /acceso al panel/i);
});

// --- DW-4.2: listado con búsqueda, filtro y paginación ---

test('DW-4.2: filtrosDeListado normaliza la URL (entrada externa)', () => {
	assert.deepEqual(filtrosDeListado('?q=ana&is_active=false&page=2'), {
		q: 'ana',
		is_active: 'false',
		pagina: 2
	});
	assert.deepEqual(filtrosDeListado('?is_active=true'), { q: '', is_active: 'true', pagina: 1 });
	assert.deepEqual(filtrosDeListado('?q=%20ana%20perez%20'), {
		q: 'ana perez',
		is_active: '',
		pagina: 1
	});

	// Sin URL o vacía: filtros limpios y página 1.
	for (const search of ['', null, undefined]) {
		assert.deepEqual(filtrosDeListado(search), { q: '', is_active: '', pagina: 1 }, String(search));
	}

	// is_active fuera del contrato se ignora (no viaja al API).
	for (const valor of ['quizas', 'TRUE', '1', '']) {
		assert.equal(filtrosDeListado(`?is_active=${valor}`).is_active, '', valor);
	}

	// page basura cae a 1; un entero válido se respeta.
	for (const page of ['0', '-3', 'abc', '']) {
		assert.equal(filtrosDeListado(`?page=${page}`).pagina, 1, page);
	}
	assert.equal(filtrosDeListado('?page=2.9').pagina, 2);
	assert.equal(filtrosDeListado('?page=3').pagina, 3);
});

test('DW-4.2: queryDeListado arma la consulta del API sin campos vacíos', () => {
	assert.deepEqual(queryDeListado({ q: 'ana', is_active: 'false', pagina: 2 }), {
		q: 'ana',
		is_active: 'false',
		page: 2
	});
	assert.deepEqual(queryDeListado({ q: 'ana', is_active: '', pagina: 1 }), { q: 'ana' });
	assert.deepEqual(queryDeListado({ q: '', is_active: '', pagina: 1 }), {});
	assert.deepEqual(queryDeListado(), {});
});

test('DW-4.2: rutaListado aplica filtros y resetea la página', () => {
	assert.equal(
		rutaListado({ q: 'ana', is_active: 'true' }),
		'/admin/usuarios?q=ana&is_active=true'
	);
	assert.equal(rutaListado({ q: '', is_active: '' }), '/admin/usuarios');
	assert.equal(rutaListado({ q: '  ana  ', is_active: 'false' }), '/admin/usuarios?q=ana&is_active=false');
	// `pagina` del estado no viaja al aplicar filtros; is_active inválido se descarta.
	assert.equal(rutaListado({ q: 'ana', is_active: 'quizas', pagina: 3 }), '/admin/usuarios?q=ana');
	assert.equal(rutaListado(null), '/admin/usuarios');
});

test('DW-4.2: rutaPagina conserva filtros y pagina', () => {
	assert.equal(
		rutaPagina('?q=ana&is_active=true&page=2', 3),
		'/admin/usuarios?q=ana&is_active=true&page=3'
	);
	assert.equal(rutaPagina('?q=ana&page=2', 1), '/admin/usuarios?q=ana', 'volver a la 1 limpia page');
	assert.equal(rutaPagina('', 2), '/admin/usuarios?page=2');
	assert.equal(rutaPagina(null, 1), '/admin/usuarios');
});

test('DW-4.2: la página del listado cablea filtros, API y paginación', () => {
	const lista = fuente(LISTA);
	assert.match(lista, /api\('\/admin\/usuarios\/', \{ query: queryDeListado\(/);
	assert.match(lista, /filtrosDeListado\(page\.url\.search\)/);
	assert.match(lista, /goto\(rutaListado\(filtros\)\)/);
	assert.match(lista, /goto\(rutaPagina\(page\.url\.search, n\)\)/);
	assert.match(lista, />Activos</);
	assert.match(lista, />Inactivos</);
	assert.match(lista, /datos\.next/);
	// Página fuera de rango (404 del contrato): vuelve a la primera conservando filtros.
	assert.match(lista, /e\.status === 404/);
	assert.match(lista, /goto\(rutaPagina\(page\.url\.search, 1\)\)/);
});

// --- Guard estático: identificadores llamados sin importar/declarar ---
// Regresión: `notificar` se llamaba en el listado sin import (rama 404) y la
// aserción de fuente no lo detectaba; en runtime era un ReferenceError.

// Runes de Svelte y globales de JS/navegador que una página puede llamar sin declarar.
const GLOBALES = new Set([
	'$state', '$derived', '$effect', '$props', '$bindable', '$inspect', '$host',
	'Boolean', 'Number', 'String', 'Object', 'Array', 'JSON', 'Math', 'Date', 'Promise',
	'Error', 'RegExp', 'Map', 'Set', 'parseInt', 'parseFloat', 'isNaN',
	'FormData', 'URLSearchParams', 'URL', 'fetch', 'console', 'setTimeout', 'clearTimeout',
	'window', 'document', 'localStorage'
]);
const PALABRAS = new Set([
	'if', 'else', 'for', 'while', 'do', 'switch', 'catch', 'return', 'typeof', 'void',
	'delete', 'new', 'function', 'await', 'yield', 'in', 'of', 'instanceof'
]);

function identificadoresLibres(fuente) {
	// Sin CSS (clamp/var/minmax parecen llamadas) ni comentarios por ahora:
	// las páginas admin no tienen `nombre(` dentro de comentarios.
	const codigo = fuente.replace(/<style>[\s\S]*?<\/style>/g, '');
	const declarados = new Set();
	for (const m of codigo.matchAll(/import\s*\{([^}]*)\}/g)) {
		for (const parte of m[1].split(',')) {
			const nombre = parte.trim().split(/\s+as\s+/).pop();
			if (nombre) declarados.add(nombre);
		}
	}
	for (const m of codigo.matchAll(/import\s+([A-Za-z_$][\w$]*)\s+from/g)) declarados.add(m[1]);
	for (const m of codigo.matchAll(/\b(?:function|const|let|var)\s+([A-Za-z_$][\w$]*)/g)) {
		declarados.add(m[1]);
	}
	const libres = new Set();
	// `nombre(` sin espacio es una llamada; los métodos (`algo.nombre(`) quedan afuera.
	for (const m of codigo.matchAll(/(?<![\w$.])([A-Za-z_$][\w$]*)(?=\()/g)) {
		const nombre = m[1];
		if (!declarados.has(nombre) && !GLOBALES.has(nombre) && !PALABRAS.has(nombre)) {
			libres.add(nombre);
		}
	}
	return [...libres];
}

test('admin: las páginas del panel importan/declaran todo identificador que llaman', () => {
	// El guard detecta el defecto real: llamada sin binding → falla sin el import.
	assert.deepEqual(identificadoresLibres(`<script>notificar('hola');</script>`), ['notificar']);
	// Con el import presente no hay identificadores libres.
	assert.deepEqual(
		identificadoresLibres(
			`<script>import { notificar } from '$lib/toast.svelte.js';notificar('hola');</script>`
		),
		[]
	);
	// Las tres páginas del panel pasan el guard.
	for (const ruta of [LISTA, DETALLE, ALTA]) {
		assert.deepEqual(identificadoresLibres(fuente(ruta)), [], ruta);
	}
});

// --- DW-4.3: detalle editable con toggle ---

test('DW-4.3: puedeToggle bloquea la propia cuenta y exige objetivo y sesión', () => {
	assert.equal(puedeToggle({ id: 5 }, { id: 5 }), false, 'auto-desactivarse');
	assert.equal(puedeToggle({ id: 5 }, { id: 7 }), true);
	assert.equal(puedeToggle(null, { id: 7 }), false);
	assert.equal(puedeToggle({ id: 5 }, null), false);
	assert.equal(puedeToggle({}, { id: 7 }), false, 'sin id de objetivo');
	assert.equal(puedeToggle({ id: 5 }, {}), false, 'sin id de sesión');
});

test('DW-4.3: fusionarUsuario conserva lo que el PATCH no devuelve', () => {
	const usuario = {
		id: 5,
		email: 'ana@example.com',
		username: 'ana',
		dni: '30111223',
		first_name: 'Ana',
		is_active: true
	};

	// La respuesta del update-serializer trae perfil + is_active, no email/dni/username.
	const fusionado = fusionarUsuario(usuario, { first_name: 'Ana María', is_active: false });
	assert.equal(fusionado.first_name, 'Ana María');
	assert.equal(fusionado.is_active, false);
	assert.equal(fusionado.email, 'ana@example.com');
	assert.equal(fusionado.dni, '30111223');
	assert.equal(fusionado.username, 'ana');
	assert.deepEqual(fusionarUsuario(usuario, null), usuario, 'respuesta ausente no rompe');
});

test('DW-4.3: el detalle cablea edición, toggle y reflejo inmediato', () => {
	const detalle = fuente(DETALLE);
	// Edición de perfil por PATCH (FormData) y toggle con la respuesta aplicada al estado.
	assert.match(detalle, /method: 'PATCH'/);
	assert.match(detalle, /is_active: !usuario\.is_active/);
	assert.match(detalle, /fusionarUsuario\(usuario, r\)/);
	assert.match(detalle, /puedeToggle\(usuario, session\.user\)/);
	assert.match(detalle, /No podés desactivar tu propia cuenta\./);
	// email/username/dni son solo lectura: no hay inputs editables con esos nombres.
	assert.doesNotMatch(detalle, /name="(email|dni|username)"/);
});

// --- DW-4.4: alta con errores por campo ---

test('DW-4.4: fieldErrors mapea el 400 del alta a mensajes por campo', () => {
	const errores = fieldErrors({
		email: ['Ya existe una cuenta con este email.'],
		password2: ['Las contraseñas no coinciden.'],
		dni: 'Ya existe una cuenta con ese DNI.'
	});
	assert.equal(errores.email, 'Ya existe una cuenta con este email.');
	assert.equal(errores.password2, 'Las contraseñas no coinciden.');
	assert.equal(errores.dni, 'Ya existe una cuenta con ese DNI.');
});

test('DW-4.4: bodies no confiables del API se normalizan sin romper', () => {
	assert.deepEqual(fieldErrors(['Error general.']), { detail: 'Error general.' });
	assert.deepEqual(fieldErrors({ non_field_errors: ['Algo salió mal.'] }), {
		non_field_errors: 'Algo salió mal.'
	});
	for (const data of [null, undefined, '', 'texto', 42]) {
		assert.deepEqual(fieldErrors(data), {}, JSON.stringify(data));
	}
});

test('DW-4.4: la página de alta cablea POST, errores por campo y mismatch', () => {
	const alta = fuente(ALTA);
	assert.match(alta, /api\('\/admin\/usuarios\/', \{ method: 'POST', body: data, form: true \}\)/);
	assert.match(alta, /fieldErrors\(error\.data\)/);
	assert.match(alta, /form\.password\.value !== form\.password2\.value/);
	// Cada campo con error tiene su bloque (el patrón ARIA del proyecto).
	assert.match(alta, /\{#if errors\.email\}/);
	assert.match(alta, /\{#if errors\.dni\}/);
	assert.match(alta, /\{#if errors\.password2\}/);
	// Sin autologin: no se guardan tokens; éxito → aviso + volver al listado.
	assert.match(alta, /notificar\('Usuario creado\.'\)/);
	assert.match(alta, /goto\(resolve\('\/admin\/usuarios'\)\)/);
});

// --- Bordes más allá de los DW ---

test('admin: nombreUsuario usa nombre y apellido, o el usuario', () => {
	assert.equal(nombreUsuario({ first_name: 'Ana', last_name: 'Perez' }), 'Ana Perez');
	assert.equal(nombreUsuario({ first_name: 'Ana', last_name: '' }), 'Ana');
	assert.equal(nombreUsuario({ username: 'ana' }), 'ana');
	assert.equal(nombreUsuario({ first_name: '', last_name: '', username: '' }), '');
	assert.equal(nombreUsuario(null), '');
});

test('admin: $lib/api.js re-exporta fieldErrors (imports existentes intactos)', () => {
	assert.match(fuente('lib/api.js'), /export \{ fieldErrors \} from '\.\/errores\.js';/);
	// Y no queda una copia local duplicada.
	assert.doesNotMatch(fuente('lib/api.js'), /export function fieldErrors/);
});
