<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { fieldErrors } from '$lib/api.js';
	import { login } from '$lib/session.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';

	let email = $state('');
	let password = $state('');
	let errors = $state({});
	let general = $state('');
	let enviando = $state(false);
	let verClave = $state(false);

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

<div class="acceso">
	<aside class="acceso__panel">
		<h1 class="acceso__titulo">Volviste. <span>Tus pools te esperan.</span></h1>
		<p class="acceso__bajada">
			Seguí tus compras en conjunto, respondé en el chat y enterate cuando un pool se complete.
		</p>
		<ul class="acceso__pills">
			<li>Estado de cada compra</li>
			<li>Pools de tu ciudad</li>
			<li>Tu propia compra colectiva</li>
		</ul>
	</aside>

	<section class="acceso__card">
		<h2 class="acceso__titulo-card">Ingresar</h2>
		<p class="acceso__bajada">Usá el email con el que te registraste.</p>

		<form class="acceso__form" onsubmit={enviar}>
			<Campo id="email" etiqueta="Email" error={errors.email}>
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

			<Campo id="password" etiqueta="Contraseña" error={errors.password}>
				{#snippet children(props)}
					<div class="acceso__clave" class:acceso__clave--error={Boolean(errors.password)}>
						<input
							id="password"
							name="password"
							type={verClave ? 'text' : 'password'}
							bind:value={password}
							required
							autocomplete="current-password"
							{...props}
						/>
						<button
							class="acceso__ver"
							type="button"
							aria-label={verClave ? 'Ocultar contraseña' : 'Mostrar contraseña'}
							onclick={() => (verClave = !verClave)}
						>
							{verClave ? 'Ocultar' : 'Mostrar'}
						</button>
					</div>
				{/snippet}
			</Campo>

			<div class="acceso__fila">
				<a class="acceso__olvide" href={resolve('/recuperar')}>¿Olvidaste tu contraseña?</a>
			</div>

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
				{#if enviando}<span class="spinner spinner--chico"></span> Ingresando…{:else}Ingresar{/if}
			</Boton>
		</form>

		<p class="acceso__pie">
			¿Primera vez en PoolShop? <a href={resolve('/registro')}>Creá tu cuenta</a>
		</p>
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

	.acceso__titulo span {
		color: var(--marca);
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

	/* Métricas del mockup 13 (50px / 12px / 15px) sobre los controles de la card. */
	.acceso__form input {
		min-height: 50px;
		font-size: 0.9375rem;
	}

	/* Contraseña con botón Mostrar/Ocultar: el borde lo lleva la envoltura. */
	.acceso__clave {
		display: flex;
		align-items: center;
		min-height: 50px;
		padding-right: 6px;
		border: 1px solid var(--linea-control);
		border-radius: var(--radio-sm);
		background: var(--superficie);
		transition: border-color var(--transicion);
	}

	.acceso__clave:focus-within {
		border-color: var(--acento);
		outline: 2px solid var(--acento);
		outline-offset: 1px;
	}

	.acceso__clave--error {
		border-color: var(--peligro);
	}

	.acceso__clave input {
		flex: 1;
		min-width: 0;
		border: 0;
		outline: 0;
	}

	.acceso__clave input:focus-visible {
		outline: none;
	}

	.acceso__ver {
		flex: none;
		min-height: 38px;
		padding: 0 10px;
		border: 0;
		border-radius: var(--radio-xs);
		background: transparent;
		color: var(--marca-fuerte);
		font-family: inherit;
		font-size: var(--texto-xs);
		font-weight: 700;
		cursor: pointer;
	}

	.acceso__ver:hover {
		background: var(--melocoton);
	}

	.acceso__fila {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		align-items: center;
		gap: 10px;
	}

	.acceso__olvide {
		font-size: var(--texto-sm);
		font-weight: 700;
	}

	/* CTA del mockup: 54px de alto y radio 14px sobre la primitiva. */
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
