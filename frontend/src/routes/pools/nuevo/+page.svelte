<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api, fieldErrors } from '$lib/api.js';

	let categorias = $state([]);
	let archivos = $state([]);
	let errors = $state({});
	let general = $state('');
	let enviando = $state(false);
	let form = $state();

	const TIPOS_PAGO = [
		['efectivo', 'Efectivo'],
		['transferencia', 'Transferencia'],
		['sin_especificar', 'Sin especificar']
	];

	$effect(() => {
		api('/categories/')
			.then((r) => (categorias = r.results))
			.catch(() => {});
	});

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

<section class="panel formulario">
	<form bind:this={form} onsubmit={enviar}>
		<fieldset class="bloque">
			<legend>Producto</legend>
			<div class="grilla-campos">
				<div class="campo">
					<label for="titulo">Título <span aria-hidden="true">*</span></label>
					<input
						id="titulo"
						name="titulo"
						type="text"
						required
						aria-invalid={errors.titulo ? 'true' : undefined}
						aria-describedby={errors.titulo ? 'titulo-error' : 'titulo-ayuda'}
					/>
					{#if errors.titulo}
						<p class="error" id="titulo-error">{errors.titulo}</p>
					{:else}
						<p class="ayuda" id="titulo-ayuda">Un nombre corto que resuma la compra.</p>
					{/if}
				</div>
				<div class="campo">
					<label for="nombre_producto">Producto <span aria-hidden="true">*</span></label>
					<input
						id="nombre_producto"
						name="nombre_producto"
						type="text"
						required
						aria-invalid={errors.nombre_producto ? 'true' : undefined}
						aria-describedby={errors.nombre_producto ? 'nombre_producto-error' : undefined}
					/>
					{#if errors.nombre_producto}
						<p class="error" id="nombre_producto-error">{errors.nombre_producto}</p>
					{/if}
				</div>
				<div class="campo">
					<label for="categoria">Categoría <span aria-hidden="true">*</span></label>
					<select id="categoria" name="categoria" required>
						<option value="">Elegí una</option>
						{#each categorias as categoria (categoria.id)}
							<option value={categoria.id}>{categoria.nombre}</option>
						{/each}
					</select>
					{#if errors.categoria}<p class="error">{errors.categoria}</p>{/if}
				</div>
				<div class="campo">
					<label for="enlace">Enlace del producto</label>
					<input
						id="enlace"
						name="enlace"
						type="url"
						placeholder="https://…"
						aria-invalid={errors.enlace ? 'true' : undefined}
						aria-describedby={errors.enlace ? 'enlace-error' : 'enlace-ayuda'}
					/>
					{#if errors.enlace}
						<p class="error" id="enlace-error">{errors.enlace}</p>
					{:else}
						<p class="ayuda" id="enlace-ayuda">Opcional. Sirve para que vean el producto.</p>
					{/if}
				</div>
			</div>
			<div class="campo">
				<label for="descripcion">Descripción</label>
				<textarea
					id="descripcion"
					name="descripcion"
					rows="3"
					aria-describedby={errors.descripcion ? 'descripcion-error' : 'descripcion-ayuda'}
				></textarea>
				{#if errors.descripcion}
					<p class="error" id="descripcion-error">{errors.descripcion}</p>
				{:else}
					<p class="ayuda" id="descripcion-ayuda">
						Contá detalles útiles: marca, medidas, punto de entrega.
					</p>
				{/if}
			</div>
		</fieldset>

		<fieldset class="bloque">
			<legend>Precio y cantidades</legend>
			<div class="grilla-campos">
				<div class="campo">
					<label for="precio_unitario">Precio unitario <span aria-hidden="true">*</span></label>
					<input
						id="precio_unitario"
						name="precio_unitario"
						type="number"
						min="0"
						step="0.01"
						required
						aria-invalid={errors.precio_unitario ? 'true' : undefined}
						aria-describedby={errors.precio_unitario ? 'precio_unitario-error' : 'precio_unitario-ayuda'}
					/>
					{#if errors.precio_unitario}
						<p class="error" id="precio_unitario-error">{errors.precio_unitario}</p>
					{:else}
						<p class="ayuda" id="precio_unitario-ayuda">Precio al por mayor por unidad.</p>
					{/if}
				</div>
				<div class="campo">
					<label for="cantidad_total">Cantidad total <span aria-hidden="true">*</span></label>
					<input
						id="cantidad_total"
						name="cantidad_total"
						type="number"
						min="1"
						required
						aria-invalid={errors.cantidad_total ? 'true' : undefined}
						aria-describedby={errors.cantidad_total ? 'cantidad_total-error' : 'cantidad_total-ayuda'}
					/>
					{#if errors.cantidad_total}
						<p class="error" id="cantidad_total-error">{errors.cantidad_total}</p>
					{:else}
						<p class="ayuda" id="cantidad_total-ayuda">Unidades que hay que juntar para comprar.</p>
					{/if}
				</div>
				<div class="campo">
					<label for="cantidad_creador">Cantidad del creador</label>
					<input
						id="cantidad_creador"
						name="cantidad_creador"
						type="number"
						min="1"
						value="1"
						aria-describedby={errors.cantidad_creador ? 'cantidad_creador-error' : 'cantidad_creador-ayuda'}
					/>
					{#if errors.cantidad_creador}
						<p class="error" id="cantidad_creador-error">{errors.cantidad_creador}</p>
					{:else}
						<p class="ayuda" id="cantidad_creador-ayuda">Cuántas unidades reservás vos.</p>
					{/if}
				</div>
				<div class="campo">
					<label for="min_por_integrante">Mínimo por integrante</label>
					<input
						id="min_por_integrante"
						name="min_por_integrante"
						type="number"
						min="1"
						value="1"
						aria-invalid={errors.min_por_integrante ? 'true' : undefined}
						aria-describedby={errors.min_por_integrante ? 'min_por_integrante-error' : 'min_por_integrante-ayuda'}
					/>
					{#if errors.min_por_integrante}
						<p class="error" id="min_por_integrante-error">{errors.min_por_integrante}</p>
					{:else}
						<p class="ayuda" id="min_por_integrante-ayuda">
							Mínimo que puede reservar cada persona.
						</p>
					{/if}
				</div>
			</div>
		</fieldset>

		<fieldset class="bloque">
			<legend>Entrega</legend>
			<div class="grilla-campos">
				<div class="campo">
					<label for="fecha_caducidad">Caducidad <span aria-hidden="true">*</span></label>
					<input
						id="fecha_caducidad"
						name="fecha_caducidad"
						type="date"
						required
						aria-invalid={errors.fecha_caducidad ? 'true' : undefined}
						aria-describedby={errors.fecha_caducidad ? 'fecha_caducidad-error' : 'fecha_caducidad-ayuda'}
					/>
					{#if errors.fecha_caducidad}
						<p class="error" id="fecha_caducidad-error">{errors.fecha_caducidad}</p>
					{:else}
						<p class="ayuda" id="fecha_caducidad-ayuda">Hasta 30 días desde hoy.</p>
					{/if}
				</div>
				<div class="campo">
					<label for="tipo_pago">Tipo de pago</label>
					<select id="tipo_pago" name="tipo_pago">
						{#each TIPOS_PAGO as [valor, texto] (valor)}
							<option value={valor}>{texto}</option>
						{/each}
					</select>
					{#if errors.tipo_pago}<p class="error">{errors.tipo_pago}</p>{/if}
				</div>
				<div class="campo">
					<label for="direccion">Dirección <span aria-hidden="true">*</span></label>
					<input
						id="direccion"
						name="direccion"
						type="text"
						required
						aria-invalid={errors.direccion ? 'true' : undefined}
						aria-describedby={errors.direccion ? 'direccion-error' : undefined}
					/>
					{#if errors.direccion}<p class="error" id="direccion-error">{errors.direccion}</p>{/if}
				</div>
				<div class="campo">
					<label for="ciudad">Ciudad <span aria-hidden="true">*</span></label>
					<input
						id="ciudad"
						name="ciudad"
						type="text"
						required
						aria-invalid={errors.ciudad ? 'true' : undefined}
						aria-describedby={errors.ciudad ? 'ciudad-error' : undefined}
					/>
					{#if errors.ciudad}<p class="error" id="ciudad-error">{errors.ciudad}</p>{/if}
				</div>
			</div>
		</fieldset>

		<fieldset class="bloque">
			<legend>Imágenes</legend>
			<div class="campo">
				<label for="imagenes">Imágenes del pool</label>
				<input
					id="imagenes"
					name="imagenes"
					type="file"
					accept="image/*"
					multiple
					bind:files={archivos}
					aria-describedby="imagenes-ayuda"
				/>
				<p class="ayuda" id="imagenes-ayuda">
					Opcional, hasta 10 archivos JPEG o PNG.
					{#if archivos.length}Seleccionadas: {archivos.length}.{/if}
				</p>
			</div>
		</fieldset>

		{#if general}
			<div class="alerta alerta--error aviso" role="alert">{general}</div>
		{/if}

		<div class="acciones">
			<button class="btn btn--primario" type="submit" disabled={enviando}>
				{#if enviando}<span class="spinner spinner--chico"></span> Creando…{:else}Crear pool{/if}
			</button>
			<a class="btn btn--ghost" href={resolve('/pools')}>Cancelar</a>
		</div>
	</form>
</section>

<style>
	.formulario {
		max-width: 52rem;
		padding: clamp(1.25rem, 2.5vw, 2rem);
	}

	.bloque {
		margin: 0 0 var(--e-6);
		padding: var(--e-5) 0 0;
		border: 0;
		border-top: 1px solid var(--linea);
	}

	.bloque:first-of-type {
		padding-top: 0;
		border-top: 0;
	}

	.bloque legend {
		padding: 0 var(--e-3) 0 0;
		font-family: var(--fuente-display);
		font-size: var(--texto-md);
		font-weight: 600;
		color: var(--tinta);
	}

	.grilla-campos {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0 var(--e-4);
		margin-top: var(--e-4);
	}

	.grilla-campos .campo {
		margin-bottom: var(--e-3);
	}

	.aviso {
		margin-bottom: var(--e-4);
	}

	.acciones {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3);
		margin-top: var(--e-5);
		padding-top: var(--e-5);
		border-top: 1px solid var(--linea);
	}

	.spinner--chico {
		width: 0.95rem;
		height: 0.95rem;
		border-color: rgba(255, 255, 255, 0.35);
		border-top-color: #fff;
	}

	@media (max-width: 560px) {
		.grilla-campos {
			grid-template-columns: 1fr;
		}
	}
</style>
