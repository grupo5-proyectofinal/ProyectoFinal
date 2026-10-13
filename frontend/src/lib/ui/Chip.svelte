<script>
	// Primitiva Chip: etiqueta/filtro cliqueable con estado activo.
	let { activo = false, onclick, class: clase = '', children, ...rest } = $props();
</script>

<button
	class="ui-chip{activo ? ' ui-chip--activo' : ''} {clase}"
	type="button"
	aria-pressed={activo}
	{onclick}
	{...rest}
>
	{@render children()}
</button>

<style>
	.ui-chip {
		display: inline-flex;
		align-items: center;
		min-height: 36px;
		padding: 0.4rem 0.85rem;
		border: 1px solid var(--linea-fuerte);
		border-radius: var(--radio-full);
		background: var(--superficie);
		color: var(--tinta);
		font-family: inherit;
		font-size: var(--texto-sm);
		font-weight: 500;
		cursor: pointer;
		transition:
			border-color var(--transicion),
			background-color var(--transicion),
			color var(--transicion);
	}

	.ui-chip:hover {
		border-color: var(--marca);
		background: var(--melocoton);
		color: var(--marca-fuerte);
	}

	.ui-chip--activo {
		border-color: var(--marca);
		background: var(--melocoton);
		color: var(--marca-fuerte);
		font-weight: 600;
	}
</style>
