<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { fieldErrors } from '$lib/api.js';
	import { login } from '$lib/session.svelte.js';

	let email = $state('');
	let password = $state('');
	let errors = $state({});
	let general = $state('');
	let enviando = $state(false);

	async function enviar(event) {
		event.preventDefault();
		errors = {};
		general = '';
		enviando = true;
		try {
			await login(email, password);
			goto(resolve('/'));
		} catch (error) {
			if (error.status === 401) {
				general = 'Email o contraseña incorrectos.';
			} else {
				errors = fieldErrors(error.data);
				general = errors.detail || 'No se pudo iniciar sesión.';
				delete errors.detail;
			}
		} finally {
			enviando = false;
		}
	}
</script>

<section class="tarjeta angosta">
	<h1>Ingresar</h1>
	<form onsubmit={enviar}>
		<div class="campo">
			<label for="email">Email</label>
			<input id="email" name="email" type="email" bind:value={email} required autocomplete="email" />
			{#if errors.email}<p class="error">{errors.email}</p>{/if}
		</div>
		<div class="campo">
			<label for="password">Contraseña</label>
			<input
				id="password"
				name="password"
				type="password"
				bind:value={password}
				required
				autocomplete="current-password"
			/>
			{#if errors.password}<p class="error">{errors.password}</p>{/if}
		</div>
		{#if general}<p class="error">{general}</p>{/if}
		<button class="btn" type="submit" disabled={enviando}>Ingresar</button>
	</form>
	<p class="muted">¿No tenés cuenta? <a href={resolve('/registro')}>Registrate</a>.</p>
</section>
