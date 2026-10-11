import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { compile } from 'svelte/compiler';
import { render } from 'svelte/server';

const RAIZ = new URL('../', import.meta.url);

function fuente(ruta) {
	return readFileSync(new URL(ruta, RAIZ), 'utf8');
}

function json(ruta) {
	return JSON.parse(fuente(ruta));
}

const APP_CSS = fuente('src/app.css');
const APP_HTML = fuente('src/app.html');
const LAYOUT = fuente('src/routes/+layout.svelte');
const LOGO = fuente('src/lib/Logo.svelte');

// --- DW-6.1: marca y favicon ---

test('DW-6.1: el isotipo renderizado hereda la paleta (sin literales de color)', async () => {
	// Ejecuta el componente real: lo que el navegador recibe, no un pin de fuente.
	const { body } = await logoRender({ class: 'marca--cabecera' });
	assert.match(body, /stroke="currentColor"/);
	assert.match(body, /stroke="var\(--acento\)"/);
	assert.ok(
		!/#[0-9a-fA-F]{3,8}\b/.test(body),
		'el render no hardcodea colores: hereda la paleta'
	);
});

test('DW-6.1: el isotipo expone nombre accesible solo cuando el wordmark no está visible', async () => {
	const conNombre = await logoRender({});
	assert.match(conNombre.body, /aria-hidden="true"/);
	assert.doesNotMatch(conNombre.body, /aria-label="PoolShop"/);

	const sinNombre = await logoRender({ conNombre: false });
	assert.match(sinNombre.body, /role="img"/);
	assert.match(sinNombre.body, /aria-label="PoolShop"/);
});

test('DW-6.1: las variantes de tamaño de la marca matchean el DOM renderizado', async () => {
	for (const [clase, tamano] of [
		['marca--cabecera', '1.3rem'],
		['marca--pie', '1.2rem'],
		['auth__logo', '2.75rem']
	]) {
		const { body, css } = await logoRender({ class: clase });
		// El span raíz lleva la clase del contexto y el hash propio del componente.
		const span = body.match(new RegExp(`class="marca ${clase} (svelte-\\w+)"`));
		assert.ok(span, `${clase}: el span renderizado no lleva la clase con el hash del componente`);
		// La regla emitida queda atada a ese mismo hash: matchea de verdad (el default
		// de .marca pierde por orden dentro de la misma hoja del componente).
		assert.match(
			css,
			new RegExp(`\\.${clase}\\.${span[1]} \\{[^}]*font-size: ${tamano.replace('.', '\\.')}`),
			`${clase}: la regla emitida no matchea el span renderizado`
		);
	}
});

test('DW-6.1: el wordmark de la cabecera se oculta en pantallas chicas desde el componente', async () => {
	const { body, css } = await logoRender({ class: 'marca--cabecera' });
	const hash = body.match(/svelte-\w+/)[0];
	assert.match(body, /class="marca__nombre svelte-/, 'sin wordmark no hay nada que ocultar');
	assert.match(
		css,
		new RegExp(
			`@media \\(max-width: 520px\\) \\{[^@]*\\.marca--cabecera\\.${hash} \\.marca__nombre[^{]*\\{[^}]*display: none`
		),
		'el hide en ≤520px no matchea el span renderizado'
	);
});

test('DW-6.1: app.html apunta al favicon nuevo y el theme-color acompaña al papel', () => {
	assert.match(APP_HTML, /rel="icon"[^>]*href="\/favicon-poolshop\.svg"/);
	assert.ok(existsSync(new URL('static/favicon-poolshop.svg', RAIZ)), 'falta el favicon referenciado');
	// Cross-check con app.css: la barra del navegador usa el papel del sistema.
	const papel = APP_CSS.match(/--papel:\s*(#[0-9a-fA-F]{3,8})/)[1];
	assert.match(APP_HTML, new RegExp(`name="theme-color" content="${papel}"`, 'i'));
});

// --- DW-6.2: requisito de Node ---

test('DW-6.2: engines.node coincide con el rango que exige la Vite instalada', () => {
	const pkg = json('package.json');
	const vite = json('node_modules/vite/package.json');
	assert.equal(typeof pkg.engines?.node, 'string');
	assert.equal(typeof vite.engines?.node, 'string');
	assert.equal(
		pkg.engines.node,
		vite.engines.node,
		`el rango debe copiar el de vite ${vite.version}`
	);
	// Declarar menos permitiría instalar en un Node que Vite rechaza.
	assert.match(pkg.engines.node, /20\.19/);
});

test('DW-6.2: .npmrc hace cumplir el rango de Node declarado', () => {
	assert.match(fuente('.npmrc'), /engine-strict=true/);
});

test('DW-6.2: el Node actual satisface el rango declarado', () => {
	const rango = json('package.json').engines.node;
	assert.ok(
		rango.split('||').some((parte) => cumple(process.version, parte.trim())),
		`${process.version} no satisface ${rango}`
	);
});

// --- DW-6.3: paleta consolidada ---

test('DW-6.3: no quedan literales de color fuera de los tokens', () => {
	const { raiz, soloPaleta } = repartoDeColores();
	assert.match(raiz, /--papel:/, 'el bloque :root define la paleta');
	// El único literal deliberado es el blanco de texto sobre color.
	assert.deepEqual(
		[...new Set(soloPaleta)],
		['#fff'],
		'los colores fuera de :root se consolidan en tokens'
	);
});

test('DW-6.3: la cabecera toma su color del token de papel', () => {
	const papel = APP_CSS.match(/--papel:\s*(#[0-9a-fA-F]{3,8})/)[1];
	const fondo = LAYOUT.match(/background: (rgba?\([^)]+\))/)[1];
	// Mismo color que --papel, con alpha para el vidrio esmerilado (no exige el mismo alpha).
	assert.equal(formaRgb(fondo), formaRgb(papel), 'el fondo de la cabecera debe derivar de --papel');
	assert.match(fondo, /rgba\(/);
});

test('DW-6.3: la paleta está completa y conserva los valores medidos', () => {
	const { raiz } = repartoDeColores();
	// Cada token es un hex o un alias de otro token (--acento: var(--c-azul)).
	const declarados = [...raiz.matchAll(/(--[a-z0-9-]+):\s*([^;]+);/g)].map((m) => [
		m[1],
		m[2].trim()
	]);
	const tokens = new Map(declarados);
	const hex = (nombre) => {
		const valor = tokens.get(nombre);
		if (!valor) return undefined;
		const alias = valor.match(/^var\((--[a-z0-9-]+)\)$/);
		return alias ? hex(alias[1]) : valor;
	};
	const completos = [
		'--papel',
		'--superficie',
		'--superficie-alt',
		'--tinta',
		'--tinta-suave',
		'--tinta-tenue',
		'--linea',
		'--linea-fuerte',
		'--linea-control',
		'--c-azul',
		'--c-verde',
		'--c-ambar',
		'--c-coral',
		'--c-violeta',
		'--c-teal',
		'--tinte-azul',
		'--tinte-verde',
		'--tinte-ambar',
		'--tinte-coral',
		'--tinte-violeta',
		'--tinte-teal',
		'--acento',
		'--acento-suave',
		'--acento-fuerte',
		'--peligro',
		'--peligro-suave',
		'--exito',
		'--alerta',
		'--texto-exito',
		'--texto-peligro',
		'--texto-alerta',
		'--texto-acento',
		'--borde-exito',
		'--borde-acento',
		'--borde-alerta',
		'--borde-peligro',
		'--borde-peligro-fuerte',
		'--skeleton-base',
		'--skeleton-brillo'
	];
	for (const nombre of completos) {
		assert.ok(tokens.has(nombre), `falta el token ${nombre}`);
		assert.match(hex(nombre), /^#[0-9a-f]{3,6}$/i, `${nombre} no resuelve a un hex válido`);
	}
	// Borde de campos: 3.06:1 sobre papel (WCAG 1.4.11) — la consolidación no lo toca.
	assert.equal(hex('--linea-control'), '#8f8b83');
	assert.equal(hex('--borde-peligro-fuerte'), '#dfb7b3');
	assert.equal(hex('--acento'), hex('--c-azul'), 'el acento sigue siendo el azul de la paleta');
});

// --- Helpers ---

// Compila y renderiza `Logo.svelte` con las herramientas reales de Svelte: verifica
// el contrato efectivo (el DOM que el componente produce y el CSS que recibe el
// navegador, atados por el hash de scoping), que un pin de fuente no puede ver.
const CACHE = new URL('../node_modules/.cache/', import.meta.url);
let logoServer;
async function logoRender(props) {
	if (!logoServer) {
		const { js, css } = compile(LOGO, { filename: 'Logo.svelte', generate: 'server' });
		const tmp = new URL('logo-server.mjs', CACHE);
		mkdirSync(CACHE, { recursive: true });
		writeFileSync(tmp, js.code);
		try {
			logoServer = { Componente: (await import(tmp.href)).default, css: css.code };
		} finally {
			rmSync(tmp, { force: true });
		}
	}
	return { body: render(logoServer.Componente, { props }).body, css: logoServer.css };
}

// Separa el bloque :root (paleta) del resto de las reglas: fuera de :root solo puede
// quedar el blanco literal (texto sobre color).
function repartoDeColores() {
	const finRaiz = APP_CSS.indexOf('}');
	const raiz = APP_CSS.slice(0, finRaiz);
	const reglas = APP_CSS.slice(finRaiz);
	const soloPaleta = [...reglas.matchAll(/#[0-9a-fA-F]{3,8}\b/g)].map((m) => m[0]);
	return { raiz, soloPaleta };
}

// Forma "r g b" de un color hex o rgba, para comparar el tono sin exigir el mismo alpha.
function formaRgb(valor) {
	if (valor.startsWith('#')) {
		const hex = valor.slice(1);
		const completo =
			hex.length === 3
				? hex
						.split('')
						.map((c) => c + c)
						.join('')
				: hex;
		return [0, 2, 4].map((i) => parseInt(completo.slice(i, i + 2), 16)).join(' ');
	}
	return valor
		.match(/rgba?\(([^)]+)\)/)[1]
		.split(',')
		.slice(0, 3)
		.map((p) => Number(p.trim()))
		.join(' ');
}

// Subconjunto de rangos semver: "20.19.1" cumple ">=20.19.0 <21" y "^20.19.0".
// Solo cubre los operadores que usan Vite y el package.json (^, >=, <, ||).
function cumple(version, rango) {
	const [mayor, menor, parche] = version.replace(/^v/, '').split('.').map(Number);
	for (const alternativa of rango.split('||')) {
		let ok = true;
		for (const condicion of alternativa.trim().split(/\s+/)) {
			if (condicion.startsWith('^')) {
				const [M, m, p] = condicion.slice(1).split('.').map(Number);
				ok &&= mayor === M && (menor > m || (menor === m && parche >= p));
			} else if (condicion.startsWith('>=')) {
				const [M, m, p] = condicion.slice(2).split('.').map(Number);
				ok &&= mayor > M || (mayor === M && (menor > m || (menor === m && parche >= p)));
			} else if (condicion.startsWith('<')) {
				const [M, m, p] = condicion.slice(1).split('.').map(Number);
				ok &&= mayor < M || (mayor === M && (menor < m || (menor === m && parche < p)));
			} else {
				ok = false;
			}
		}
		if (ok) return true;
	}
	return false;
}
