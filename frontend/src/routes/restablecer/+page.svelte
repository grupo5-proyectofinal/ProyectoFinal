<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, fieldErrors } from '$lib/api.js';
	import { enlaceInvalido, mensajeReset, parametrosDeReset } from '$lib/recuperacion.js';
	import { notificar } from '$lib/toast.svelte.js';

	const parametros = $derived(parametrosDeReset(page.url.search));

	let password = $state('');
	let password2 = $state('');
	let errors = $state({});
	let general = $state('');
	let enviando = $state(false);
	let enlaceRoto = $state('');

	async function enviar(event) {
		event.preventDefault();
		if (enviando) return;
		errors = {};
		general = '';
		if (password !== password2) {
			errors = { password2: 'Las contraseñas no coinciden.' };
			return;
		}
		enviando = true;
		try {
			await api('/auth/password-reset/confirm/', {
				method: 'POST',
				body: {
					uid: parametros.uid,
					token: parametros.token,
					password,
					password2
				},
				auth: false
			});
			notificar('Contraseña actualizada. Ya podés iniciar sesión.');
			goto(resolve('/login'));
		} catch (error) {
			if (enlaceInvalido(error)) {
				enlaceRoto = mensajeReset(error);
			} else {
				errors = fieldErrors(error.data);
				delete errors.detail;
				delete errors.non_field_errors;
				general = !errors.password && !errors.password2 ? mensajeReset(error) : '';
			}
		} finally {
			enviando = false;
		}
	}
</script>

<svelte:head>
	<title>Definir contraseña — PoolShop</title>
</svelte:head>

<div class="auth">
	<aside class="auth__panel">
		<p class="auth__panel-titulo">Casi listo</p>
		<p>
			Elegí una contraseña nueva para tu cuenta. Después vas a poder ingresar con ella como
			siempre.
		</p>
		<ul>
			<li>El enlace se puede usar una sola vez.</li>
			<li>Si venció, pedí uno nuevo en un minuto.</li>
			<li>Tu contraseña anterior deja de funcionar.</li>
		</ul>
	</aside>

	<section class="auth__formulario">
		{#if !parametros.completo || enlaceRoto}
			<h1>Enlace inválido</h1>
			<div class="alerta alerta--error aviso" role="alert">
				{enlaceRoto || 'El enlace está incompleto o no es válido. Pedí uno nuevo.'}
			</div>
			<p class="muted intro">
				Los enlaces de restablecimiento vencen por seguridad y se pueden usar una sola vez.
			</p>
			<a class="btn btn--primario btn--bloque" href={resolve('/recuperar')}>Pedir un enlace nuevo</a>
			<p class="auth__cambio">
				¿Te acordaste? <a href={resolve('/login')}>Ingresá</a>.
			</p>
		{:else}
			<h1>Definí tu contraseña</h1>
			<p class="muted intro">Elegí una contraseña nueva para tu cuenta.</p>

			<form onsubmit={enviar}>
				<div class="campo">
					<label for="password">Contraseña nueva</label>
					<input
						id="password"
						name="password"
						type="password"
						bind:value={password}
						required
						autocomplete="new-password"
						aria-invalid={errors.password ? 'true' : undefined}
						aria-describedby={errors.password ? 'password-error' : 'password-ayuda'}
					/>
					{#if errors.password}
						<p class="error" id="password-error">{errors.password}</p>
					{:else}
						<p class="ayuda" id="password-ayuda">Mínimo 8 caracteres, no muy común.</p>
					{/if}
				</div>

				<div class="campo">
					<label for="password2">Repetir contraseña</label>
					<input
						id="password2"
						name="password2"
						type="password"
						bind:value={password2}
						required
						autocomplete="new-password"
						aria-invalid={errors.password2 ? 'true' : undefined}
						aria-describedby={errors.password2 ? 'password2-error' : undefined}
					/>
					{#if errors.password2}
						<p class="error" id="password2-error">{errors.password2}</p>
					{/if}
				</div>

				{#if general}
					<div class="alerta alerta--error aviso" role="alert">{general}</div>
				{/if}

				<button class="btn btn--primario btn--bloque" type="submit" disabled={enviando}>
					{#if enviando}<span class="spinner spinner--chico"></span> Guardando…{:else}Cambiar contraseña{/if}
				</button>
			</form>
		{/if}
	</section>
</div>
