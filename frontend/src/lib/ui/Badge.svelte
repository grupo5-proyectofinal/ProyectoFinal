<script>
	// Primitiva Badge: etiqueta de estado (pool, usuario, descuento).
	// `variante` mapea a la sub-paleta de estados definida en app.css.
	let { variante = 'neutro', class: clase = '', children, ...rest } = $props();
</script>

<span class="ui-badge ui-badge--{variante} {clase}" {...rest}>
	{@render children()}
</span>

<style>
	.ui-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.4em;
		padding: 0.15rem 0.6rem;
		border: 1px solid transparent;
		border-radius: var(--radio-full);
		font-size: var(--texto-xs);
		font-weight: 600;
		line-height: 1.6;
		letter-spacing: 0.01em;
		white-space: nowrap;
	}

	/* Estados del pool */
	.ui-badge--abierto {
		background: var(--exito-suave);
		color: var(--texto-exito);
		border-color: var(--borde-exito);
	}

	.ui-badge--listo {
		background: var(--info-suave);
		color: var(--texto-info);
		border-color: var(--borde-info);
	}

	.ui-badge--en_curso {
		background: var(--alerta-suave);
		color: var(--texto-alerta);
		border-color: var(--borde-alerta);
	}

	.ui-badge--finalizado {
		background: var(--crema);
		color: var(--tinta-suave);
		border-color: var(--linea);
	}

	.ui-badge--cancelado {
		background: var(--peligro-suave);
		color: var(--texto-peligro);
		border-color: var(--borde-peligro);
	}

	/* Usuarios (backoffice) */
	.ui-badge--activo {
		background: var(--exito-suave);
		color: var(--texto-exito);
		border-color: var(--borde-exito);
	}

	.ui-badge--inactivo {
		background: var(--crema);
		color: var(--tinta-tenue);
		border-color: var(--linea);
	}

	.ui-badge--staff {
		background: var(--info-suave);
		color: var(--texto-info);
		border-color: var(--borde-info);
	}

	/* Promociones / marca */
	.ui-badge--descuento {
		background: var(--marca);
		color: #fff;
	}

	.ui-badge--neutro {
		background: var(--crema);
		color: var(--tinta-suave);
		border-color: var(--linea);
	}
</style>
