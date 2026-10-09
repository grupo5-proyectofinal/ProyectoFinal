<script>
	import { resolve } from '$app/paths';
	import { api } from '$lib/api.js';
	import { confirmacionDeSolicitud, mensajeReset } from '$lib/recuperacion.js';

	let email = $state('');
	let general = $state('');
	let enviando = $state(false);
	let confirmacion = $state('');

	async function enviar(event) {
		event.preventDefault();
		if (enviando) return;
		general = '';
		enviando = true;
		try {
			const data = await api('/auth/password-reset/', {
				method: 'POST',
				body: { email },
				auth: false
			});
			confirmacion = confirmacionDeSolicitud(data);
		} catch (error) {
			general = mensajeReset(error);
		} finally {
			enviando = false;
		}
	}
</script>

<svelte:head>
	<title>Recuperar contraseña — PoolShop</title>
</svelte:head>

<div class="auth">
	<aside class="auth__panel">
		<p class="auth__panel-titulo">¿Te olvidaste la contraseña?</p>
		<p>
			Poné el email con el que te registraste y te enviamos un enlace para definir una
			contraseña nueva.
		</p>
		<ul>
			<li>El enlace vence solo, por seguridad.</li>
			<li>Si no llega, revisá la carpeta de correo no deseado.</li>
			<li>Podés pedir un enlace nuevo cuando quieras.</li>
		</ul>
	</aside>

	<section class="auth__formulario">
		{#if confirmacion}
			<h1>Revisá tu correo</h1>
			<div class="alerta alerta--info aviso" role="status">{confirmacion}</div>
			<p class="muted intro">Puede tardar unos minutos. Fijate también en spam.</p>
			<a class="btn btn--primario btn--bloque" href={resolve('/login')}>Volver a ingresar</a>
		{:else}
			<h1>Recuperar contraseña</h1>
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
					/>
				</div>

				{#if general}
					<div class="alerta alerta--error aviso" role="alert">{general}</div>
				{/if}

				<button class="btn btn--primario btn--bloque" type="submit" disabled={enviando}>
					{#if enviando}<span class="spinner spinner--chico"></span> Enviando…{:else}Enviar enlace{/if}
				</button>
			</form>

			<p class="auth__cambio">
				¿Te acordaste? <a href={resolve('/login')}>Ingresá</a>.
			</p>
		{/if}
	</section>
</div>
