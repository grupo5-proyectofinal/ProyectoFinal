<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, fieldErrors } from '$lib/api.js';
	import { etiquetaEstado, puedeEditar } from '$lib/estados.js';
	import { moneda } from '$lib/formato.js';
	import { session } from '$lib/session.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let pool = $state(null);
	let categorias = $state([]);
	let cargando = $state(true);
	let error = $state('');
	let errors = $state({});
	let general = $state('');
	let exito = $state('');
	let form = $state();

	const TIPOS_PAGO = [
		['efectivo', 'Efectivo'],
		['transferencia', 'Transferencia'],
		['sin_especificar', 'Sin especificar']
	];

	$effect(() => {
		cargar(page.params.id);
	});

	async function cargar(id) {
		cargando = true;
		try {
			pool = await api(`/pools/${id}/`);
			categorias = (await api('/categories/')).results;
		} catch (e) {
			error = e.status === 404 ? 'El pool no existe.' : 'No se pudo cargar el pool.';
		} finally {
			cargando = false;
		}
	}

	const esCreador = $derived(session.user?.id === pool?.creador?.id);
	const esEditable = $derived(puedeEditar(pool, session.user?.id));
	const hayOtrosIntegrantes = $derived(
		pool?.miembros?.some((m) => m.usuario.id !== pool.creador.id) ?? false
	);
	const portada = $derived(pool?.imagenes?.[0]?.imagen ?? null);
	const comprometido = $derived(pool ? pool.cantidad_total - pool.disponible : 0);

	async function enviar(event) {
		event.preventDefault();
		errors = {};
		general = '';
		exito = '';
		try {
			pool = await api(`/pools/${pool.id}/`, {
				method: 'PATCH',
				body: {
					titulo: form.titulo.value,
					nombre_producto: form.nombre_producto.value,
					precio_unitario: form.precio_unitario.value,
					cantidad_total: Number(form.cantidad_total.value),
					direccion: form.direccion.value,
					ciudad: form.ciudad.value,
					categoria: Number(form.categoria.value),
					descripcion: form.descripcion.value,
					fecha_caducidad: form.fecha_caducidad.value,
					min_por_integrante: Number(form.min_por_integrante.value),
					tipo_pago: form.tipo_pago.value
				}
			});
			exito = 'Cambios guardados.';
		} catch (e) {
			if (e.status === 403) {
				general = 'Solo el creador puede editar este pool.';
			} else {
				errors = fieldErrors(e.data);
				if (!Object.keys(errors).length) general = 'No se pudo guardar.';
			}
		}
	}

	async function subirImagenes(event) {
		const lista = event.target.files;
		if (!lista?.length) return;
		general = '';
		let fallidas = 0;
		for (const archivo of lista) {
			const fd = new FormData();
			fd.append('imagen', archivo);
			try {
				await api(`/pools/${pool.id}/imagenes/`, { method: 'POST', body: fd, form: true });
			} catch {
				fallidas += 1;
			}
		}
		event.target.value = '';
		await cargar(pool.id);
		if (fallidas) general = 'Algunas imágenes no se pudieron subir.';
	}

	async function borrarImagen(id) {
		if (!confirm('¿Borrar esta imagen?')) return;
		general = '';
		try {
			await api(`/pools/${pool.id}/imagenes/${id}/`, { method: 'DELETE' });
			await cargar(pool.id);
		} catch (e) {
			general = fieldErrors(e.data).detail ?? 'No se pudo borrar la imagen.';
		}
	}
</script>

<svelte:head>
	<title>Editar pool — PoolShop</title>
</svelte:head>

{#if cargando}
	<div class="cargando" role="status"><span class="spinner spinner--grande"></span> Cargando el pool…</div>
{:else if error}
	<div class="vacio">
		<h3>{error}</h3>
		<Boton variante="secundario" href={resolve('/pools')}>Volver a pools</Boton>
	</div>
{:else if !esCreador}
	<div class="vacio">
		<h3>Solo el creador puede editar este pool</h3>
		<p>Si necesitás cambios, pedile al creador que los haga.</p>
		<Boton variante="secundario" href={resolve(`/pools/${pool.id}`)}>Volver al detalle</Boton>
	</div>
{:else if !esEditable}
	<div class="vacio">
		<h3>Este pool ya no se puede editar</h3>
		<p>Solo se puede editar mientras el pool esté abierto.</p>
		<Boton variante="secundario" href={resolve(`/pools/${pool.id}`)}>Volver al detalle</Boton>
	</div>
{:else}
	<header class="cabecera-pool">
		<div class="cabecera-pool__media">
			{#if portada}
				<img src={portada} alt={pool.titulo} width="84" height="84" />
			{:else}
				<svg
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.4"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<path d="M3 8l9-5 9 5v8l-9 5-9-5z" />
					<path d="M3 8l9 5 9-5M12 13v8" />
				</svg>
			{/if}
		</div>
		<div class="cabecera-pool__datos">
			<div class="cabecera-pool__rol">
				<span>Sos el administrador</span>
				<Badge variante={pool.estado}>{etiquetaEstado(pool.estado)}</Badge>
			</div>
			<h1>{pool.titulo}</h1>
			<p class="cabecera-pool__meta">
				{comprometido} / {pool.cantidad_total} unidades ·
				{moneda(pool.precio_unitario)} c/u ·
				{pool.integrantes}
				{pool.integrantes === 1 ? 'participante' : 'participantes'} · {pool.ciudad}
			</p>
		</div>
		<div class="cabecera-pool__acciones">
			<Boton variante="secundario" href={resolve(`/pools/${pool.id}`)}>Volver al detalle</Boton>
		</div>
	</header>

	{#if hayOtrosIntegrantes}
		<div class="editar__aviso">
			<Aviso variante="info">
				Ya hay integrantes en el pool: el título, el producto, el precio, la cantidad total y el
				domicilio no se pueden cambiar.
			</Aviso>
		</div>
	{/if}

	<form bind:this={form} onsubmit={enviar}>
		<fieldset class="seccion">
			<legend class="seccion__titulo">1. Producto</legend>
			<div class="grilla-campos">
				<Campo id="titulo" etiqueta="Título" error={errors.titulo}>
					{#snippet children(props)}
						<input id="titulo" name="titulo" type="text" value={pool.titulo} {...props} />
					{/snippet}
				</Campo>
				<Campo id="nombre_producto" etiqueta="Producto" error={errors.nombre_producto}>
					{#snippet children(props)}
						<input
							id="nombre_producto"
							name="nombre_producto"
							type="text"
							value={pool.nombre_producto}
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo id="categoria" etiqueta="Categoría" error={errors.categoria}>
					{#snippet children(props)}
						<select id="categoria" value={pool.categoria} {...props}>
							{#each categorias as categoria (categoria.id)}
								<option value={categoria.id}>{categoria.nombre}</option>
							{/each}
						</select>
					{/snippet}
				</Campo>
			</div>
			<Campo id="descripcion" etiqueta="Descripción" error={errors.descripcion}>
				{#snippet children(props)}
					<textarea id="descripcion" name="descripcion" rows="3" {...props}>{pool.descripcion}</textarea>
				{/snippet}
			</Campo>
		</fieldset>

		<fieldset class="seccion">
			<legend class="seccion__titulo">2. Precio y cantidades</legend>
			<div class="grilla-campos">
				<Campo id="precio_unitario" etiqueta="Precio unitario" error={errors.precio_unitario}>
					{#snippet children(props)}
						<input
							id="precio_unitario"
							name="precio_unitario"
							type="number"
							min="0"
							step="0.01"
							value={pool.precio_unitario}
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo id="cantidad_total" etiqueta="Cantidad total" error={errors.cantidad_total}>
					{#snippet children(props)}
						<input
							id="cantidad_total"
							name="cantidad_total"
							type="number"
							min="1"
							value={pool.cantidad_total}
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo
					id="min_por_integrante"
					etiqueta="Mínimo por integrante"
					error={errors.min_por_integrante}
				>
					{#snippet children(props)}
						<input
							id="min_por_integrante"
							name="min_por_integrante"
							type="number"
							min="1"
							value={pool.min_por_integrante}
							{...props}
						/>
					{/snippet}
				</Campo>
			</div>
		</fieldset>

		<fieldset class="seccion">
			<legend class="seccion__titulo">3. Entrega y pago</legend>
			<div class="grilla-campos">
				<Campo id="fecha_caducidad" etiqueta="Caducidad" error={errors.fecha_caducidad}>
					{#snippet children(props)}
						<input
							id="fecha_caducidad"
							name="fecha_caducidad"
							type="date"
							value={pool.fecha_caducidad}
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo id="tipo_pago" etiqueta="Tipo de pago" error={errors.tipo_pago}>
					{#snippet children(props)}
						<select id="tipo_pago" value={pool.tipo_pago} {...props}>
							{#each TIPOS_PAGO as [valor, texto] (valor)}
								<option value={valor}>{texto}</option>
							{/each}
						</select>
					{/snippet}
				</Campo>
				<Campo id="direccion" etiqueta="Dirección" error={errors.direccion}>
					{#snippet children(props)}
						<input id="direccion" name="direccion" type="text" value={pool.direccion} {...props} />
					{/snippet}
				</Campo>
				<Campo id="ciudad" etiqueta="Ciudad" error={errors.ciudad}>
					{#snippet children(props)}
						<input id="ciudad" name="ciudad" type="text" value={pool.ciudad} {...props} />
					{/snippet}
				</Campo>
			</div>
		</fieldset>

		{#if exito}
			<div class="editar__aviso">
				<Aviso variante="exito">{exito}</Aviso>
			</div>
		{/if}
		{#if general}
			<div class="editar__aviso">
				<Aviso variante="error">{general}</Aviso>
			</div>
		{/if}

		<div class="acciones">
			<Boton tipo="submit" variante="primario">Guardar cambios</Boton>
			<Boton variante="ghost" href={resolve(`/pools/${pool.id}`)}>Descartar</Boton>
		</div>
	</form>

	<div class="imagenes-panel">
		<Tarjeta>
			<div class="imagenes">
				<h2 class="imagenes__titulo">Imágenes</h2>
				{#if pool.imagenes.length}
					<ul class="imagenes__lista">
						{#each pool.imagenes as imagen (imagen.id)}
							<li class="imagen">
								<img
									class="imagen__img"
									src={imagen.imagen}
									alt={pool.titulo}
									width="160"
									height="120"
									loading="lazy"
								/>
								<Boton variante="peligro-suave" tamano="sm" onclick={() => borrarImagen(imagen.id)}>
									Borrar
								</Boton>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="imagenes__vacio">Sin imágenes todavía.</p>
				{/if}
				<div class="imagenes__agregar">
					<input
						id="nuevas"
						class="archivo__input"
						type="file"
						accept="image/*"
						multiple
						onchange={subirImagenes}
						aria-describedby="nuevas-ayuda"
					/>
					<label class="imagenes__tile" for="nuevas">
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
					<span class="imagenes__ayuda" id="nuevas-ayuda">Hasta 10, JPEG o PNG</span>
				</div>
			</div>
		</Tarjeta>
	</div>
{/if}

<style>
	.cabecera-pool {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-4);
		margin-bottom: var(--e-6);
	}

	.cabecera-pool__media {
		display: grid;
		place-items: center;
		flex: none;
		width: 84px;
		height: 84px;
		border-radius: var(--radio);
		background: var(--melocoton-fuerte);
		overflow: hidden;
	}

	.cabecera-pool__media img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.cabecera-pool__media svg {
		width: 40px;
		height: 40px;
		color: var(--naranja-fuerte);
	}

	.cabecera-pool__datos {
		flex: 1 1 20rem;
		min-width: 0;
	}

	.cabecera-pool__rol {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2);
		font-size: var(--texto-xs);
		font-weight: 700;
		color: var(--naranja-fuerte);
	}

	.cabecera-pool__datos h1 {
		margin: var(--e-1) 0;
		font-size: var(--texto-xl);
		letter-spacing: -0.02em;
		overflow-wrap: anywhere;
	}

	.cabecera-pool__meta {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.cabecera-pool__acciones {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-3);
	}

	.editar__aviso {
		margin-bottom: var(--e-4);
	}

	.imagenes-panel {
		margin-top: var(--e-6);
	}

	.seccion {
		margin: 0 0 var(--e-6);
		padding: 0;
		border: 0;
	}

	.seccion__titulo {
		padding: 0 0 var(--e-3);
		font-family: var(--fuente-display);
		font-size: var(--texto-lg);
		font-weight: 800;
		letter-spacing: -0.01em;
		color: var(--tinta);
	}

	.imagenes {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
		padding: clamp(1.25rem, 2.5vw, 2rem);
	}

	.imagenes__titulo {
		margin: 0;
		font-family: var(--fuente-display);
		font-size: var(--texto-lg);
		font-weight: 800;
		letter-spacing: -0.01em;
	}

	.imagenes__lista {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
		gap: var(--e-3);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.imagen {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--e-2);
	}

	.imagen__img {
		width: 100%;
		aspect-ratio: 4 / 3;
		object-fit: cover;
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
	}

	.imagenes__vacio {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.imagenes__agregar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3);
	}

	.imagenes__tile {
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

	.imagenes__tile:hover {
		border-color: var(--naranja-fuerte);
		color: var(--naranja-fuerte);
	}

	.imagenes__tile svg {
		width: 22px;
		height: 22px;
	}

	.imagenes__ayuda {
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
	}
</style>
