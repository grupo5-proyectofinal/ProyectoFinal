<script>
	// Festejo de "¡Compra realizada!": confeti con los colores de la marca y las
	// bolsitas del logo saltando. Se cierra solo, con un clic o con Escape.
	// Con "reducir movimiento" no hay confeti: solo el cartel con un fundido.
	import { fade, scale } from 'svelte/transition';
	import { backOut } from 'svelte/easing';
	import { piezasConfeti } from '$lib/festejo.js';
	import { duracion, prefiereMenosMovimiento } from '$lib/movimiento.js';
	import Logo from '$lib/Logo.svelte';

	let { titulo = '¡Compra realizada!', detalle = '', alCerrar } = $props();

	const piezas = prefiereMenosMovimiento() ? [] : piezasConfeti(70);

	$effect(() => {
		const temporizador = setTimeout(() => alCerrar?.(), 3200);
		const alTeclear = (evento) => {
			if (evento.key === 'Escape') alCerrar?.();
		};
		window.addEventListener('keydown', alTeclear);
		return () => {
			clearTimeout(temporizador);
			window.removeEventListener('keydown', alTeclear);
		};
	});
</script>

<!-- Es decorativo y se cierra solo: el clic es un atajo, Escape cubre el teclado. -->
<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="festejo" onclick={() => alCerrar?.()} transition:fade={{ duration: duracion(250) }}>
	<div class="festejo__confeti" aria-hidden="true">
		{#each piezas as p (p.id)}
			<span
				class="festejo__pieza festejo__pieza--{p.forma}"
				style:left="{p.x}%"
				style:background={p.color}
				style:--deriva="{p.deriva}vw"
				style:--giro="{p.giro}deg"
				style:animation-delay="{p.retraso}ms"
				style:animation-duration="{p.duracion}ms"
			></span>
		{/each}
	</div>

	<div
		class="festejo__cartel"
		role="status"
		in:scale={{ start: 0.7, duration: duracion(450), easing: backOut }}
	>
		<Logo conNombre={false} class="marca--festejo" />
		<p class="festejo__titulo">{titulo}</p>
		{#if detalle}<p class="festejo__detalle">{detalle}</p>{/if}
	</div>
</div>

<style>
	.festejo {
		position: fixed;
		inset: 0;
		z-index: 70;
		display: grid;
		place-items: center;
		padding: var(--e-4);
		background: color-mix(in srgb, var(--tinta) 18%, transparent);
		cursor: pointer;
	}

	.festejo__confeti {
		position: absolute;
		inset: 0;
		overflow: hidden;
		pointer-events: none;
	}

	.festejo__pieza {
		position: absolute;
		top: -4vh;
		width: 0.6rem;
		height: 0.6rem;
		border-radius: 2px;
		opacity: 0;
		animation-name: caida;
		animation-timing-function: cubic-bezier(0.25, 0.6, 0.5, 1);
		animation-fill-mode: forwards;
	}

	.festejo__pieza--tira {
		width: 0.35rem;
		height: 0.9rem;
	}

	@keyframes caida {
		0% {
			opacity: 1;
			transform: translate(0, 0) rotate(0);
		}
		85% {
			opacity: 1;
		}
		100% {
			opacity: 0;
			transform: translate(var(--deriva), 108vh) rotate(var(--giro));
		}
	}

	.festejo__cartel {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--e-2);
		max-width: 22rem;
		padding: var(--e-6) var(--e-6) var(--e-5);
		border-radius: var(--radio-lg);
		background: var(--superficie);
		box-shadow: 0 20px 50px rgb(0 0 0 / 0.2);
		text-align: center;
	}

	.festejo__cartel :global(.marca--festejo) {
		font-size: 3.5rem;
		margin-bottom: var(--e-2);
	}

	.festejo__titulo {
		margin: 0;
		font-family: var(--fuente-display);
		font-size: var(--texto-xl);
		font-weight: 800;
		color: var(--tinta);
	}

	.festejo__detalle {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}
</style>
