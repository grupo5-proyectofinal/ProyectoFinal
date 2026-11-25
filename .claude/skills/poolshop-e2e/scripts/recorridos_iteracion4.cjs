// Recorridos e2e de la Iteración 4 (caducidad y reconfirmación, baja con devolución, visitante,
// chat al finalizar). Requiere los datos de `sembrar_iteracion4.py`.
//
//   node .claude/skills/poolshop-e2e/scripts/recorridos_iteracion4.cjs \
//     --base http://<ip-del-contenedor>:5173 --api http://127.0.0.1:8000 \
//     --capturas <carpeta> [--solo caducidad,baja]
//
// Imprime OK/FALLA por recorrido y sale con código 1 si alguno falla.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');

const args = Object.fromEntries(
	process.argv.slice(2).reduce((pares, valor, i, todos) => {
		if (valor.startsWith('--')) pares.push([valor.slice(2), todos[i + 1]]);
		return pares;
	}, [])
);
const BASE = args.base ?? 'http://localhost:5173';
const API = args.api ?? 'http://127.0.0.1:8000';
const CAPTURAS = args.capturas ?? 'e2e-capturas';
const SOLO = args.solo ? args.solo.split(',') : null;
const CLAVE = 'Clave-segura-123';
fs.mkdirSync(CAPTURAS, { recursive: true });

// IDs de los pools sembrados (por título, vía la API).
async function idDe(titulo) {
	const r = await fetch(`${API}/api/v1/pools/?q=${encodeURIComponent(titulo)}`);
	const datos = await r.json();
	const pool = datos.results.find((p) => p.titulo === titulo);
	if (!pool) throw new Error(`no existe el pool "${titulo}": correr sembrar_iteracion4.py`);
	return pool.id;
}

// El login tiene un límite de 10 por minuto por IP: se inicia sesión una vez por usuario y
// los demás recorridos reutilizan la sesión guardada.
const SESIONES = {};

async function sesion(browser, usuario) {
	const opciones = { viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 1 };
	if (SESIONES[usuario]) {
		const contexto = await browser.newContext({ ...opciones, storageState: SESIONES[usuario] });
		return { contexto, page: await contexto.newPage() };
	}
	const contexto = await browser.newContext(opciones);
	const page = await contexto.newPage();
	await page.goto(`${BASE}/login`);
	await page.fill('#identificador', `${usuario}@poolshop.test`);
	await page.fill('#password', CLAVE);
	await page.click('button[type=submit]');
	await page.waitForURL((url) => !url.pathname.startsWith('/login'));
	SESIONES[usuario] = await contexto.storageState();
	return { contexto, page };
}

const captura = (page, nombre) => page.screenshot({ path: path.join(CAPTURAS, `${nombre}.png`), fullPage: true });

async function verTexto(page, texto, timeout = 10000) {
	await page.getByText(texto).first().waitFor({ state: 'visible', timeout });
}

function fechaEn(dias) {
	const d = new Date(Date.now() + dias * 86400000);
	return d.toISOString().slice(0, 10);
}

const RECORRIDOS = {
	// El creador extiende el plazo; ana sigue y beto sale; el pool vuelve a Abierto.
	async caducidad(browser) {
		const id = await idDe('E2E caducado');
		const admin = await sesion(browser, 'admin');
		await admin.page.goto(`${BASE}/pools/${id}`);
		await verTexto(admin.page, 'Este pool caducó');
		await captura(admin.page, 'caducidad-1-creador');

		// Una fecha dentro del período de reconfirmación se rechaza junto al campo.
		await admin.page.fill('#nueva_fecha', fechaEn(2));
		await admin.page.getByRole('button', { name: 'Extender plazo' }).click();
		await verTexto(admin.page, 'Elegí una fecha posterior al plazo de reconfirmación');
		await captura(admin.page, 'caducidad-2-fecha-rechazada');

		await admin.page.fill('#nueva_fecha', fechaEn(10));
		await admin.page.getByRole('button', { name: 'Extender plazo' }).click();
		await verTexto(admin.page, 'Esperando confirmación');
		await captura(admin.page, 'caducidad-3-esperando');
		await admin.contexto.close();

		const ana = await sesion(browser, 'ana');
		await ana.page.goto(`${BASE}/pools/${id}`);
		await verTexto(ana.page, 'Sigo en el pool');
		await captura(ana.page, 'caducidad-4-integrante');
		await ana.page.getByRole('button', { name: 'Sigo en el pool' }).click();
		await verTexto(ana.page, 'Ya respondiste');
		await ana.contexto.close();

		const beto = await sesion(browser, 'beto');
		await beto.page.goto(`${BASE}/pools/${id}`);
		await beto.page.getByRole('button', { name: 'Salir' }).click();
		await beto.page.waitForTimeout(1500);
		await beto.contexto.close();

		const admin2 = await sesion(browser, 'admin');
		await admin2.page.goto(`${BASE}/pools/${id}`);
		await verTexto(admin2.page, 'Abierto');
		if (await admin2.page.getByText('Esperando confirmación').first().isVisible().catch(() => false)) {
			throw new Error('el pool sigue esperando confirmaciones');
		}
		await captura(admin2.page, 'caducidad-5-abierto');
		await admin2.contexto.close();
	},

	// Pedido de baja → aprobar → devolución hecha → confirmada.
	async baja(browser) {
		const id = await idDe('E2E baja');
		const ana = await sesion(browser, 'ana');
		await ana.page.goto(`${BASE}/pools/${id}`);
		await ana.page.getByRole('button', { name: 'Pedir baja y devolución' }).click();
		await ana.page.fill('#motivo-baja', 'Ya no lo necesito');
		await ana.page.getByRole('button', { name: 'Pedir la baja' }).click();
		await verTexto(ana.page, 'Esperando respuesta');
		await captura(ana.page, 'baja-1-pedido');
		await ana.contexto.close();

		const admin = await sesion(browser, 'admin');
		await admin.page.goto(`${BASE}/pools/${id}`);
		await verTexto(admin.page, 'Pedidos de baja');
		await admin.page.getByRole('button', { name: 'Aprobar' }).click();
		await admin.page.getByRole('button', { name: 'Aprobar la baja' }).click();
		await verTexto(admin.page, 'Esperando devolución');
		await captura(admin.page, 'baja-2-aprobada');
		await admin.page.getByRole('button', { name: 'Ya devolví el dinero' }).click();
		await verTexto(admin.page, 'Devolución realizada');
		await admin.contexto.close();

		const ana2 = await sesion(browser, 'ana');
		await ana2.page.goto(`${BASE}/pools/${id}`);
		await ana2.page.getByRole('button', { name: 'Confirmar que lo recibí' }).click();
		await verTexto(ana2.page, 'Devolución recibida');
		await captura(ana2.page, 'baja-3-confirmada');
		await ana2.contexto.close();
	},

	// Sin sesión: listado sin datos privados, detalle y perfil llevan al login, mejoras al inicio.
	async visitante(browser) {
		const contexto = await browser.newContext({ viewport: { width: 1280, height: 900 } });
		const page = await contexto.newPage();
		const id = await idDe('E2E baja');
		const lista = await (await fetch(`${API}/api/v1/pools/`)).json();
		const tarjeta = lista.results[0];
		for (const campo of ['direccion', 'latitud', 'longitud', 'miembros', 'enlace']) {
			if (campo in tarjeta) throw new Error(`el listado anónimo expone ${campo}`);
		}
		await page.goto(`${BASE}/pools`);
		await verTexto(page, 'E2E');
		await captura(page, 'visitante-1-listado');
		await page.goto(`${BASE}/pools/${id}`);
		await page.waitForURL(/\/login\?next=/, { timeout: 10000 });
		await page.goto(`${BASE}/usuarios/1`);
		await page.waitForURL(/\/login\?next=/, { timeout: 10000 });
		for (const ruta of ['/mayoristas', '/comparar']) {
			await page.goto(`${BASE}${ruta}`);
			await page.waitForURL((url) => url.pathname === '/', { timeout: 10000 });
		}
		await contexto.close();
	},

	// Al finalizar, el chat se lee pero no se escribe.
	async chat(browser) {
		const id = await idDe('E2E finalizado');
		const ana = await sesion(browser, 'ana');
		await ana.page.goto(`${BASE}/pools/${id}?seccion=chat`);
		await verTexto(ana.page, 'Gracias por todo');
		await verTexto(ana.page, 'solo lectura');
		if (await ana.page.locator('textarea').count()) throw new Error('el chat finalizado permite escribir');
		await captura(ana.page, 'chat-finalizado');
		await ana.contexto.close();
	}
};

(async () => {
	const browser = await chromium.launch();
	let fallas = 0;
	for (const [nombre, fn] of Object.entries(RECORRIDOS)) {
		if (SOLO && !SOLO.includes(nombre)) continue;
		try {
			await fn(browser);
			console.log(`OK     ${nombre}`);
		} catch (error) {
			fallas += 1;
			console.log(`FALLA  ${nombre}: ${error.message.split('\n')[0]}`);
		}
	}
	await browser.close();
	process.exit(fallas ? 1 : 0);
})();
