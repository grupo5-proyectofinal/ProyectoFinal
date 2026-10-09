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

<svelte:head>
	<title>Ingresar — PoolShop</title>
</svelte:head>

<div class="auth">
	<aside class="auth__panel">
		<p class="auth__panel-titulo">Qué bueno verte de nuevo</p>
		<p>
			Entrá para seguir tus pools, ajustar tu cantidad y confirmar los pedidos que ya están en
			curso.
		</p>
		<ul>
			<li>Mirá el estado de cada compra en la que participás.</li>
			<li>Sumate a nuevos pools de tu ciudad.</li>
			<li>Organizá tu propia compra colectiva.</li>
		</ul>
	</aside>

	<section class="auth__formulario">
		<h1>Ingresar</h1>
		<p class="muted intro">Usá el email con el que te registraste.</p>

		<form onsubmit={enviar}>
			<div class="campo">
				<label for="email">Email</label>
				<input
					id="email"
					name="email"
					type="email"
					bind:value={email}
					required
					autocomplete="email"
					spellcheck="false"
					aria-invalid={errors.email ? 'true' : undefined}
					aria-describedby={errors.email ? 'email-error' : undefined}
				/>
				{#if errors.email}<p class="error" id="email-error">{errors.email}</p>{/if}
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
					aria-invalid={errors.password ? 'true' : undefined}
					aria-describedby={errors.password ? 'password-error' : undefined}
				/>
				{#if errors.password}<p class="error" id="password-error">{errors.password}</p>{/if}
			</div>

			{#if general}
				<div class="alerta alerta--error aviso" role="alert">{general}</div>
			{/if}

			<button class="btn btn--primario btn--bloque" type="submit" disabled={enviando}>
				{#if enviando}<span class="spinner spinner--chico"></span> Ingresando…{:else}Ingresar{/if}
			</button>
		</form>

		<p class="auth__cambio">
			¿Olvidaste tu contraseña? <a href={resolve('/recuperar')}>Recuperala</a>.
		</p>

		<p class="auth__cambio">
			¿No tenés cuenta? <a href={resolve('/registro')}>Creá una cuenta</a>.
		</p>
	</section>
</div>

