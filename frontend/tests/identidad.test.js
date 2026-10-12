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
const LOGO = fuente('src/lib/Logo.svelte');

// --- Poda P1 (rediseño) ----------------------------------------------------
// Quedaron fuera los pins del sistema visual viejo que el rediseño dejó obsoletos:
//   · Logo: isotipo "dos círculos" + wordmark "PoolShop." → se reemplazó por el del
//     mockup (P en caja roja + "Pool"+"Shop" naranja). Se podaron los tests que
//     pineaban el `stroke="var(--acento)"`, los tamaños (1.3/1.2/2.75rem) y el hide
//     ≤520px (pins de markup viejo, no detectaban defectos de comportamiento).
//   · Paleta: `--acento` dejó de ser azul (ahora rojo de texto), `--papel` ahora es
//     blanco. Los tests que pineaban `--papel/#f5f3ee`, `--acento===--c-azul`,
//     `--linea-control #8f8b83` y el cross-check `theme-color ↔ --papel` quedaron
//     obsoletos por el propio DW-1.1 (nueva paleta). Se podan con razón.
//   Se conservan los que siguen guardando invariantes reales: "no quedan literales de
//   color fuera de :root" (disciplina de tokens), el nombre accesible del isotipo
//   (restaurado abajo: la guarda sigue válida con el logo nuevo) y los de Node (DW-6.2).

// --- DW-6.1: marca y favicon ---

test('DW-6.1: app.html apunta al favicon de la marca', () => {
	assert.match(APP_HTML, /rel="icon"[^>]*href="\/favicon-poolshop\.svg"/);
	assert.ok(existsSync(new URL('static/favicon-poolshop.svg', RAIZ)), 'falta el favicon referenciado');
});

test('DW-6.1: el isotipo expone nombre accesible solo cuando el wordmark no está visible', async () => {
	const conNombre = await logoRender({});
	assert.match(conNombre.body, /aria-hidden="true"/);
	assert.doesNotMatch(conNombre.body, /aria-label="PoolShop"/);

	const sinNombre = await logoRender({ conNombre: false });
	assert.match(sinNombre.body, /role="img"/);
	assert.match(sinNombre.body, /aria-label="PoolShop"/);
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

// --- Helpers ---

// Compila y renderiza `Logo.svelte` con las herramientas reales de Svelte: verifica
// el contrato efectivo (el DOM que el componente produce), que un pin de fuente no
// puede ver. La guarda "sin literales de color en el render" la aporta el test
// "no quedan literales de color fuera de los tokens" (app.css), no este helper.
const CACHE = new URL('../node_modules/.cache/', import.meta.url);
let logoServer;
async function logoRender(props) {
	if (!logoServer) {
		const { js } = compile(LOGO, { filename: 'Logo.svelte', generate: 'server' });
		const tmp = new URL('logo-server.mjs', CACHE);
		mkdirSync(CACHE, { recursive: true });
		writeFileSync(tmp, js.code);
		try {
			logoServer = (await import(tmp.href)).default;
		} finally {
			rmSync(tmp, { force: true });
		}
	}
	return { body: render(logoServer, { props }).body };
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
