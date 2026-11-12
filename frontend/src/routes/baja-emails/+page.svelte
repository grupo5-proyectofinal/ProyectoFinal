<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api } from '$lib/api.js';
	import { session } from '$lib/session.svelte.js';
	import { mensajeVerificacion, tokenDeBaja } from '$lib/verificacion.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';

	const token = $derived(tokenDeBaja(page.url.search));

	let estado = $state('confirmar');
	let mensaje = $state('');
	let correo = $state('');
	let enviando = $state(false);

	// El enlace es de una cuenta: mostrarla (enmascarada) antes de confirmar.
	$effect(() => {
		if (!token) return;
		api(`/auth/baja-emails/?token=${encodeURIComponent(token)}`, { auth: false })
			.then((r) => (correo = r.email ?? ''))
			.catch(() => {
				// Si no se puede leer, el POST igual valida el token y muestra su error.
			});
	});

	// La baja pide un click explícito: algunos clientes de mail abren los links
	// solos para escanearlos, y eso no debería dar de baja a nadie.
	async function darDeBaja() {
		enviando = true;
		try {
			const respuesta = await api('/auth/baja-emails/', {
				method: 'POST',
				body: { token },
				auth: false
			});
			mensaje = respuesta.detail;
			correo = respuesta.email ?? correo;
			estado = 'listo';
		} catch (e) {
			mensaje = mensajeVerificacion(e);
			estado = 'error';
		} finally {
			enviando = false;
		}
	}
</script>

<svelte:head>
	<title>Dejar de recibir correos — PoolShop</title>
</svelte:head>

<div class="acceso">
	<aside class="acceso__panel">
		<p class="acceso__titulo">Vos elegís <span>qué te llega</span></p>
		<p class="acceso__bajada">
			Los avisos de tus pools siguen en la campana de la app. Los correos de tu cuenta (verificación
			y contraseña) te van a seguir llegando porque protegen tu acceso.
		</p>
	</aside>

	<section class="acceso__card">
		{#if !token}
			<h1 class="acceso__titulo-card">Enlace incompleto</h1>
			<Aviso variante="error">Abrí el enlace de nuevo desde el pie del correo.</Aviso>
			<Boton variante="primario" bloque href={resolve('/')}>Volver a PoolShop</Boton>
			<Boton variante="ghost" bloque href={resolve('/login')}>Ingresar</Boton>
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
				<h1 class="acceso__titulo-card">Listo</h1>
				<Aviso variante="exito">
					{mensaje}{#if correo} La cuenta es <strong>{correo}</strong>.{/if}
				</Aviso>
				<Boton variante="primario" href={resolve('/')}>Volver a PoolShop</Boton>
				{#if session.access}
					<Boton variante="ghost" href={resolve('/notificaciones')}>Gestionar mis avisos</Boton>
				{/if}
			</div>
		{:else}
			<h1 class="acceso__titulo-card">Dejar de recibir notificaciones por mail</h1>
			{#if correo}
				<p class="acceso__bajada">
					Vas a dejar de recibir avisos de tus pools en <strong>{correo}</strong>.
				</p>
			{:else}
				<p class="acceso__bajada">
					Vas a dejar de recibir los avisos de tus pools por mail.
				</p>
			{/if}
			<p class="acceso__bajada">
				Podés volver a activarlos cuando quieras desde Notificaciones. Los correos de tu cuenta
				(verificación y contraseña) te siguen llegando.
			</p>
			{#if estado === 'error'}
				<Aviso variante="error">{mensaje}</Aviso>
			{/if}
			<Boton variante="peligro-suave" bloque disabled={enviando} onclick={darDeBaja}>
				{enviando ? 'Guardando…' : 'Confirmar baja'}
			</Boton>
			<Boton variante="ghost" bloque href={resolve('/')}>Cancelar</Boton>
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

	:global(.acceso__cta.ui-boton) {
		min-height: 54px;
		border-radius: var(--radio);
		font-size: var(--texto-md);
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
