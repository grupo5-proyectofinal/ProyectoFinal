// Recorridos e2e de PoolShop con Playwright (Chromium preinstalado).
//
//   node .claude/skills/poolshop-e2e/scripts/recorridos.cjs \
//     --base http://<ip-del-contenedor>:5173 --email ana@poolshop.test \
//     --clave Clave-segura-123 --imagenes <carpeta> --capturas <carpeta> [--solo sesion,foto]
//
// Cada recorrido imprime OK/FALLA con el motivo y deja capturas. Sale con código 1
// si alguno falla. Usar la IP del contenedor (no localhost) reproduce el caso del
// cliente que entra desde otro dispositivo de la red.
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
const EMAIL = args.email ?? 'ana@poolshop.test';
const CLAVE = args.clave ?? 'Clave-segura-123';
const IMAGENES = args.imagenes ?? 'e2e-imagenes';
const CAPTURAS = args.capturas ?? 'e2e-capturas';
const SOLO = args.solo ? args.solo.split(',') : null;
const CLAVE_SESION = 'poolshop.session';

fs.mkdirSync(CAPTURAS, { recursive: true });

async function ingresar(page) {
	await page.goto(`${BASE}/login`);
	await page.fill('#email', EMAIL);
	await page.fill('#password', CLAVE);
	await page.click('button[type=submit]');
	await page.waitForURL((url) => !url.pathname.startsWith('/login'));
}

async function imagenCargada(locator) {
	await locator.first().waitFor({ state: 'visible', timeout: 10000 });
	return locator.first().evaluate((img) =>
		img.complete ? img.naturalWidth > 0 : new Promise((ok) => {
			img.onload = () => ok(img.naturalWidth > 0);
			img.onerror = () => ok(false);
		})
	);
}

const RECORRIDOS = {
	// Access vencido + refresh válido: la página se recarga y la sesión sigue.
	async sesion(page) {
		await ingresar(page);
		await page.evaluate((k) => {
			const s = JSON.parse(localStorage.getItem(k));
			s.access = 'vencido.' + s.access.split('.')[1] + '.firma-invalida';
			localStorage.setItem(k, JSON.stringify(s));
		}, CLAVE_SESION);
		await page.goto(`${BASE}/pools/nuevo`);
		await page.waitForTimeout(1500);
		if (!page.url().includes('/pools/nuevo')) throw new Error(`terminó en ${page.url()}`);
		const categorias = await page.locator('#categoria option').count();
		if (categorias < 2) throw new Error('no cargaron las categorías');
		await page.screenshot({ path: path.join(CAPTURAS, 'sesion-renovada.png') });
	},

	// Refresh también vencido: aviso "Tu sesión expiró" + login con ?next= + borrador.
	async expirada(page) {
		await ingresar(page);
		await page.goto(`${BASE}/pools/nuevo`);
		await page.fill('#titulo', 'Compra de perfumes (borrador e2e)');
		await page.waitForTimeout(300);
		await page.evaluate((k) => {
			localStorage.setItem(k, JSON.stringify({ access: 'x.y.z', refresh: 'x.y.z' }));
		}, CLAVE_SESION);
		await page.reload();
		await page.waitForURL(/\/login\?next=/, { timeout: 10000 });
		const aviso = await page.getByText('Tu sesión expiró').first().isVisible();
		if (!aviso) throw new Error('no apareció el aviso de sesión expirada');
		await page.screenshot({ path: path.join(CAPTURAS, 'sesion-expirada.png') });
		await page.fill('#email', EMAIL);
		await page.fill('#password', CLAVE);
		await page.click('button[type=submit]');
		await page.waitForURL(/\/pools\/nuevo/);
		await page.waitForTimeout(800);
		const titulo = await page.inputValue('#titulo');
		if (titulo !== 'Compra de perfumes (borrador e2e)') throw new Error(`borrador perdido: "${titulo}"`);
		await page.screenshot({ path: path.join(CAPTURAS, 'borrador-recuperado.png') });
	},

	// Foto de perfil HEIC (iPhone) subida y visible entrando por la IP de la red.
	async foto(page) {
		await ingresar(page);
		await page.goto(`${BASE}/perfil`);
		await page.setInputFiles('#foto', path.join(IMAGENES, 'IMG_0001.HEIC'));
		await page.click('form.perfil__form button[type=submit]');
		await page.getByText('Datos actualizados.').waitFor({ timeout: 10000 });
		await page.reload();
		const ok = await imagenCargada(page.locator('aside img'));
		if (!ok) throw new Error('la foto de perfil no carga');
		await page.screenshot({ path: path.join(CAPTURAS, 'foto-perfil.png') });
	},

	// Crear pool con imagen WEBP y verla en el detalle.
	async pool(page) {
		await ingresar(page);
		await page.goto(`${BASE}/pools/nuevo`);
		await page.waitForSelector('#categoria option:nth-child(2)', { state: 'attached' });
		const borrador = page.getByText('Empezar de cero');
		if (await borrador.isVisible()) await borrador.click();
		await page.fill('#titulo', 'Pool e2e con foto de WhatsApp');
		await page.fill('#nombre_producto', 'Perfume 100 ml');
		await page.selectOption('#categoria', { index: 1 });
		await page.fill('#precio_unitario', '12000');
		await page.fill('#cantidad_total', '20');
		const enUnaSemana = new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10);
		await page.fill('#fecha_caducidad', enUnaSemana);
		await page.fill('#direccion', 'Belgrano 1200');
		await page.fill('#ciudad', 'Corrientes');
		const tipoPago = page.locator('#tipo_pago');
		if (await tipoPago.count()) await tipoPago.selectOption('transferencia');
		await page.setInputFiles('#imagenes', path.join(IMAGENES, 'imagen_de_whatsapp.webp'));
		await page.click('#pool-form button[type=submit], button[form=pool-form][type=submit]');
		await page.waitForURL(/\/pools\/\d+/, { timeout: 15000 });
		if (page.url().includes('aviso=imagenes')) throw new Error('la imagen no se subió');
		const ok = await imagenCargada(page.locator('.hero img, img[alt*="Pool e2e"]'));
		if (!ok) throw new Error('la imagen del pool no carga');
		await page.screenshot({ path: path.join(CAPTURAS, 'pool-con-imagen.png') });
	}
};

(async () => {
	const navegador = await chromium.launch();
	let fallas = 0;
	for (const [nombre, recorrido] of Object.entries(RECORRIDOS)) {
		if (SOLO && !SOLO.includes(nombre)) continue;
		const contexto = await navegador.newContext({ viewport: { width: 1280, height: 900 } });
		const page = await contexto.newPage();
		try {
			await recorrido(page);
			console.log(`OK     ${nombre}`);
		} catch (error) {
			fallas += 1;
			console.log(`FALLA  ${nombre}: ${error.message}`);
			await page.screenshot({ path: path.join(CAPTURAS, `falla-${nombre}.png`) }).catch(() => {});
		}
		await contexto.close();
	}
	await navegador.close();
	process.exit(fallas ? 1 : 0);
})();
