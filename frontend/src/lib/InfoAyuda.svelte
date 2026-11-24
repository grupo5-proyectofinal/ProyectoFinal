<script>
	// Ícono "i" que explica algo al tocarlo, pasarle el mouse o enfocarlo con el teclado.
	let { texto, etiqueta = 'Más información', id } = $props();

	let abierto = $state(false);
</script>

<span
	class="info"
	onmouseenter={() => (abierto = true)}
	onmouseleave={() => (abierto = false)}
>
	<button
		type="button"
		class="info__boton"
		aria-label={etiqueta}
		aria-expanded={abierto}
		aria-describedby={abierto ? id : undefined}
		onclick={() => (abierto = !abierto)}
		onblur={() => (abierto = false)}
		onkeydown={(event) => event.key === 'Escape' && (abierto = false)}
	>
		<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
			<circle cx="12" cy="12" r="9" />
			<path d="M12 11v5M12 8h.01" />
		</svg>
	</button>
	{#if abierto}
		<span class="info__texto" {id} role="tooltip">{texto}</span>
	{/if}
</span>

<style>
	.info {
		position: relative;
		display: inline-flex;
	}

	.info__boton {
		display: grid;
		place-items: center;
		width: 1.75rem;
		height: 1.75rem;
		padding: 0;
		border: 0;
		border-radius: 50%;
		background: none;
		color: var(--tinta-suave);
		cursor: help;
	}

	.info__boton:hover,
	.info__boton[aria-expanded='true'] {
		color: var(--marca);
	}

	.info__boton svg {
		width: 1.25rem;
		height: 1.25rem;
	}

	.info__texto {
		position: absolute;
		z-index: 30;
		bottom: calc(100% + 6px);
		right: 0;
		width: min(20rem, 80vw);
		padding: var(--e-3);
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
		background: var(--superficie);
		box-shadow: 0 8px 24px rgba(31, 21, 18, 0.18);
		color: var(--tinta);
		font-size: var(--texto-sm);
		font-weight: 400;
		line-height: 1.45;
		text-align: left;
	}
</style>
