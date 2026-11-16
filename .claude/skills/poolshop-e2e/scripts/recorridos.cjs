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

Object.assign(RECORRIDOS, {
	// Fase 1: "Ropa" en el select y precio total calculado (no editable).
	async categorias(page) {
		await ingresar(page);
		await page.goto(`${BASE}/pools/nuevo`);
		await page.waitForSelector('#categoria option:nth-child(2)', { state: 'attached' });
		const borrador = page.getByText('Empezar de cero');
		if (await borrador.isVisible()) await borrador.click();
		const opciones = await page.locator('#categoria option').allTextContents();
		if (!opciones.includes('Ropa')) throw new Error(`falta Ropa: ${opciones.join(', ')}`);
		if (opciones.includes('Alimentos')) throw new Error('Alimentos sigue apareciendo');
		const etiqueta = await page.locator('#precio_total').evaluate((el) => el.tagName);
		if (etiqueta !== 'OUTPUT') throw new Error(`el total es editable (${etiqueta})`);
		await page.fill('#precio_unitario', '1234.5');
		await page.fill('#cantidad_total', '3');
		const total = (await page.locator('#precio_total').textContent()).replace(/\s+/g, ' ').trim();
		if (!total.includes('3.703,50')) throw new Error(`total calculado incorrecto: "${total}"`);
		await page.locator('#precio_total').scrollIntoViewIfNeeded();
		await page.screenshot({ path: path.join(CAPTURAS, 'total-calculado.png') });
	},

	// Fase 1: el integrante ve los datos para transferir, sube el comprobante y al
	// creador le llega el aviso. Requiere `sembrar.py` (POOL_PAGOS) y --pool <id>.
	async pagos(page) {
		if (!args.pool) throw new Error('falta --pool <id> (lo imprime sembrar.py)');
		await ingresar(page);
		await page.goto(`${BASE}/pools/${args.pool}?seccion=pagos`);
		await page.getByText('poolshop.admin.mp').waitFor({ timeout: 10000 });
		await page.locator('.transferir').scrollIntoViewIfNeeded();
		await page.waitForTimeout(700); // fin de la animación de entrada
		await page.screenshot({ path: path.join(CAPTURAS, 'pagos-datos-transferencia.png') });
		await page.setInputFiles('#comprobante', path.join(IMAGENES, 'foto.png'));
		await page.getByRole('button', { name: 'Enviar comprobante' }).click();
		await page.getByText('Esperando que el administrador revise').waitFor({ timeout: 10000 });

		const admin = await page.context().browser().newContext({ viewport: { width: 1280, height: 900 } });
		const pAdmin = await admin.newPage();
		await pAdmin.goto(`${BASE}/login`);
		await pAdmin.fill('#email', args.admin ?? 'admin@poolshop.test');
		await pAdmin.fill('#password', CLAVE);
		await pAdmin.click('button[type=submit]');
		await pAdmin.waitForURL((url) => !url.pathname.startsWith('/login'));
		await pAdmin.goto(`${BASE}/notificaciones`);
		await pAdmin.getByText('envió su comprobante').first().waitFor({ timeout: 10000 });
		await pAdmin.screenshot({ path: path.join(CAPTURAS, 'pagos-aviso-creador.png') });
		await pAdmin.goto(`${BASE}/pools/${args.pool}?seccion=pagos`);
		await pAdmin.getByText('Recaudado').first().waitFor({ timeout: 10000 });
		await pAdmin.locator('.pagos').scrollIntoViewIfNeeded();
		await pAdmin.waitForTimeout(700);
		await pAdmin.screenshot({ path: path.join(CAPTURAS, 'pagos-resumen-creador.png') });
		await admin.close();
	}
});

async function ingresarComo(contexto, email) {
	const pagina = await contexto.newPage();
	await pagina.goto(`${BASE}/login`);
	await pagina.fill('#email', email);
	await pagina.fill('#password', CLAVE);
	await pagina.click('button[type=submit]');
	await pagina.waitForURL((url) => !url.pathname.startsWith('/login'));
	return pagina;
}

Object.assign(RECORRIDOS, {
	// Fase 2: el organizador crea un pool de remeras con talles y colores, un
	// integrante se une con dos variantes y el organizador ve el pedido por variante.
	async variantes(page) {
		const navegador = page.context().browser();
		const admin = await navegador.newContext({ viewport: { width: 1280, height: 900 } });
		const pa = await ingresarComo(admin, args.admin ?? 'admin@poolshop.test');
		await pa.goto(`${BASE}/pools/nuevo`);
		await pa.waitForSelector('#categoria option:nth-child(2)', { state: 'attached' });
		const borrador = pa.getByText('Empezar de cero');
		if (await borrador.isVisible()) await borrador.click();
		await pa.fill('#titulo', 'Remeras e2e con talles');
		await pa.fill('#nombre_producto', 'Remera algodón peinado');
		await pa.selectOption('#categoria', { label: 'Ropa' });
		await pa.selectOption('#subcategoria', { label: 'Remera' });
		for (const opcion of ['S', 'M', 'Negro', 'Blanco']) {
			await pa.locator('label.opcion', { hasText: new RegExp(`^\\s*${opcion}\\s*$`) }).click();
		}
		await pa.fill('#precio_unitario', '8500');
		await pa.fill('#cantidad_total', '12');
		await pa.fill('#fecha_caducidad', new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10));
		await pa.fill('#direccion', 'Belgrano 1200');
		await pa.fill('#ciudad', 'Corrientes');
		await pa.locator('.categoria-variantes').scrollIntoViewIfNeeded();
		await pa.screenshot({ path: path.join(CAPTURAS, 'variantes-crear.png') });
		await pa.click('#pool-form button[type=submit], button[form=pool-form][type=submit]');
		await pa.waitForURL(/\/pools\/\d+/, { timeout: 20000 });
		const id = pa.url().match(/\/pools\/(\d+)/)[1];

		await page.goto(`${BASE}/login`);
		await page.fill('#email', EMAIL);
		await page.fill('#password', CLAVE);
		await page.click('button[type=submit]');
		await page.waitForURL((url) => !url.pathname.startsWith('/login'));
		await page.goto(`${BASE}/pools/${id}`);
		await page.selectOption('#variante-0-Talle', 'M');
		await page.selectOption('#variante-0-Color', 'Negro');
		await page.fill('#variante-0-cantidad', '2');
		await page.getByRole('button', { name: '+ Agregar otra variante' }).click();
		await page.selectOption('#variante-1-Talle', 'S');
		await page.selectOption('#variante-1-Color', 'Blanco');
		await page.fill('#variante-1-cantidad', '1');
		await page.fill('#telefono', '3794555123');
		await page.locator('.filas').scrollIntoViewIfNeeded();
		await page.screenshot({ path: path.join(CAPTURAS, 'variantes-unirse.png') });
		await page.getByRole('button', { name: 'Unirme al pool' }).click();
		await page.getByText('Te uniste').first().waitFor({ timeout: 10000 });

		await pa.goto(`${BASE}/pools/${id}?seccion=participantes`);
		const tabla = pa.locator('.resumen-variantes__tabla');
		await tabla.waitFor({ timeout: 10000 });
		const filas = await tabla.locator('tbody tr').evaluateAll((trs) =>
			trs.map((tr) => [...tr.cells].map((td) => td.textContent.trim()).join(' = '))
		);
		if (!filas.includes('M · Negro = 2') || !filas.includes('S · Blanco = 1')) {
			throw new Error(`resumen inesperado: ${filas.join(' | ')}`);
		}
		await tabla.scrollIntoViewIfNeeded();
		await pa.waitForTimeout(600);
		await pa.screenshot({ path: path.join(CAPTURAS, 'variantes-resumen.png') });
		await admin.close();
	},

	// Fase 2: un link que no se puede leer explica por qué (no un aviso genérico).
	async autocompletar(page) {
		await ingresar(page);
		await page.goto(`${BASE}/pools/nuevo`);
		await page.fill('#enlace', 'https://no-existe-poolshop-e2e.invalid/producto?utm_source=wa#x');
		await page.getByRole('button', { name: 'Autocompletar' }).click();
		const aviso = page.getByText('No pudimos abrir el enlace');
		await aviso.waitFor({ timeout: 20000 });
		const enlace = await page.inputValue('#enlace');
		if (enlace.includes('utm_source')) throw new Error(`el enlace no se limpió: ${enlace}`);
		await page.screenshot({ path: path.join(CAPTURAS, 'autocompletar-motivo.png') });
	}
});

Object.assign(RECORRIDOS, {
	// Fase 3: el admin ve la jerarquía y los atributos de una subcategoría.
	async categoriasAdmin(page) {
		await page.goto(`${BASE}/login`);
		await page.fill('#email', args.admin ?? 'admin@poolshop.test');
		await page.fill('#password', CLAVE);
		await page.click('button[type=submit]');
		await page.waitForURL((url) => !url.pathname.startsWith('/login'));
		await page.goto(`${BASE}/admin/categorias`);
		await page.getByRole('button', { name: 'Remera', exact: true }).click();
		await page.getByText('Atributos de Remera').waitFor();
		const talle = await page.locator('.fila input').nth(1).inputValue();
		if (!talle.includes('XS')) throw new Error(`atributos de Remera inesperados: ${talle}`);
		await page.screenshot({ path: path.join(CAPTURAS, 'categorias-admin.png') });
	}
});

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
