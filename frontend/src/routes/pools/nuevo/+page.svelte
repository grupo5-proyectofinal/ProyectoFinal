<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { api, fieldErrors } from '$lib/api.js';
	import { moneda } from '$lib/formato.js';
	import { session } from '$lib/session.svelte.js';
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

	const TIPOS_PAGO = [
		['efectivo', 'Efectivo'],
		['transferencia', 'Transferencia'],
		['sin_especificar', 'Sin especificar']
	];

	$effect(() => {
		api('/categories/')
			.then((r) => {
				categorias = r.results;
				errorCategorias = false;
			})
			.catch(() => {
				errorCategorias = true;
			});
	});

	// El `input` burbujea: un solo handler mantiene la vista previa sincronizada.
	function alInput() {
		if (form) datos = Object.fromEntries(new FormData(form));
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
			const creado = await api('/pools/', { method: 'POST', body: fd, form: true });
			let fallidas = 0;
			for (const archivo of archivos) {
				const imgFd = new FormData();
				imgFd.append('imagen', archivo);
				try {
					await api(`/pools/${creado.id}/imagenes/`, { method: 'POST', body: imgFd, form: true });
				} catch {
					fallidas += 1;
				}
			}
			goto(resolve(fallidas ? `/pools/${creado.id}?aviso=imagenes` : `/pools/${creado.id}`));
		} catch (e) {
			errors = fieldErrors(e.data);
			if (!Object.keys(errors).length) general = 'No se pudo crear el pool.';
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
	const totalPool = $derived(cantidadTotal && datos.precio_unitario ? cantidadTotal * Number(datos.precio_unitario) : null);
	const participantes = $derived(
		cantidadTotal && minPorIntegrante
			? Math.ceil(Math.max(cantidadTotal - cantidadCreador, 0) / minPorIntegrante)
			: null
	);

	// Objeto con defaults seguros para reusar `PoolCard` sin tocar el form.
	const preview = $derived({
		id: 0,
		estado: 'abierto',
		imagenes: [],
		titulo: datos.titulo?.trim() || 'Tu pool',
		nombre_producto: datos.nombre_producto?.trim() || '',
		categoria_nombre: categorias.find((c) => String(c.id) === String(datos.categoria))?.nombre ?? '',
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
		<fieldset class="seccion">
			<legend class="seccion__titulo">1. Enlace de la oferta</legend>
			<Campo
				id="enlace"
				etiqueta="Enlace del producto"
				ayuda="Opcional. Sirve para que vean el producto."
				error={errors.enlace}
			>
				{#snippet children(props)}
					<input id="enlace" name="enlace" type="url" placeholder="https://…" {...props} />
				{/snippet}
			</Campo>
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
				<Campo id="categoria" etiqueta="Categoría" requerido error={errors.categoria}>
					{#snippet children(props)}
						<select id="categoria" name="categoria" required {...props}>
							<option value="">Elegí una</option>
							{#each categorias as categoria (categoria.id)}
								<option value={categoria.id}>{categoria.nombre}</option>
							{/each}
						</select>
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
				ayuda="Opcional, hasta 10 archivos JPEG o PNG."
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
</style>
