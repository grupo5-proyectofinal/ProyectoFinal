<script>
	// Primitiva Campo: dueña de la etiqueta, ayuda, error y del wiring ARIA.
	// El caller suelta el control en el slot y solo esparce `{...controlProps}`
	// sobre el input: no escribe `aria-describedby` ni `aria-invalid` a mano.
	let { id, etiqueta, ayuda, error, requerido = false, children } = $props();

	const descrito = $derived(
		[ayuda ? `${id}-ayuda` : null, error ? `${id}-error` : null].filter(Boolean).join(' ') ||
			undefined
	);
	const invalid = $derived(error ? true : undefined);
</script>

<div class="ui-campo">
	<label class="ui-campo__etiqueta" for={id}>
		{etiqueta}
		{#if requerido}<span class="ui-campo__requerido" aria-hidden="true"> *</span>{/if}
	</label>
	{@render children({ 'aria-describedby': descrito, 'aria-invalid': invalid })}
	{#if ayuda}<p id={`${id}-ayuda`} class="ui-campo__ayuda">{ayuda}</p>{/if}
	{#if error}<p id={`${id}-error`} class="ui-campo__error">{error}</p>{/if}
</div>

<style>
	.ui-campo {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		margin-bottom: var(--e-4);
	}

	.ui-campo__etiqueta {
		font-size: var(--texto-sm);
		font-weight: 600;
		color: var(--tinta);
	}

	.ui-campo__requerido {
		color: var(--marca);
	}

	.ui-campo__ayuda {
		margin: 0;
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
	}

	.ui-campo__error {
		margin: 0;
		font-size: var(--texto-xs);
		font-weight: 500;
		color: var(--peligro);
	}
</style>
