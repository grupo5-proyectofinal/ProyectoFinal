<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, fieldErrors } from '$lib/api.js';
	import { enlaceInvalido, mensajeReset, parametrosDeReset } from '$lib/recuperacion.js';
	import { notificar } from '$lib/toast.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';

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

<div class="acceso">
	<aside class="acceso__panel">
		<h1 class="acceso__titulo">Casi listo</h1>
		<p class="acceso__bajada">
			Elegí una contraseña nueva para tu cuenta. Después vas a poder ingresar con ella como
			siempre.
		</p>
		<ul class="acceso__pills">
			<li>El enlace se usa una sola vez</li>
			<li>Si venció, pedí uno nuevo</li>
			<li>La anterior deja de funcionar</li>
		</ul>
	</aside>

	<section class="acceso__card">
		{#if !parametros.completo || enlaceRoto}
			<h2 class="acceso__titulo-card">Enlace inválido</h2>
			<Aviso variante="error">
				{enlaceRoto || 'El enlace está incompleto o no es válido. Pedí uno nuevo.'}
			</Aviso>
			<p class="acceso__bajada">
				Los enlaces de restablecimiento vencen por seguridad y se pueden usar una sola vez.
			</p>
			<Boton variante="primario" bloque href={resolve('/recuperar')}>Pedir un enlace nuevo</Boton>
			<p class="acceso__pie">
				¿Te acordaste? <a href={resolve('/login')}>Ingresá</a>.
			</p>
		{:else}
			<h2 class="acceso__titulo-card">Definí tu contraseña</h2>
			<p class="acceso__bajada">Elegí una contraseña nueva para tu cuenta.</p>

			<form class="acceso__form" onsubmit={enviar}>
				<Campo
					id="password"
					etiqueta="Contraseña nueva"
					requerido
					ayuda="Mínimo 8 caracteres, no muy común."
					error={errors.password}
				>
					{#snippet children(props)}
						<input
							id="password"
							name="password"
							type="password"
							bind:value={password}
							required
							autocomplete="new-password"
							{...props}
						/>
					{/snippet}
				</Campo>

				<Campo id="password2" etiqueta="Repetir contraseña" requerido error={errors.password2}>
					{#snippet children(props)}
						<input
							id="password2"
							name="password2"
							type="password"
							bind:value={password2}
							required
							autocomplete="new-password"
							{...props}
						/>
					{/snippet}
				</Campo>

				{#if general}
					<Aviso variante="error">{general}</Aviso>
				{/if}

				<Boton
					variante="primario"
					tamano="lg"
					bloque
					tipo="submit"
					disabled={enviando}
					class="acceso__cta"
				>
					{#if enviando}<span class="spinner spinner--chico"></span> Guardando…{:else}Cambiar contraseña{/if}
				</Boton>
			</form>
		{/if}
	</section>
</div>

<style>
	.acceso {
		display: flex;
		flex-wrap: wrap;
		align-items: stretch;
		gap: 36px;
	}

	.acceso__panel {
		display: flex;
		flex: 1 1 380px;
		flex-direction: column;
		justify-content: center;
		gap: var(--e-4);
		min-width: 0;
		padding: 40px;
		border-radius: var(--radio-lg);
		background: var(--melocoton-fuerte);
	}

	.acceso__titulo {
		font-size: clamp(2rem, 3.2vw, 2.875rem);
		letter-spacing: -0.03em;
		line-height: 1.05;
	}

	.acceso__bajada {
		margin: 0;
		max-width: 46ch;
		font-size: 1.0625rem;
		line-height: 1.5;
		color: var(--tinta-suave);
	}

	.acceso__pills {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
		margin: var(--e-2) 0 0;
		padding: 0;
		list-style: none;
	}

	.acceso__pills li {
		padding: 8px 14px;
		border-radius: var(--radio-full);
		background: var(--superficie);
		font-size: var(--texto-sm);
		font-weight: 700;
	}

	.acceso__card {
		display: flex;
		flex: 999 1 460px;
		flex-direction: column;
		justify-content: center;
		min-width: 0;
		max-width: 560px;
		padding: 36px;
		border: 1px solid var(--linea);
		border-radius: var(--radio-lg);
		background: var(--superficie);
	}

	.acceso__titulo-card {
		font-size: clamp(1.6rem, 2.2vw, 1.875rem);
	}

	.acceso__card .acceso__bajada {
		margin-top: var(--e-3);
		margin-bottom: var(--e-5);
	}

	.acceso__form {
		display: flex;
		flex-direction: column;
		gap: 18px;
	}

	.acceso__form :global(.ui-campo) {
		margin-bottom: 0;
	}

	.acceso__form input {
		min-height: 50px;
		font-size: 0.9375rem;
	}

	:global(.acceso__cta.ui-boton) {
		min-height: 54px;
		border-radius: var(--radio);
		font-size: var(--texto-md);
	}

	.acceso__pie {
		margin-top: var(--e-5);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	@media (max-width: 800px) {
		.acceso {
			gap: var(--e-5);
		}

		.acceso__panel {
			order: 1;
			padding: var(--e-5);
		}

		.acceso__card {
			max-width: none;
			padding: var(--e-5);
		}
	}
</style>
