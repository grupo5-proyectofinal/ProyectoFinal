<script>
	// Popup de confirmación al unirse a un pool: check animado + resumen de la reserva.
	// `<dialog>` nativo con showModal(): atrapa el foco, cierra con Escape y devuelve
	// el foco al disparador al cerrarse.
	import { moneda } from '$lib/formato.js';
	import Boton from '$lib/ui/Boton.svelte';

	let { abierto = $bindable(false), titulo, cantidad, total } = $props();

	let dialogo = $state();

	$effect(() => {
		if (!dialogo) return;
		if (abierto && !dialogo.open) dialogo.showModal();
		if (!abierto && dialogo.open) dialogo.close();
	});

	function cerrar() {
		abierto = false;
	}

	function alClicFondo(event) {
		// El clic sobre el backdrop llega con el propio <dialog> como target.
		if (event.target === dialogo) cerrar();
	}
</script>

<dialog
	class="dialogo-union"
	bind:this={dialogo}
	aria-labelledby="dialogo-union-titulo"
	aria-describedby="dialogo-union-texto"
	onclose={cerrar}
	onclick={alClicFondo}
>
	<div class="dialogo-union__contenido">
		<span class="dialogo-union__check" aria-hidden="true">
			<svg viewBox="0 0 52 52">
				<circle class="dialogo-union__circulo" cx="26" cy="26" r="24" />
				<path class="dialogo-union__tilde" d="M15 27l7 7 15-16" />
			</svg>
		</span>
		<h2 id="dialogo-union-titulo" class="dialogo-union__titulo">¡Te uniste al pool!</h2>
		<p id="dialogo-union-texto" class="dialogo-union__texto">
			Reservaste <b>{cantidad} {Number(cantidad) === 1 ? 'unidad' : 'unidades'}</b> en
			<b>{titulo}</b> por <b>{moneda(total)}</b>. Te avisamos cuando el pool cambie de estado.
		</p>
		<Boton variante="primario" bloque onclick={cerrar} autofocus>Listo</Boton>
	</div>
</dialog>

<style>
	.dialogo-union {
		width: min(420px, calc(100vw - 2rem));
		padding: 0;
		border: 0;
		border-radius: var(--radio-lg);
		background: var(--superficie);
		color: var(--tinta);
		box-shadow: var(--sombra-md);
	}

	.dialogo-union::backdrop {
		background: rgba(30, 20, 15, 0.45);
	}

	.dialogo-union__contenido {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--e-3);
		padding: var(--e-6) var(--e-5) var(--e-5);
		text-align: center;
	}

	.dialogo-union__check svg {
		width: 72px;
		height: 72px;
	}

	.dialogo-union__circulo {
		fill: var(--exito-suave);
		stroke: var(--exito);
		stroke-width: 2.5;
	}

	.dialogo-union__tilde {
		fill: none;
		stroke: var(--exito);
		stroke-width: 4;
		stroke-linecap: round;
		stroke-linejoin: round;
		stroke-dasharray: 40;
		stroke-dashoffset: 40;
		animation: dibujar-tilde 0.45s 0.15s ease-out forwards;
	}

	.dialogo-union__titulo {
		margin: 0;
		font-size: var(--texto-xl);
	}

	.dialogo-union__texto {
		margin: 0 0 var(--e-2);
		color: var(--tinta-suave);
	}

	@keyframes dibujar-tilde {
		to {
			stroke-dashoffset: 0;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.dialogo-union__tilde {
			animation: none;
			stroke-dashoffset: 0;
		}
	}
</style>
