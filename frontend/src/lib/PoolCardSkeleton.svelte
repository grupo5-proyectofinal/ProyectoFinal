<script>
	import Tarjeta from '$lib/ui/Tarjeta.svelte';
</script>

<Tarjeta class="pool-skeleton" aria-hidden="true">
	<div class="pool-skeleton__contenido">
		<div class="skeleton pool-skeleton__media"></div>
		<div class="pool-skeleton__cuerpo">
			<div class="skeleton pool-skeleton__linea pool-skeleton__linea--corta"></div>
			<div class="skeleton pool-skeleton__titulo"></div>
			<div class="skeleton pool-skeleton__linea"></div>
			<div class="skeleton pool-skeleton__barra"></div>
			<div class="skeleton pool-skeleton__accion"></div>
		</div>
	</div>
</Tarjeta>

<style>
	.pool-skeleton__contenido {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.pool-skeleton__media {
		aspect-ratio: 16 / 10;
		margin: var(--e-3) var(--e-3) 0;
		border-radius: var(--radio-sm);
	}

	.pool-skeleton__cuerpo {
		display: flex;
		flex: 1;
		flex-direction: column;
		gap: var(--e-2);
		padding: var(--e-3);
	}

	.pool-skeleton__titulo {
		height: 1.1rem;
		width: 80%;
	}

	.pool-skeleton__linea {
		height: 0.8rem;
		width: 100%;
	}

	.pool-skeleton__linea--corta {
		width: 45%;
	}

	.pool-skeleton__barra {
		height: 8px;
		border-radius: var(--radio-full);
	}

	.pool-skeleton__accion {
		height: 44px;
		margin-top: auto;
		border-radius: var(--radio-sm);
	}
</style>
