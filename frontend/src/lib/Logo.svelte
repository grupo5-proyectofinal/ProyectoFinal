<script>
	// Marca del mockup: isotipo "P" en caja redondeada roja + wordmark "Pool" (tinta)
	// y "Shop" (naranja). Los colores heredan de tokens; el contexto solo cambia el tamaño.
	let { conNombre = true, class: clase = '', ...rest } = $props();
</script>

<span class="marca {clase}" {...rest}>
	<span
		class="marca__isotipo"
		role={conNombre ? undefined : 'img'}
		aria-hidden={conNombre ? 'true' : undefined}
		aria-label={conNombre ? undefined : 'PoolShop'}
	>
		<svg
			viewBox="0 0 24 24"
			fill="none"
			stroke="var(--marca)"
			stroke-width="3"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<path d="M7 21V4h7a5 5 0 0 1 0 10H7" />
		</svg>
	</span>
	{#if conNombre}<span class="marca__nombre">Pool<span class="marca__shop">Shop</span></span>{/if}
</span>

<style>
	.marca {
		display: inline-flex;
		align-items: center;
		gap: 0.45em;
		font-family: var(--fuente-display);
		font-weight: 800;
		font-size: 1.5rem;
		letter-spacing: -0.02em;
		line-height: 1;
		color: var(--tinta);
	}

	.marca__isotipo {
		flex: none;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.42em;
		height: 1.42em;
		border: 2.5px solid var(--marca);
		border-radius: 0.42em;
		box-sizing: border-box;
	}

	.marca__isotipo svg {
		width: 0.66em;
		height: 0.66em;
	}

	.marca__shop {
		color: var(--acento-naranja);
	}

	/* Variantes por contexto (el consumidor pasa la clase). */
	.marca--cabecera {
		font-size: 1.5rem;
	}

	.marca--pie {
		font-size: 1.2rem;
	}

	.auth__logo {
		margin-bottom: var(--e-5);
		font-size: 2.75rem;
	}
</style>
