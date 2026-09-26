<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { fieldErrors } from '$lib/api.js';
	import { register } from '$lib/session.svelte.js';

	let errors = $state({});
	let general = $state('');
	let enviando = $state(false);
	let form = $state();

	const generos = ['Femenino', 'Masculino', 'Otro', 'Prefiero no decir'];

	async function enviar(event) {
		event.preventDefault();
		errors = {};
		general = '';
		if (form.password.value !== form.password2.value) {
			errors = { password2: 'Las contraseñas no coinciden.' };
			return;
		}
		enviando = true;
		try {
			const data = new FormData(form);
			if (!data.get('foto')?.name) data.delete('foto');
			await register(data, true);
			goto(resolve('/'));
		} catch (error) {
			errors = fieldErrors(error.data);
			if (!Object.keys(errors).length) general = 'No se pudo crear la cuenta.';
		} finally {
			enviando = false;
		}
	}
</script>

<section class="tarjeta">
	<h1>Crear cuenta</h1>
	<form bind:this={form} onsubmit={enviar}>
		<div class="grilla">
			<div class="campo">
				<label for="email">Email</label>
				<input id="email" name="email" type="email" required autocomplete="email" />
				{#if errors.email}<p class="error">{errors.email}</p>{/if}
			</div>
			<div class="campo">
				<label for="username">Nombre de usuario</label>
				<input id="username" name="username" type="text" required autocomplete="username" />
				{#if errors.username}<p class="error">{errors.username}</p>{/if}
			</div>
			<div class="campo">
				<label for="first_name">Nombre</label>
				<input id="first_name" name="first_name" type="text" autocomplete="given-name" />
				{#if errors.first_name}<p class="error">{errors.first_name}</p>{/if}
			</div>
			<div class="campo">
				<label for="last_name">Apellido</label>
				<input id="last_name" name="last_name" type="text" autocomplete="family-name" />
				{#if errors.last_name}<p class="error">{errors.last_name}</p>{/if}
			</div>
			<div class="campo">
				<label for="dni">DNI</label>
				<input id="dni" name="dni" type="text" required />
				{#if errors.dni}<p class="error">{errors.dni}</p>{/if}
			</div>
			<div class="campo">
				<label for="telefono">Teléfono</label>
				<input id="telefono" name="telefono" type="tel" autocomplete="tel" />
				{#if errors.telefono}<p class="error">{errors.telefono}</p>{/if}
			</div>
			<div class="campo">
				<label for="genero">Género</label>
				<select id="genero" name="genero">
					<option value="">Sin especificar</option>
					{#each generos as genero (genero)}
						<option value={genero}>{genero}</option>
					{/each}
				</select>
				{#if errors.genero}<p class="error">{errors.genero}</p>{/if}
			</div>
			<div class="campo">
				<label for="direccion">Dirección</label>
				<input id="direccion" name="direccion" type="text" autocomplete="street-address" />
				{#if errors.direccion}<p class="error">{errors.direccion}</p>{/if}
			</div>
			<div class="campo">
				<label for="ciudad">Ciudad</label>
				<input id="ciudad" name="ciudad" type="text" autocomplete="address-level2" />
				{#if errors.ciudad}<p class="error">{errors.ciudad}</p>{/if}
			</div>
			<div class="campo">
				<label for="foto">Foto (opcional)</label>
				<input id="foto" name="foto" type="file" accept="image/*" />
				{#if errors.foto}<p class="error">{errors.foto}</p>{/if}
			</div>
			<div class="campo">
				<label for="password">Contraseña</label>
				<input
					id="password"
					name="password"
					type="password"
					required
					autocomplete="new-password"
				/>
				{#if errors.password}<p class="error">{errors.password}</p>{/if}
			</div>
			<div class="campo">
				<label for="password2">Repetir contraseña</label>
				<input
					id="password2"
					name="password2"
					type="password"
					required
					autocomplete="new-password"
				/>
				{#if errors.password2}<p class="error">{errors.password2}</p>{/if}
			</div>
		</div>
		{#if errors.non_field_errors || general}
			<p class="error">{errors.non_field_errors || general}</p>
		{/if}
		<button class="btn" type="submit" disabled={enviando}>Crear cuenta</button>
	</form>
	<p class="muted">¿Ya tenés cuenta? <a href={resolve('/login')}>Ingresá</a>.</p>
</section>
