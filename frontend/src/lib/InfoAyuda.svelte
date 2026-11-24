<script>
	import Boton from '$lib/ui/Boton.svelte';

	// Ícono "i" que abre una explicación. Es un diálogo nativo: se ve entero en el celular (un
	// globo flotante quedaba tapado por la barra de abajo), atrapa el foco, se cierra con Esc,
	// con el botón o tocando afuera, y devuelve el foco al ícono.
	let { titulo, etiqueta = 'Más información', children } = $props();

	const tituloId = $props.id();
	let dialogo = $state();

	function cerrarSiEsFondo(event) {
		// El clic sobre el propio <dialog> (y no sobre su contenido) es un clic en el fondo.
		if (event.target === dialogo) dialogo.close();
	}
</script>

<button type="button" class="info__boton" aria-label={etiqueta} onclick={() => dialogo?.showModal()}>
	<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
		<circle cx="12" cy="12" r="9" />
		<path d="M12 11v5M12 8h.01" />
	</svg>
</button>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
<dialog class="info" bind:this={dialogo} aria-labelledby={tituloId} onclick={cerrarSiEsFondo}>
	<div class="info__caja">
		<h2 class="info__titulo" id={tituloId}>{titulo}</h2>
		<div class="info__texto">{@render children?.()}</div>
		<div class="info__acciones">
			<Boton variante="primario" onclick={() => dialogo?.close()}>Entendido</Boton>
		</div>
	</div>
</dialog>

<style>
	.info__boton {
		display: grid;
		place-items: center;
		flex: none;
		width: 2.25rem;
		height: 2.25rem;
		padding: 0;
		border: 0;
		border-radius: 50%;
		background: none;
		color: var(--tinta-suave);
		cursor: pointer;
	}

	.info__boton:hover {
		color: var(--marca);
	}

	.info__boton svg {
		width: 1.35rem;
		height: 1.35rem;
	}

	.info {
		width: min(28rem, calc(100vw - 2rem));
		max-width: none;
		padding: 0;
		border: 0;
		border-radius: var(--radio-lg);
		background: var(--superficie);
		color: var(--tinta);
		box-shadow: 0 24px 60px rgba(31, 21, 18, 0.24);
	}

	.info::backdrop {
		background: rgba(31, 21, 18, 0.5);
	}

	.info__caja {
		display: grid;
		gap: var(--e-3);
		padding: var(--e-5);
	}

	.info__titulo {
		margin: 0;
		font-size: var(--texto-lg, 1.125rem);
	}

	.info__texto {
		line-height: 1.5;
	}

	.info__texto :global(ul) {
		margin: var(--e-2) 0 0;
		padding-left: var(--e-4);
	}

	.info__texto :global(li + li) {
		margin-top: var(--e-1);
	}

	.info__acciones {
		display: flex;
		justify-content: flex-end;
	}
</style>
