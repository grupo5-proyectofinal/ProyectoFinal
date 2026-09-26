<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { fieldErrors } from '$lib/api.js';
	import { session, updateMe } from '$lib/session.svelte.js';

	let errors = $state({});
	let exito = $state('');
	let guardando = $state(false);
	let form = $state();

	const generos = ['Femenino', 'Masculino', 'Otro', 'Prefiero no decir'];

	$effect(() => {
		if (!session.access) goto(resolve('/login'));
	});

	async function enviar(event) {
		event.preventDefault();
		errors = {};
		exito = '';
		guardando = true;
		try {
			const data = new FormData(form);
			if (!data.get('foto')?.name) data.delete('foto');
			await updateMe(data, true);
			exito = 'Datos actualizados.';
		} catch (error) {
			errors = fieldErrors(error.data);
			if (!Object.keys(errors).length) errors = { detalle: 'No se pudo actualizar el perfil.' };
		} finally {
			guardando = false;
		}
	}
</script>

<section class="tarjeta">
	<h1>Mi perfil</h1>
	{#if session.user}
		{#if session.user.foto}
			<img class="foto" src={session.user.foto} alt="Foto de perfil" />
		{/if}
		<p class="muted">
			{session.user.email} · usuario: {session.user.username} · DNI: {session.user.dni}
		</p>
		<form bind:this={form} onsubmit={enviar}>
			<div class="grilla">
				<div class="campo">
					<label for="first_name">Nombre</label>
					<input id="first_name" name="first_name" type="text" value={session.user.first_name} />
					{#if errors.first_name}<p class="error">{errors.first_name}</p>{/if}
				</div>
				<div class="campo">
					<label for="last_name">Apellido</label>
					<input id="last_name" name="last_name" type="text" value={session.user.last_name} />
					{#if errors.last_name}<p class="error">{errors.last_name}</p>{/if}
				</div>
				<div class="campo">
					<label for="telefono">Teléfono</label>
					<input id="telefono" name="telefono" type="tel" value={session.user.telefono} />
					{#if errors.telefono}<p class="error">{errors.telefono}</p>{/if}
				</div>
				<div class="campo">
					<label for="genero">Género</label>
					<select id="genero" name="genero" value={session.user.genero}>
						<option value="">Sin especificar</option>
						{#each generos as genero (genero)}
							<option value={genero}>{genero}</option>
						{/each}
					</select>
					{#if errors.genero}<p class="error">{errors.genero}</p>{/if}
				</div>
				<div class="campo">
					<label for="direccion">Dirección</label>
					<input id="direccion" name="direccion" type="text" value={session.user.direccion} />
					{#if errors.direccion}<p class="error">{errors.direccion}</p>{/if}
				</div>
				<div class="campo">
					<label for="ciudad">Ciudad</label>
					<input id="ciudad" name="ciudad" type="text" value={session.user.ciudad} />
					{#if errors.ciudad}<p class="error">{errors.ciudad}</p>{/if}
				</div>
				<div class="campo">
					<label for="foto">Foto</label>
					<input id="foto" name="foto" type="file" accept="image/*" />
					{#if errors.foto}<p class="error">{errors.foto}</p>{/if}
				</div>
			</div>
			{#if exito}<p class="exito">{exito}</p>{/if}
			{#if errors.detalle}<p class="error">{errors.detalle}</p>{/if}
			{#if errors.non_field_errors}<p class="error">{errors.non_field_errors}</p>{/if}
			<button class="btn" type="submit" disabled={guardando}>Guardar cambios</button>
		</form>
	{:else}
		<p class="muted">Cargando…</p>
	{/if}
</section>
