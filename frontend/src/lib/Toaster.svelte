<script>
	import { flip } from 'svelte/animate';
	import { cubicOut } from 'svelte/easing';
	import { fade, fly } from 'svelte/transition';
	import { duracion } from '$lib/movimiento.js';
	import { cerrar, DURACION, toasts } from '$lib/toast.svelte.js';
</script>

<div class="toasts" role="status" aria-live="polite">
	{#each toasts as aviso (aviso.id)}
		<div
			class="toast toast--{aviso.tipo}"
			style:--vida="{DURACION[aviso.tipo] ?? 4000}ms"
			in:fly={{ x: 32, duration: duracion(240), easing: cubicOut }}
			out:fade={{ duration: duracion(150) }}
			animate:flip={{ duration: duracion(200), easing: cubicOut }}
		>
			<span>{aviso.mensaje}</span>
			<button
				class="toast__cerrar"
				type="button"
				onclick={() => cerrar(aviso.id)}
				aria-label="Cerrar aviso"
			>
				×
			</button>
		</div>
	{/each}
</div>

<style>
	.toasts {
		position: fixed;
		right: var(--e-4);
		bottom: var(--e-4);
		z-index: 60;
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		width: min(22rem, calc(100vw - 2rem));
		pointer-events: none;
	}

	.toast {
		position: relative;
		overflow: hidden;
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--e-3);
		padding: 0.7rem 0.8rem 0.7rem 1rem;
		border: 1px solid var(--tono, var(--linea));
		border-radius: var(--radio-sm);
		background: var(--superficie);
		box-shadow: var(--sombra-md);
		font-size: var(--texto-sm);
		pointer-events: auto;
	}

	/* Tiempo que le queda al aviso antes de cerrarse solo. */
	.toast::after {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		height: 2px;
		background: var(--tono, currentColor);
		opacity: 0.35;
		transform-origin: left;
		animation: vida var(--vida) linear both;
	}

	@keyframes vida {
		from {
			transform: scaleX(1);
		}
		to {
			transform: scaleX(0);
		}
	}

	.toast--exito {
		--tono: var(--exito);
		border-color: var(--exito);
	}

	.toast--error {
		--tono: var(--peligro);
		border-color: var(--peligro);
	}

	.toast--aviso {
		--tono: var(--alerta);
		border-color: var(--alerta);
	}

	.toast--info {
		--tono: var(--acento);
		border-color: var(--acento);
	}

	.toast__cerrar {
		flex: none;
		width: 2rem;
		height: 2rem;
		display: grid;
		place-items: center;
		border: 0;
		border-radius: var(--radio-xs);
		background: transparent;
		color: var(--tinta-suave);
		font-size: 1.1rem;
		line-height: 1;
		cursor: pointer;
	}

	.toast__cerrar:hover {
		background: var(--superficie-alt);
		color: var(--tinta);
	}
</style>
