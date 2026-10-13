<script>
	import { resolve } from '$app/paths';
	import { api } from '$lib/api.js';
	import { confirmacionDeSolicitud, mensajeReset } from '$lib/recuperacion.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';

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

<div class="acceso">
	<aside class="acceso__panel">
		<h1 class="acceso__titulo">¿Te olvidaste la contraseña?</h1>
		<p class="acceso__bajada">
			Poné el email con el que te registraste y te enviamos un enlace para definir una contraseña
			nueva.
		</p>
		<ul class="acceso__pills">
			<li>El enlace vence solo</li>
			<li>Revisá el spam si no llega</li>
			<li>Podés pedir otro cuando quieras</li>
		</ul>
	</aside>

	<section class="acceso__card">
		{#if confirmacion}
			<div class="acceso__hecho">
				<span class="acceso__hecho-icono" aria-hidden="true">
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.8"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<rect x="3" y="5" width="18" height="14" rx="2" />
						<path d="M3 7l9 6 9-6" />
					</svg>
				</span>
				<h2 class="acceso__titulo-card">Revisá tu email</h2>
				<Aviso variante="info">{confirmacion}</Aviso>
				<p class="acceso__bajada">Puede tardar unos minutos. Fijate también en spam.</p>
				<Boton variante="secundario" href={resolve('/login')}>Volver a ingresar</Boton>
			</div>
		{:else}
			<h2 class="acceso__titulo-card">Recuperar contraseña</h2>
			<p class="acceso__bajada">Usá el email con el que te registraste.</p>

			<form class="acceso__form" onsubmit={enviar}>
				<Campo id="email" etiqueta="Email">
					{#snippet children(props)}
						<input
							id="email"
							name="email"
							type="email"
							bind:value={email}
							required
							autocomplete="email"
							spellcheck="false"
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
					{#if enviando}<span class="spinner spinner--chico"></span> Enviando…{:else}Enviar enlace{/if}
				</Boton>
			</form>

			<p class="acceso__pie">
				¿Te acordaste? <a href={resolve('/login')}>Ingresá</a>.
			</p>
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

	/* Confirmación neutral (mockup 13, vista "sent"). */
	.acceso__hecho {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--e-3);
		text-align: center;
	}

	.acceso__hecho-icono {
		display: grid;
		place-items: center;
		width: 72px;
		height: 72px;
		border-radius: var(--radio-lg);
		background: var(--melocoton-fuerte);
		color: var(--naranja-fuerte);
	}

	.acceso__hecho-icono svg {
		width: 34px;
		height: 34px;
	}

	.acceso__hecho .acceso__bajada {
		margin: 0;
		max-width: 360px;
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
