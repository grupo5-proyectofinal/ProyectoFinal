<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, fieldErrors } from '$lib/api.js';
	import { puedeEditar } from '$lib/estados.js';
	import { session } from '$lib/session.svelte.js';

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
		<a class="btn btn--secundario" href={resolve('/pools')}>Volver a pools</a>
	</div>
{:else if !esCreador}
	<div class="vacio">
		<h3>Solo el creador puede editar este pool</h3>
		<p>Si necesitás cambios, pedile al creador que los haga.</p>
		<a class="btn btn--secundario" href={resolve(`/pools/${pool.id}`)}>Volver al detalle</a>
	</div>
{:else if !esEditable}
	<div class="vacio">
		<h3>Este pool ya no se puede editar</h3>
		<p>Solo se puede editar mientras el pool esté abierto.</p>
		<a class="btn btn--secundario" href={resolve(`/pools/${pool.id}`)}>Volver al detalle</a>
	</div>
{:else}
	<div class="cabecera-pagina">
		<div>
			<h1>Editar pool</h1>
			<p>{pool.titulo}</p>
		</div>
		<div class="cabecera-pagina__acciones">
			<a class="btn btn--ghost" href={resolve(`/pools/${pool.id}`)}>Volver al detalle</a>
		</div>
	</div>

	<section class="panel formulario">
		{#if hayOtrosIntegrantes}
			<div class="alerta alerta--info aviso" role="status">
				Ya hay integrantes en el pool: el título, el producto, el precio, la cantidad total y el
				domicilio no se pueden cambiar.
			</div>
		{/if}

		<form bind:this={form} onsubmit={enviar}>
			<fieldset class="bloque">
				<legend>Datos del pool</legend>
				<div class="grilla-campos">
					<div class="campo">
						<label for="titulo">Título</label>
						<input
							id="titulo"
							name="titulo"
							type="text"
							value={pool.titulo}
							aria-invalid={errors.titulo ? 'true' : undefined}
							aria-describedby={errors.titulo ? 'titulo-error' : undefined}
						/>
						{#if errors.titulo}<p class="error" id="titulo-error">{errors.titulo}</p>{/if}
					</div>
					<div class="campo">
						<label for="nombre_producto">Producto</label>
						<input
							id="nombre_producto"
							name="nombre_producto"
							type="text"
							value={pool.nombre_producto}
							aria-invalid={errors.nombre_producto ? 'true' : undefined}
							aria-describedby={errors.nombre_producto ? 'nombre_producto-error' : undefined}
						/>
						{#if errors.nombre_producto}
							<p class="error" id="nombre_producto-error">{errors.nombre_producto}</p>
						{/if}
					</div>
					<div class="campo">
						<label for="categoria">Categoría</label>
						<select id="categoria" value={pool.categoria}>
							{#each categorias as categoria (categoria.id)}
								<option value={categoria.id}>{categoria.nombre}</option>
							{/each}
						</select>
						{#if errors.categoria}<p class="error">{errors.categoria}</p>{/if}
					</div>
				</div>
				<div class="campo">
					<label for="descripcion">Descripción</label>
					<textarea
						id="descripcion"
						name="descripcion"
						rows="3"
						aria-invalid={errors.descripcion ? 'true' : undefined}
						aria-describedby={errors.descripcion ? 'descripcion-error' : undefined}
					>{pool.descripcion}</textarea>
					{#if errors.descripcion}
						<p class="error" id="descripcion-error">{errors.descripcion}</p>
					{/if}
				</div>
			</fieldset>

			<fieldset class="bloque">
				<legend>Precio y cantidades</legend>
				<div class="grilla-campos">
					<div class="campo">
						<label for="precio_unitario">Precio unitario</label>
						<input
							id="precio_unitario"
							name="precio_unitario"
							type="number"
							min="0"
							step="0.01"
							value={pool.precio_unitario}
							aria-invalid={errors.precio_unitario ? 'true' : undefined}
							aria-describedby={errors.precio_unitario ? 'precio_unitario-error' : undefined}
						/>
						{#if errors.precio_unitario}
							<p class="error" id="precio_unitario-error">{errors.precio_unitario}</p>
						{/if}
					</div>
					<div class="campo">
						<label for="cantidad_total">Cantidad total</label>
						<input
							id="cantidad_total"
							name="cantidad_total"
							type="number"
							min="1"
							value={pool.cantidad_total}
							aria-invalid={errors.cantidad_total ? 'true' : undefined}
							aria-describedby={errors.cantidad_total ? 'cantidad_total-error' : undefined}
						/>
						{#if errors.cantidad_total}
							<p class="error" id="cantidad_total-error">{errors.cantidad_total}</p>
						{/if}
					</div>
					<div class="campo">
						<label for="min_por_integrante">Mínimo por integrante</label>
						<input
							id="min_por_integrante"
							name="min_por_integrante"
							type="number"
							min="1"
							value={pool.min_por_integrante}
							aria-invalid={errors.min_por_integrante ? 'true' : undefined}
							aria-describedby={errors.min_por_integrante ? 'min_por_integrante-error' : undefined}
						/>
						{#if errors.min_por_integrante}
							<p class="error" id="min_por_integrante-error">{errors.min_por_integrante}</p>
						{/if}
					</div>
				</div>
			</fieldset>

			<fieldset class="bloque">
				<legend>Entrega</legend>
				<div class="grilla-campos">
					<div class="campo">
						<label for="fecha_caducidad">Caducidad</label>
						<input
							id="fecha_caducidad"
							name="fecha_caducidad"
							type="date"
							value={pool.fecha_caducidad}
							aria-invalid={errors.fecha_caducidad ? 'true' : undefined}
							aria-describedby={errors.fecha_caducidad ? 'fecha_caducidad-error' : undefined}
						/>
						{#if errors.fecha_caducidad}
							<p class="error" id="fecha_caducidad-error">{errors.fecha_caducidad}</p>
						{/if}
					</div>
					<div class="campo">
						<label for="tipo_pago">Tipo de pago</label>
						<select id="tipo_pago" value={pool.tipo_pago}>
							{#each TIPOS_PAGO as [valor, texto] (valor)}
								<option value={valor}>{texto}</option>
							{/each}
						</select>
						{#if errors.tipo_pago}<p class="error">{errors.tipo_pago}</p>{/if}
					</div>
					<div class="campo">
						<label for="direccion">Dirección</label>
						<input
							id="direccion"
							name="direccion"
							type="text"
							value={pool.direccion}
							aria-invalid={errors.direccion ? 'true' : undefined}
							aria-describedby={errors.direccion ? 'direccion-error' : undefined}
						/>
						{#if errors.direccion}<p class="error" id="direccion-error">{errors.direccion}</p>{/if}
					</div>
					<div class="campo">
						<label for="ciudad">Ciudad</label>
						<input
							id="ciudad"
							name="ciudad"
							type="text"
							value={pool.ciudad}
							aria-invalid={errors.ciudad ? 'true' : undefined}
							aria-describedby={errors.ciudad ? 'ciudad-error' : undefined}
						/>
						{#if errors.ciudad}<p class="error" id="ciudad-error">{errors.ciudad}</p>{/if}
					</div>
				</div>
			</fieldset>

			{#if exito}
				<div class="alerta alerta--exito aviso" role="status">{exito}</div>
			{/if}
			{#if general}
				<div class="alerta alerta--error aviso" role="alert">{general}</div>
			{/if}

			<div class="acciones">
				<button class="btn btn--primario" type="submit">Guardar cambios</button>
				<a class="btn btn--ghost" href={resolve(`/pools/${pool.id}`)}>Descartar</a>
			</div>
		</form>
	</section>

	<section class="panel formulario imagenes">
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
						<button
							class="btn btn--peligro-suave btn--sm"
							type="button"
							onclick={() => borrarImagen(imagen.id)}
						>
							Borrar
						</button>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="muted">Sin imágenes todavía.</p>
		{/if}
		<div class="campo">
			<label for="nuevas">Agregar imágenes</label>
			<div class="archivo">
				<input
					id="nuevas"
					class="archivo__input"
					type="file"
					accept="image/*"
					multiple
					onchange={subirImagenes}
					aria-describedby="nuevas-ayuda"
				/>
				<label class="archivo__boton btn btn--secundario" for="nuevas">Elegir imágenes</label>
				<span class="archivo__nombre" id="nuevas-ayuda">Hasta 10, JPEG o PNG</span>
			</div>
		</div>
	</section>
{/if}

<style>
	.imagenes {
		margin-top: var(--e-6);
	}

	.imagenes__titulo {
		font-size: var(--texto-lg);
		margin-bottom: var(--e-4);
	}

	.imagenes__lista {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
		gap: var(--e-3);
		margin: 0 0 var(--e-5);
		padding: 0;
		list-style: none;
	}

	.imagen {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
	}

	.imagen__img {
		width: 100%;
		aspect-ratio: 4 / 3;
		object-fit: cover;
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
	}

</style>
