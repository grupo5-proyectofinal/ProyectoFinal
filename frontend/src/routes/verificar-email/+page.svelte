<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { parametrosDeReset } from '$lib/recuperacion.js';
	import { reenviarVerificacion, verificarEmail } from '$lib/session.svelte.js';
	import { mensajeVerificacion } from '$lib/verificacion.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';

	// El link del mail trae `uid` y `token`, igual que el de restablecer.
	const enlace = $derived(parametrosDeReset(page.url.search));

	let estado = $state('verificando');
	let error = $state('');
	let email = $state('');
	let reenviado = $state('');
	let enviando = $state(false);
	let intentado = false;

	$effect(() => {
		if (intentado) return;
		intentado = true;
		if (!enlace.completo) {
			estado = 'error';
			error = 'El enlace está incompleto. Abrilo de nuevo desde el mail.';
			return;
		}
		verificar(enlace.uid, enlace.token);
	});

	async function verificar(uid, token) {
		try {
			await verificarEmail(uid, token);
			estado = 'listo';
		} catch (e) {
			estado = 'error';
			error = mensajeVerificacion(e);
		}
	}

	async function reenviar(event) {
		event.preventDefault();
		if (enviando) return;
		enviando = true;
		reenviado = '';
		try {
			reenviado = (await reenviarVerificacion(email)).detail;
		} catch (e) {
			error = mensajeVerificacion(e);
		} finally {
			enviando = false;
		}
	}
</script>

<svelte:head>
	<title>Confirmar email — PoolShop</title>
</svelte:head>

<div class="acceso">
	<aside class="acceso__panel">
		<h1 class="acceso__titulo">Un paso más y <span>ya estás adentro</span></h1>
		<p class="acceso__bajada">
			Confirmamos tu email para proteger tu cuenta y que te lleguen los avisos de tus pools.
		</p>
	</aside>

	<section class="acceso__card" aria-live="polite">
		{#if estado === 'verificando'}
			<h2 class="acceso__titulo-card">Confirmando tu email…</h2>
			<p class="acceso__bajada" role="status">Esto tarda un segundo.</p>
		{:else if estado === 'listo'}
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
				<h2 class="acceso__titulo-card">¡Cuenta confirmada!</h2>
				<Aviso variante="exito">Ya iniciaste sesión. Te mandamos un mail de bienvenida.</Aviso>
				<Boton variante="primario" onclick={() => goto(resolve('/pools'))}>Explorar pools</Boton>
			</div>
		{:else}
			<h2 class="acceso__titulo-card">No pudimos confirmar tu email</h2>
			<Aviso variante="error">{error}</Aviso>
			<p class="acceso__bajada">
				Si ya la confirmaste, <a href={resolve('/login')}>ingresá</a>. Si no, pedí un enlace nuevo:
			</p>
			{#if reenviado}
				<Aviso variante="info">{reenviado}</Aviso>
			{:else}
				<form class="acceso__form" onsubmit={reenviar}>
					<Campo id="email" etiqueta="Email">
						{#snippet children(props)}
							<input
								id="email"
								type="email"
								bind:value={email}
								required
								autocomplete="email"
								{...props}
							/>
						{/snippet}
					</Campo>
					<Boton variante="primario" bloque tipo="submit" disabled={enviando}>
						{enviando ? 'Enviando…' : 'Enviar enlace nuevo'}
					</Boton>
				</form>
			{/if}
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
