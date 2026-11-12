<script>
	// Stepper compartido por Crear pool y Editar pool. El padre decide qué
	// significa "ir" a un paso (validar, enfocar, hacer scroll).
	let { pasos = [], paso = 0, onir, etiqueta = 'Pasos del formulario' } = $props();
</script>

<nav class="pasos" aria-label={etiqueta}>
	<ol class="pasos__lista">
		{#each pasos as item, indice (item.id)}
			<li>
				<button
					type="button"
					class="pasos__item"
					class:activo={paso === indice}
					class:hecho={paso > indice}
					aria-current={paso === indice ? 'step' : undefined}
					disabled={indice > paso}
					onclick={() => onir?.(indice)}
				>
					<span class="pasos__numero" aria-hidden="true">{indice + 1}</span>
					<span class="pasos__nombre">{item.titulo}</span>
				</button>
			</li>
		{/each}
	</ol>
	<p class="pasos__cuenta">Paso {paso + 1} de {pasos.length}</p>
</nav>

<style>
	.pasos {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-3);
		margin-bottom: var(--e-5);
	}

	.pasos__lista {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.pasos__item {
		display: inline-flex;
		align-items: center;
		gap: var(--e-2);
		min-height: var(--alto-tap);
		padding: 0 0.85rem;
		border: 1px solid var(--linea-fuerte);
		border-radius: var(--radio-full);
		background: var(--superficie);
		color: var(--tinta-suave);
		font: inherit;
		font-size: var(--texto-sm);
		font-weight: 600;
		cursor: pointer;
	}

	.pasos__item:disabled {
		opacity: 0.6;
		cursor: default;
	}

	.pasos__item.activo {
		border-color: var(--marca);
		background: var(--melocoton);
		color: var(--marca-fuerte);
	}

	.pasos__item.hecho {
		color: var(--tinta);
	}

	.pasos__numero {
		display: grid;
		place-items: center;
		width: 1.4rem;
		height: 1.4rem;
		border-radius: 50%;
		background: var(--crema);
		color: var(--tinta-suave);
		font-size: var(--texto-xs);
		font-variant-numeric: tabular-nums;
	}

	.pasos__item.activo .pasos__numero {
		background: var(--marca);
		color: #fff;
	}

	.pasos__item.hecho .pasos__numero {
		background: var(--exito-suave);
		color: var(--exito);
	}

	.pasos__cuenta {
		margin: 0;
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
		font-weight: 600;
	}
</style>
