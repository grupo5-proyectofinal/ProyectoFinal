<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount, tick } from 'svelte';
	import { api, fieldErrors } from '$lib/api.js';
	import { aplicarBorrador, borrarBorrador, guardarBorrador, leerBorrador } from '$lib/borrador.js';
	import { moneda } from '$lib/formato.js';
	import {
		camposDesdeVistaPrevia,
		enlaceAnalizable,
		precioTotal
	} from '$lib/producto.js';
	import { session } from '$lib/session.svelte.js';
	import { motivoImagen } from '$lib/imagenes.js';
	import { notificar } from '$lib/toast.svelte.js';
	import PanelEnlace from '$lib/PanelEnlace.svelte';
	import SelectorCategoria from '$lib/SelectorCategoria.svelte';
	import PoolCard from '$lib/PoolCard.svelte';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';

	let categorias = $state([]);
	let errorCategorias = $state(false);
	let archivos = $state([]);
	let errors = $state({});
	let general = $state('');
	let enviando = $state(false);
	let form = $state();
	// Valores vivos del form, solo para la vista previa: el envío sigue leyendo
	// `FormData(form)` como antes.
	let datos = $state({});
	// Autocompletado desde el enlace de la tienda.
	let vistaPrevia = $state(null);
	// Validaciones del sitio (https, acortadores, dominio raro…) antes de publicar.
	let analisisEnlace = $state(null);
	let analizando = $state(false);
	let avisoEnlace = $state('');
	let usarImagen = $state(true);
	let ultimoAnalizado = '';
	let pedidoEnlace = 0;
	// Categoría (dos niveles) y variantes ofrecidas: el selector las expone como
	// inputs ocultos `categoria` y `atributos` dentro del form.
	let categoriaId = $state('');
	let atributos = $state({});
	// Borrador en sessionStorage: sobrevive a un login en el medio.
	const BORRADOR = 'pool-nuevo';
	let borradorRestaurado = $state(false);
	let borradorListo = false;

	const TIPOS_PAGO = [
		['transferencia', 'Transferencia'],
		['sin_especificar', 'Sin especificar']
	];

	$effect(() => {
		api('/categories/')
			.then((r) => {
				categorias = r.results ?? r;
				errorCategorias = false;
			})
			.catch(() => {
				errorCategorias = true;
			})
			// Con las opciones de categoría ya en el DOM, se puede restaurar el borrador.
			.finally(restaurarBorrador);
	});

	async function restaurarBorrador() {
		// El $effect de categorías vuelve a correr cuando cambia el token (renovación,
		// sesión vencida): el borrador se restaura una sola vez, al entrar.
		if (borradorListo) return;
		await tick();
		const borrador = leerBorrador(BORRADOR);
		if (form && borrador && aplicarBorrador(form.elements, borrador)) {
			// Los inputs ocultos del selector no alcanzan: su estado vive en el componente.
			categoriaId = borrador.categoria ?? '';
			try {
				atributos = JSON.parse(borrador.atributos || '{}');
			} catch {
				atributos = {};
			}
			borradorRestaurado = true;
			alInput();
		}
		borradorListo = true;
	}

	function descartarBorrador() {
		borrarBorrador(BORRADOR);
		form?.reset();
		categoriaId = '';
		atributos = {};
		borradorRestaurado = false;
		alInput();
	}

	// El `input` burbujea: un solo handler mantiene la vista previa sincronizada
	// (incluido el precio total, que se deriva de `datos`).
	async function alInput() {
		if (!form) return;
		// Los inputs ocultos del selector de categoría se actualizan en el próximo tick.
		await tick();
		datos = Object.fromEntries(new FormData(form));
		// No pisar el borrador guardado antes de haberlo restaurado.
		if (borradorListo) guardarBorrador(BORRADOR, datos);
	}

	async function analizarEnlace({ forzar = false } = {}) {
		const enlace = form?.elements.enlace.value.trim() ?? '';
		if (!enlaceAnalizable(enlace)) {
			// El panel de confianza es del enlace anterior: no aplica al campo vacío o inválido.
			analisisEnlace = null;
			ultimoAnalizado = '';
			if (forzar) avisoEnlace = 'Pegá un enlace que empiece con https://';
			return;
		}
		if (!forzar && enlace === ultimoAnalizado) return;
		ultimoAnalizado = enlace;
		const actual = ++pedidoEnlace;
		analizando = true;
		avisoEnlace = '';
		try {
			const vista = await api('/pools/previsualizar-enlace/', {
				method: 'POST',
				body: { enlace }
			});
			if (actual !== pedidoEnlace) return;
			analisisEnlace = vista.analisis ?? null;
			// El servidor devuelve el enlace sin parámetros de seguimiento: se guarda ese.
			if (vista.enlace && vista.enlace !== enlace) {
				form.elements.enlace.value = vista.enlace;
				ultimoAnalizado = vista.enlace;
			}
			vistaPrevia = vista.encontrado ? vista : null;
			usarImagen = Boolean(vista.imagen);
			if (!vista.encontrado) {
				avisoEnlace = vista.detail;
				return;
			}
			// Hay datos pero algo no cierra (por ejemplo, el precio está en dólares).
			avisoEnlace = vista.aviso ?? '';
			const actuales = {
				titulo: form.elements.titulo.value,
				descripcion: form.elements.descripcion.value
			};
			for (const [campo, valor] of Object.entries(camposDesdeVistaPrevia(vista, actuales))) {
				form.elements[campo].value = valor;
			}
			alInput();
		} catch (e) {
			if (actual !== pedidoEnlace) return;
			vistaPrevia = null;
			analisisEnlace = null;
			avisoEnlace =
				e?.status === 429
					? 'Demasiados intentos. Esperá un minuto y volvé a probar.'
					: (fieldErrors(e.data).enlace ?? 'No pudimos leer ese enlace. Completá los datos a mano.');
		} finally {
			if (actual === pedidoEnlace) analizando = false;
		}
	}

	// Al pegar, el valor llega recién después del evento: se espera un tick del navegador.
	function alPegarEnlace() {
		setTimeout(() => analizarEnlace(), 0);
	}

	// Los `value` por defecto del DOM (cantidad del creador, mínimo) entran a la
	// vista previa sin duplicarlos en el script.
	onMount(alInput);

	function alElegirImagenes(event) {
		archivos = [...(event.target.files ?? [])];
	}

	async function enviar(event) {
		event.preventDefault();
		errors = {};
		general = '';
		if (archivos.length > 10) {
			general = 'Podés subir hasta 10 imágenes.';
			return;
		}
		enviando = true;
		try {
			const fd = new FormData(form);
			fd.delete('imagenes');
			if (usarImagen && vistaPrevia?.imagen) fd.append('imagen_url', vistaPrevia.imagen);
			const creado = await api('/pools/', { method: 'POST', body: fd, form: true });
			let fallidas = 0;
			for (const archivo of archivos) {
				const imgFd = new FormData();
				imgFd.append('imagen', archivo);
				try {
					await api(`/pools/${creado.id}/imagenes/`, { method: 'POST', body: imgFd, form: true });
				} catch (error) {
					fallidas += 1;
					notificar(`No se pudo subir ${archivo.name}: ${motivoImagen(error)}`, 'error');
				}
			}
			borrarBorrador(BORRADOR);
			goto(resolve(fallidas ? `/pools/${creado.id}?aviso=imagenes` : `/pools/${creado.id}`));
		} catch (e) {
			if (e?.status === 401) {
				// api.js ya avisó y el layout lleva al login; el borrador queda guardado.
				general = 'Tu sesión expiró. Iniciá sesión y vas a encontrar estos datos acá.';
				return;
			}
			const { detail, non_field_errors, ...porCampo } = fieldErrors(e.data);
			errors = porCampo;
			if (detail || non_field_errors) general = detail || non_field_errors;
			else if (!Object.keys(errors).length) general = 'No se pudo crear el pool.';
		} finally {
			enviando = false;
		}
	}

	// --- Vista previa "Así se verá tu pool" (mockup 06) ---
	const HOY = new Date().toISOString().slice(0, 10);
	const numero = (valor) => Math.max(Number(valor) || 0, 0);
	const cantidadTotal = $derived(numero(datos.cantidad_total));
	const cantidadCreador = $derived(numero(datos.cantidad_creador));
	const minPorIntegrante = $derived(numero(datos.min_por_integrante));
	// Precio total = unitario × cantidad (dato calculado, no editable: Iteración 3).
	const precioTotalTexto = $derived(precioTotal(datos.precio_unitario, datos.cantidad_total));
	const totalPool = $derived(precioTotalTexto ? Number(precioTotalTexto) : null);
	const participantes = $derived(
		cantidadTotal && minPorIntegrante
			? Math.ceil(Math.max(cantidadTotal - cantidadCreador, 0) / minPorIntegrante)
			: null
	);

	// Objeto con defaults seguros para reusar `PoolCard` sin tocar el form.
	const preview = $derived({
		id: 0,
		estado: 'abierto',
		imagenes: usarImagen && vistaPrevia?.imagen ? [{ imagen: vistaPrevia.imagen }] : [],
		titulo: datos.titulo?.trim() || 'Tu pool',
		nombre_producto: datos.nombre_producto?.trim() || '',
		categoria_nombre: categorias.find((c) => String(c.id) === String(categoriaId))?.nombre ?? '',
		precio_unitario: datos.precio_unitario,
		cantidad_total: cantidadTotal,
		cantidad_creador: cantidadCreador,
		disponible: Math.max(cantidadTotal - cantidadCreador, 0),
		// Sin fecha la fila se oculta (clase `preview--sin-fecha`), pero el fallback
		// evita que `diasHasta` deje un "Vence en NaN días" en el DOM.
		fecha_caducidad: datos.fecha_caducidad || HOY,
		creador: { username: session.user?.username ?? '' }
	});
</script>

<svelte:head>
	<title>Crear pool — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Crear pool</h1>
		<p>
			Cargá el producto, el precio al por mayor y hasta cuándo se puede sumar la gente. Después
			compartí el enlace.
		</p>
	</div>
</div>

<div class="crear">
	<form id="pool-form" class="crear__form" bind:this={form} onsubmit={enviar} oninput={alInput}>
		{#if borradorRestaurado}
			<Aviso variante="info" class="borrador">
				<span>Recuperamos los datos que estabas cargando.</span>
				<button type="button" class="borrador__descartar" onclick={descartarBorrador}>
					Empezar de cero
				</button>
			</Aviso>
		{/if}
		<fieldset class="seccion">
			<legend class="seccion__titulo">1. Enlace de la oferta</legend>
			<Campo
				id="enlace"
				etiqueta="Enlace del producto"
				ayuda="Opcional. Pegalo y completamos nombre, precio e imagen del producto."
				error={errors.enlace}
			>
				{#snippet children(props)}
					<div class="enlace">
						<input
							id="enlace"
							name="enlace"
							type="url"
							placeholder="https://…"
							onpaste={alPegarEnlace}
							onchange={() => analizarEnlace()}
							{...props}
						/>
						<Boton
							variante="secundario"
							disabled={analizando}
							onclick={() => analizarEnlace({ forzar: true })}
						>
							{#if analizando}<span class="spinner spinner--chico"></span> Leyendo…{:else}Autocompletar{/if}
						</Boton>
					</div>
				{/snippet}
			</Campo>
			<div class="enlace__estado" role="status">
				{#if analizando}
					Buscando los datos del producto…
				{:else if avisoEnlace && !vistaPrevia}
					<Aviso variante="aviso">{avisoEnlace}</Aviso>
				{:else if vistaPrevia}
					{#if avisoEnlace}
						<Aviso variante="aviso">{avisoEnlace}</Aviso>
					{/if}
					<div class="producto">
						{#if vistaPrevia.imagen}
							<img class="producto__imagen" src={vistaPrevia.imagen} alt="" width="72" height="72" />
						{/if}
						<div class="producto__datos">
							<p class="producto__nombre">{vistaPrevia.nombre_producto ?? 'Producto encontrado'}</p>
							<p class="producto__precio">
								{vistaPrevia.precio_unitario
									? `${moneda(vistaPrevia.precio_unitario)} por unidad`
									: 'Sin precio publicado: completalo abajo.'}
							</p>
							{#if vistaPrevia.imagen}
								<label class="producto__usar">
									<input type="checkbox" bind:checked={usarImagen} />
									Usar esta imagen como portada
								</label>
							{/if}
						</div>
					</div>
				{/if}
			</div>
			{#if analisisEnlace && !analizando}
				<PanelEnlace analisis={analisisEnlace} />
			{/if}
		</fieldset>

		<fieldset class="seccion">
			<legend class="seccion__titulo">2. Producto</legend>
			<div class="grilla-campos">
				<Campo
					id="titulo"
					etiqueta="Título"
					requerido
					ayuda="Un nombre corto que resuma la compra."
					error={errors.titulo}
				>
					{#snippet children(props)}
						<input id="titulo" name="titulo" type="text" required {...props} />
					{/snippet}
				</Campo>
				<Campo id="nombre_producto" etiqueta="Producto" requerido error={errors.nombre_producto}>
					{#snippet children(props)}
						<input id="nombre_producto" name="nombre_producto" type="text" required {...props} />
					{/snippet}
				</Campo>
				<Campo
					id="precio_unitario"
					etiqueta="Precio por unidad"
					requerido
					ayuda="Precio al por mayor por unidad."
					error={errors.precio_unitario}
				>
					{#snippet children(props)}
						<input
							id="precio_unitario"
							name="precio_unitario"
							type="number"
							min="0"
							step="0.01"
							required
							{...props}
						/>
					{/snippet}
				</Campo>
			</div>
			<div class="categoria-variantes">
				<SelectorCategoria {categorias} bind:categoriaId bind:atributos errores={errors} />
			</div>
			<Campo
				id="precio_total"
				etiqueta="Precio total"
				ayuda="Se calcula solo: precio por unidad × cantidad total."
			>
				{#snippet children(props)}
					<output id="precio_total" class="calculado" for="precio_unitario cantidad_total" {...props}>
						{#if precioTotalTexto}
							{moneda(precioTotalTexto)}
						{:else}
							<span class="calculado__vacio">Completá el precio y la cantidad total</span>
						{/if}
					</output>
				{/snippet}
			</Campo>
			{#if errorCategorias}
				<div class="crear__aviso">
					<Aviso variante="aviso">
						No se pudieron cargar las categorías. Recargá la página para volver a intentar.
					</Aviso>
				</div>
			{/if}
		</fieldset>

		<fieldset class="seccion">
			<legend class="seccion__titulo">3. Cantidades y plazo</legend>
			<div class="grilla-campos">
				<Campo
					id="cantidad_total"
					etiqueta="Cantidad total"
					requerido
					ayuda="Unidades que hay que juntar para comprar."
					error={errors.cantidad_total}
				>
					{#snippet children(props)}
						<input id="cantidad_total" name="cantidad_total" type="number" min="1" required {...props} />
					{/snippet}
				</Campo>
				<Campo
					id="cantidad_creador"
					etiqueta="Cantidad del creador"
					ayuda="Cuántas unidades reservás vos."
					error={errors.cantidad_creador}
				>
					{#snippet children(props)}
						<input
							id="cantidad_creador"
							name="cantidad_creador"
							type="number"
							min="1"
							value="1"
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo
					id="min_por_integrante"
					etiqueta="Mínimo por integrante"
					ayuda="Mínimo que puede reservar cada persona."
					error={errors.min_por_integrante}
				>
					{#snippet children(props)}
						<input
							id="min_por_integrante"
							name="min_por_integrante"
							type="number"
							min="1"
							value="1"
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo
					id="fecha_caducidad"
					etiqueta="Caducidad"
					requerido
					ayuda="Hasta 30 días desde hoy."
					error={errors.fecha_caducidad}
				>
					{#snippet children(props)}
						<input id="fecha_caducidad" name="fecha_caducidad" type="date" required {...props} />
					{/snippet}
				</Campo>
			</div>
		</fieldset>

		<fieldset class="seccion">
			<legend class="seccion__titulo">4. Entrega y pago</legend>
			<div class="grilla-campos">
				<Campo id="direccion" etiqueta="Dirección" requerido error={errors.direccion}>
					{#snippet children(props)}
						<input id="direccion" name="direccion" type="text" required {...props} />
					{/snippet}
				</Campo>
				<Campo id="ciudad" etiqueta="Ciudad" requerido error={errors.ciudad}>
					{#snippet children(props)}
						<input id="ciudad" name="ciudad" type="text" required {...props} />
					{/snippet}
				</Campo>
				<Campo id="tipo_pago" etiqueta="Tipo de pago" error={errors.tipo_pago}>
					{#snippet children(props)}
						<select id="tipo_pago" name="tipo_pago" {...props}>
							{#each TIPOS_PAGO as [valor, texto] (valor)}
								<option value={valor}>{texto}</option>
							{/each}
						</select>
					{/snippet}
				</Campo>
			</div>
		</fieldset>

		<fieldset class="seccion">
			<legend class="seccion__titulo">5. Imágenes y descripción</legend>
			<Campo
				id="imagenes"
				etiqueta="Imágenes del pool"
				ayuda="Opcional, hasta 10 fotos (JPG, PNG, HEIC o WEBP)."
			>
				{#snippet children(props)}
					<div class="tiles">
						<input
							id="imagenes"
							class="archivo__input"
							name="imagenes"
							type="file"
							accept="image/*"
							multiple
							onchange={alElegirImagenes}
							{...props}
						/>
						<label class="tiles__agregar" for="imagenes">
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2.4"
								stroke-linecap="round"
								aria-hidden="true"
							>
								<path d="M12 5v14M5 12h14" />
							</svg>
							Agregar imágenes
						</label>
						{#if archivos.length}
							<p class="tiles__contador">
								{archivos.length} archivo{archivos.length === 1 ? '' : 's'}
							</p>
						{/if}
					</div>
				{/snippet}
			</Campo>
			<Campo
				id="descripcion"
				etiqueta="Descripción"
				ayuda="Contá detalles útiles: marca, medidas, punto de entrega."
				error={errors.descripcion}
			>
				{#snippet children(props)}
					<textarea id="descripcion" name="descripcion" rows="3" {...props}></textarea>
				{/snippet}
			</Campo>
		</fieldset>
	</form>

	<aside class="crear__lateral" aria-label="Vista previa del pool">
		<h2 class="crear__preview-titulo">Así se verá tu pool</h2>
		<!-- La card es una referencia visual del pool que todavía no existe: `inert`
		     la saca del foco y del árbol de accesibilidad (su enlace iría a /pools/0). -->
		<div class="preview" class:preview--sin-fecha={!datos.fecha_caducidad} class:preview--sin-cantidad={!cantidadTotal} inert aria-hidden="true">
			<PoolCard pool={preview} />
		</div>
		<div class="resumen">
			<p class="resumen__fila">
				<span>Participantes estimados</span>
				<b>{participantes ?? '—'}</b>
			</p>
			<p class="resumen__fila">
				<span>Total del pool</span>
				<b>{totalPool === null ? '—' : moneda(totalPool)}</b>
			</p>
		</div>
		{#if general}
			<Aviso variante="error">{general}</Aviso>
		{/if}
		<Boton tipo="submit" form="pool-form" variante="primario" tamano="lg" bloque disabled={enviando}>
			{#if enviando}<span class="spinner spinner--chico"></span> Creando…{:else}Crear pool{/if}
		</Boton>
		<Boton variante="secundario" bloque href={resolve('/pools')}>Cancelar</Boton>
	</aside>
</div>

<style>
	.crear {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		gap: var(--e-6);
	}

	.crear__form {
		flex: 999 1 560px;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}

	.crear__lateral {
		flex: 1 1 340px;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
	}

	.crear__preview-titulo {
		margin: 0;
		font-size: var(--texto-md);
		font-weight: 700;
	}

	.enlace {
		display: flex;
		gap: var(--e-2);
	}

	.enlace input {
		flex: 1;
		min-width: 0;
	}

	.enlace__estado {
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.producto {
		display: flex;
		align-items: center;
		gap: var(--e-3);
		padding: var(--e-3);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--crema);
	}

	.producto__imagen {
		flex: none;
		width: 72px;
		height: 72px;
		border-radius: var(--radio-sm);
		background: var(--superficie);
		object-fit: contain;
	}

	.producto__datos p {
		margin: 0;
	}

	.producto__nombre {
		font-weight: 700;
		color: var(--tinta);
	}

	.producto__usar {
		display: inline-flex;
		align-items: center;
		gap: var(--e-2);
		margin-top: var(--e-1);
		cursor: pointer;
	}

	.crear__aviso {
		margin-top: var(--e-3);
	}

	.seccion {
		margin: 0 0 var(--e-6);
		padding: 0;
		border: 0;
	}

	.seccion:last-of-type {
		margin-bottom: 0;
	}

	.seccion__titulo {
		padding: 0 0 var(--e-3);
		font-family: var(--fuente-display);
		font-size: var(--texto-lg);
		font-weight: 800;
		letter-spacing: -0.01em;
		color: var(--tinta);
	}

	/* Vista previa: la card real del listado, sin su CTA (el pool no existe aún). */
	.preview :global(.pool__accion) {
		display: none;
	}

	/* Sin fecha no hay fila de vencimiento (evita el "Vence en NaN días" del vacío). */
	.preview--sin-fecha :global(.pool__pie) {
		display: none;
	}

	/* Sin cantidad total no hay barra ni "X / Y": "0 / 0 Completo" sería un estado
	   imposible (el form exige cantidad_total ≥ 1). */
	.preview--sin-cantidad :global(progress.pool__barra),
	.preview--sin-cantidad :global(.pool__meta) {
		display: none;
	}

	.resumen {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		padding: var(--e-4);
		border-radius: var(--radio);
		background: var(--crema);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.resumen__fila {
		display: flex;
		justify-content: space-between;
		gap: var(--e-3);
		margin: 0;
	}

	.resumen__fila b {
		color: var(--tinta);
	}

	.tiles {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3);
	}

	.tiles__agregar {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--e-2);
		width: 104px;
		height: 104px;
		padding: var(--e-2);
		border: 2px dashed var(--linea-fuerte);
		border-radius: var(--radio);
		background: var(--crema);
		color: var(--tinta-suave);
		font-size: var(--texto-xs);
		font-weight: 600;
		text-align: center;
		cursor: pointer;
		transition: border-color var(--transicion), color var(--transicion);
	}

	.tiles__agregar:hover {
		border-color: var(--naranja-fuerte);
		color: var(--naranja-fuerte);
	}

	.tiles__agregar svg {
		width: 22px;
		height: 22px;
	}

	.tiles__contador {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	@media (max-width: 900px) {
		.crear {
			gap: var(--e-5);
		}
	}

	:global(.borrador) {
		justify-content: space-between;
		align-items: center;
	}

	.borrador__descartar {
		border: 0;
		background: none;
		padding: 0;
		font: inherit;
		font-weight: 600;
		color: inherit;
		text-decoration: underline;
		cursor: pointer;
	}

	.calculado {
		display: flex;
		align-items: center;
		min-height: 2.75rem;
		padding: 0 0.9rem;
		border: 1px dashed var(--linea-control);
		border-radius: var(--radio-sm);
		background: var(--crema);
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}

	.calculado__vacio {
		font-weight: 400;
		color: var(--tinta-tenue);
	}

	.categoria-variantes {
		display: grid;
		gap: var(--e-4);
		margin-bottom: var(--e-4);
	}
</style>
