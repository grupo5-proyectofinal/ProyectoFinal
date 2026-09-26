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

<section class="tarjeta">
	<h1>Crear pool</h1>
	<form bind:this={form} onsubmit={enviar}>
		<div class="grilla">
			<div class="campo">
				<label for="titulo">Título</label>
				<input id="titulo" name="titulo" type="text" required />
				{#if errors.titulo}<p class="error">{errors.titulo}</p>{/if}
			</div>
			<div class="campo">
				<label for="nombre_producto">Producto</label>
				<input id="nombre_producto" name="nombre_producto" type="text" required />
				{#if errors.nombre_producto}<p class="error">{errors.nombre_producto}</p>{/if}
			</div>
			<div class="campo">
				<label for="categoria">Categoría</label>
				<select id="categoria" name="categoria" required>
					<option value="">Elegí una</option>
					{#each categorias as categoria (categoria.id)}
						<option value={categoria.id}>{categoria.nombre}</option>
					{/each}
				</select>
				{#if errors.categoria}<p class="error">{errors.categoria}</p>{/if}
			</div>
			<div class="campo">
				<label for="enlace">Enlace (opcional)</label>
				<input id="enlace" name="enlace" type="url" />
				{#if errors.enlace}<p class="error">{errors.enlace}</p>{/if}
			</div>
			<div class="campo">
				<label for="precio_unitario">Precio unitario</label>
				<input id="precio_unitario" name="precio_unitario" type="number" min="0" step="0.01" required />
				{#if errors.precio_unitario}<p class="error">{errors.precio_unitario}</p>{/if}
			</div>
			<div class="campo">
				<label for="cantidad_total">Cantidad total</label>
				<input id="cantidad_total" name="cantidad_total" type="number" min="1" required />
				{#if errors.cantidad_total}<p class="error">{errors.cantidad_total}</p>{/if}
			</div>
			<div class="campo">
				<label for="cantidad_creador">Cantidad del creador</label>
				<input id="cantidad_creador" name="cantidad_creador" type="number" min="1" value="1" />
				{#if errors.cantidad_creador}<p class="error">{errors.cantidad_creador}</p>{/if}
			</div>
			<div class="campo">
				<label for="min_por_integrante">Mínimo por integrante</label>
				<input id="min_por_integrante" name="min_por_integrante" type="number" min="1" value="1" />
				{#if errors.min_por_integrante}<p class="error">{errors.min_por_integrante}</p>{/if}
			</div>
			<div class="campo">
				<label for="fecha_caducidad">Caducidad</label>
				<input id="fecha_caducidad" name="fecha_caducidad" type="date" required />
				{#if errors.fecha_caducidad}<p class="error">{errors.fecha_caducidad}</p>{/if}
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
				<label for="direccion">Dirección</label>
				<input id="direccion" name="direccion" type="text" required />
				{#if errors.direccion}<p class="error">{errors.direccion}</p>{/if}
			</div>
			<div class="campo">
				<label for="ciudad">Ciudad</label>
				<input id="ciudad" name="ciudad" type="text" required />
				{#if errors.ciudad}<p class="error">{errors.ciudad}</p>{/if}
			</div>
		</div>
		<div class="campo">
			<label for="descripcion">Descripción</label>
			<textarea id="descripcion" name="descripcion" rows="3"></textarea>
			{#if errors.descripcion}<p class="error">{errors.descripcion}</p>{/if}
		</div>
		<div class="campo">
			<label for="imagenes">Imágenes (opcional, hasta 10)</label>
			<input id="imagenes" name="imagenes" type="file" accept="image/*" multiple bind:files={archivos} />
		</div>
		{#if general}<p class="error">{general}</p>{/if}
		<button class="btn" type="submit" disabled={enviando}>Crear pool</button>
	</form>
</section>
