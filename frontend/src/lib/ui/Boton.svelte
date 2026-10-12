<script>
	// Primitiva Boton: un componente cubre enlace (<a>) y botón (<button>).
	// Si recibe `href` renderiza un enlace; si no, un botón. El caller no elige el tag.
	let {
		variante = 'primario',
		tamano,
		bloque = false,
		href,
		tipo = 'button',
		disabled = false,
		onclick,
		class: clase = '',
		children,
		...rest
	} = $props();

	const claseBase = $derived(
		[
			'ui-boton',
			`ui-boton--${variante}`,
			tamano ? `ui-boton--${tamano}` : '',
			bloque ? 'ui-boton--bloque' : '',
			clase
		]
			.filter(Boolean)
			.join(' ')
	);
</script>

{#if href}
	<a class={claseBase} {href} aria-disabled={disabled ? 'true' : undefined} {onclick} {...rest}>
		{@render children()}
	</a>
{:else}
	<button class={claseBase} type={tipo} {disabled} {onclick} {...rest}>
		{@render children()}
	</button>
{/if}

<style>
	.ui-boton {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5em;
		min-height: var(--alto-tap);
		padding: 0.55rem 1.1rem;
		border: 1px solid transparent;
		border-radius: var(--radio-sm);
		background: transparent;
		color: var(--tinta);
		font-family: inherit;
		font-size: var(--texto-sm);
		font-weight: 700;
		line-height: 1.2;
		letter-spacing: 0.005em;
		text-decoration: none;
		white-space: nowrap;
		cursor: pointer;
		transition:
			background-color var(--transicion),
			border-color var(--transicion),
			color var(--transicion);
	}

	.ui-boton:hover {
		text-decoration: none;
	}

	.ui-boton:disabled,
	.ui-boton[aria-disabled='true'] {
		opacity: 0.55;
		cursor: not-allowed;
	}

	.ui-boton--primario {
		background: var(--marca);
		border-color: var(--marca);
		color: #fff;
	}

	.ui-boton--primario:hover:not(:disabled):not([aria-disabled='true']) {
		background: var(--marca-fuerte);
		border-color: var(--marca-fuerte);
		color: #fff;
	}

	.ui-boton--secundario {
		background: var(--superficie);
		border-color: var(--linea-fuerte);
		color: var(--tinta);
	}

	.ui-boton--secundario:hover:not(:disabled):not([aria-disabled='true']) {
		border-color: var(--marca);
		color: var(--marca-fuerte);
		background: var(--melocoton);
	}

	.ui-boton--ghost {
		background: transparent;
		border-color: transparent;
		color: var(--tinta-suave);
	}

	.ui-boton--ghost:hover:not(:disabled):not([aria-disabled='true']) {
		background: var(--crema);
		color: var(--tinta);
	}

	.ui-boton--peligro-suave {
		background: transparent;
		border-color: var(--borde-peligro-fuerte);
		color: var(--peligro);
	}

	.ui-boton--peligro-suave:hover:not(:disabled):not([aria-disabled='true']) {
		background: var(--peligro-suave);
		color: var(--peligro-fuerte);
	}

	.ui-boton--sm {
		min-height: 38px;
		padding: 0.35rem 0.7rem;
		font-size: var(--texto-xs);
	}

	.ui-boton--lg {
		min-height: 52px;
		padding: 0.7rem 1.5rem;
		font-size: var(--texto-base);
	}

	.ui-boton--bloque {
		width: 100%;
	}
</style>
