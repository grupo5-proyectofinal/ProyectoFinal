<article class="pool-skeleton" aria-hidden="true">
	<div class="skeleton skeleton--imagen"></div>
	<div class="pool-skeleton__cuerpo">
		<div class="skeleton skeleton--linea skeleton--corta"></div>
		<div class="skeleton skeleton--titulo"></div>
		<div class="skeleton skeleton--linea"></div>
		<div class="skeleton skeleton--linea skeleton--corta"></div>
	</div>
</article>

<style>
	.pool-skeleton {
		overflow: hidden;
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--superficie);
	}

	.pool-skeleton__cuerpo {
		display: flex;
		flex-direction: column;
		gap: var(--e-3);
		padding: var(--e-4);
	}
</style>
