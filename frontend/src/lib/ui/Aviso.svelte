<script>
	// Primitiva Aviso: mensaje de estado/error. El rol ARIA lo decide la variante.
	let { variante = 'info', class: clase = '', children, ...rest } = $props();

	const rol = $derived(variante === 'error' ? 'alert' : 'status');
</script>

<div class="ui-aviso ui-aviso--{variante} {clase}" role={rol} {...rest}>
	{@render children()}
</div>

<style>
	.ui-aviso {
		display: flex;
		align-items: flex-start;
		gap: var(--e-3);
		padding: 0.75rem 0.9rem;
		border: 1px solid;
		border-radius: var(--radio-sm);
		font-size: var(--texto-sm);
		line-height: 1.45;
	}

	.ui-aviso--exito {
		background: var(--exito-suave);
		border-color: var(--borde-exito);
		color: var(--texto-exito);
	}

	.ui-aviso--error {
		background: var(--peligro-suave);
		border-color: var(--borde-peligro);
		color: var(--texto-peligro);
	}

	.ui-aviso--aviso {
		background: var(--alerta-suave);
		border-color: var(--borde-alerta);
		color: var(--texto-alerta);
	}

	.ui-aviso--info {
		background: var(--info-suave);
		border-color: var(--borde-info);
		color: var(--texto-info);
	}
</style>
