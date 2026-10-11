<script>
	// Marca de PoolShop: dos círculos que se solapan (la unión de varias partes en un mismo pool).
	// Los trazos usan currentColor y el token --acento, así el isotipo hereda el color del
	// contexto y la paleta sigue viva en app.css.
	let { conNombre = true, class: clase = '', ...rest } = $props();
</script>

<span class="marca {clase}" {...rest}>
	<svg
		class="marca__isotipo"
		viewBox="0 0 32 32"
		role={conNombre ? undefined : 'img'}
		aria-hidden={conNombre ? 'true' : undefined}
		aria-label={conNombre ? undefined : 'PoolShop'}
	>
		<circle
			class="marca__aro"
			cx="13"
			cy="16"
			r="5.5"
			fill="none"
			stroke="currentColor"
			stroke-width="2.5"
			stroke-opacity="0.55"
		/>
		<circle cx="20" cy="16" r="5.5" fill="none" stroke="var(--acento)" stroke-width="2.5" />
	</svg>
	{#if conNombre}<span class="marca__nombre">PoolShop</span>{/if}
</span>

<style>
	.marca {
		display: inline-flex;
		align-items: center;
		gap: 0.45em;
		font-family: var(--fuente-display);
		font-size: 1.35rem;
		font-weight: 600;
		letter-spacing: -0.025em;
		line-height: 1;
		color: var(--tinta);
	}

	.marca__isotipo {
		flex: none;
		width: 1.05em;
		height: 1.05em;
	}

	/* El punto azul del wordmark replica el acento del logotipo de texto original. */
	.marca__nombre::after {
		content: '.';
		color: var(--acento);
	}

	/* Variantes por contexto: el consumidor pasa la clase y el span la lleva junto al
	   hash propio, así el selector compilado matchea siempre. Van después de .marca
	   (misma especificidad) para ganar por orden dentro de la hoja del componente. */
	.marca--cabecera {
		font-size: 1.3rem;
	}

	.marca--pie {
		font-size: 1.2rem;
	}

	/* Marca del panel de auth: encabeza el editorial, más grande y con aire. */
	.auth__logo {
		margin-bottom: var(--e-5);
		font-size: 2.75rem;
	}

	/* En pantallas chicas queda solo el isotipo (el wordmark ya está en el título). */
	@media (max-width: 520px) {
		.marca--cabecera .marca__nombre {
			display: none;
		}
	}
</style>
