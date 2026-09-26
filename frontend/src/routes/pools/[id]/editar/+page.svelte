<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, fieldErrors } from '$lib/api.js';
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

	const esCreador = $derived(session.user?.id === pool?.creador);

	async function enviar(event) {
		event.preventDefault();
		errors = {};
		general = '';
		exito = '';
		try {
			pool = await api(`/pools/${pool.id}/`, {
				method: 'PATCH',
				body: {
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

{#if cargando}
	<p class="muted">Cargando…</p>
{:else if error}
	<p class="error">{error}</p>
	<a class="btn secundario" href={resolve('/pools')}>Volver</a>
{:else if !esCreador}
	<p class="error">Solo el creador puede editar este pool.</p>
	<a class="btn secundario" href={resolve(`/pools/${pool.id}`)}>Volver al detalle</a>
{:else}
	<section class="tarjeta">
		<h1>Editar pool</h1>
		<form bind:this={form} onsubmit={enviar}>
			<div class="grilla">
				<div class="campo">
					<label for="categoria">Categoría</label>
					<select id="categoria" value={pool.categoria}>
						{#each categorias as categoria (categoria.id)}
							<option value={categoria.id}>{categoria.nombre}</option>
						{/each}
					</select>
					{#if errors.categoria}<p class="error">{errors.categoria}</p>{/if}
				</div>
				<div class="campo">
					<label for="fecha_caducidad">Caducidad</label>
					<input id="fecha_caducidad" name="fecha_caducidad" type="date" value={pool.fecha_caducidad} />
					{#if errors.fecha_caducidad}<p class="error">{errors.fecha_caducidad}</p>{/if}
				</div>
				<div class="campo">
					<label for="min_por_integrante">Mínimo por integrante</label>
					<input
						id="min_por_integrante"
						name="min_por_integrante"
						type="number"
						min="1"
						value={pool.min_por_integrante}
					/>
					{#if errors.min_por_integrante}<p class="error">{errors.min_por_integrante}</p>{/if}
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
			</div>
			<div class="campo">
				<label for="descripcion">Descripción</label>
				<textarea id="descripcion" name="descripcion" rows="3" value={pool.descripcion}></textarea>
				{#if errors.descripcion}<p class="error">{errors.descripcion}</p>{/if}
			</div>
			{#if exito}<p class="exito">{exito}</p>{/if}
			{#if general}<p class="error">{general}</p>{/if}
			<button class="btn" type="submit">Guardar cambios</button>
		</form>

		<h2>Imágenes</h2>
		{#if pool.imagenes.length}
			<div class="galeria">
				{#each pool.imagenes as imagen (imagen.id)}
					<div>
						<img src={imagen.imagen} alt={pool.titulo} />
						<button class="btn peligro" type="button" onclick={() => borrarImagen(imagen.id)}>
							Borrar
						</button>
					</div>
				{/each}
			</div>
		{:else}
			<p class="muted">Sin imágenes.</p>
		{/if}
		<div class="campo">
			<label for="nuevas">Agregar imágenes</label>
			<input id="nuevas" type="file" accept="image/*" multiple onchange={subirImagenes} />
		</div>

		<a class="btn secundario" href={resolve(`/pools/${pool.id}`)}>Volver al detalle</a>
	</section>
{/if}
