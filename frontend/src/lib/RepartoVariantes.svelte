<script>
	// Objetivo opcional por combinación de variantes. El backend valida que la
	// suma no supere la cantidad total y que las reservas no lo excedan.
	import { combinaciones, repartoDesdeMapa } from '$lib/variantes.js';

	let {
		variantes = [],
		reparto = $bindable({}),
		cantidadTotal = null,
		bloqueado = false,
		error = ''
	} = $props();

	const combos = $derived(combinaciones(variantes));
	const filas = $derived(repartoDesdeMapa(reparto, variantes));
	const asignadas = $derived(filas.reduce((suma, fila) => suma + fila.cantidad, 0));
	const excedido = $derived(cantidadTotal !== null && asignadas > Number(cantidadTotal));

	function cambiar(clave, valor) {
		reparto = { ...reparto, [clave]: valor };
	}
</script>

{#if combos.length}
	<input type="hidden" name="reparto" value={JSON.stringify(filas)} />
	<fieldset class="reparto" aria-describedby="reparto-ayuda">
		<legend class="reparto__titulo">Cupo por variante (opcional)</legend>
		<p class="reparto__ayuda" id="reparto-ayuda">
			Cuántas unidades querés asegurar de cada combinación. Si dejás el resto en blanco, esas
			unidades no tienen cupo propio y se controlan con el total del pool.
		</p>
		<div class="reparto__grilla">
			{#each combos as combo (combo.clave)}
				<label class="reparto__campo">
					<span class="reparto__etiqueta">{combo.etiqueta}</span>
					<input
						type="number"
						inputmode="numeric"
						min="0"
						placeholder="—"
						value={reparto[combo.clave] ?? ''}
						disabled={bloqueado}
						oninput={(e) => cambiar(combo.clave, e.currentTarget.value)}
					/>
				</label>
			{/each}
		</div>
		<p class="reparto__total" class:reparto__total--error={excedido} role={excedido ? 'alert' : undefined}>
			Asignadas: <strong>{asignadas}</strong>
			{#if cantidadTotal !== null}de {cantidadTotal}{/if}
			{#if excedido}· El reparto no puede superar la cantidad total.{/if}
		</p>
		{#if error}<p class="reparto__error" role="alert">{error}</p>{/if}
	</fieldset>
{/if}

<style>
	.reparto {
		display: grid;
		gap: var(--e-2);
		margin: var(--e-4) 0 0;
		padding: var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--crema);
	}

	.reparto__titulo {
		padding: 0;
		font-size: var(--texto-sm);
		font-weight: 700;
		color: var(--tinta);
	}

	.reparto__ayuda {
		margin: 0;
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
	}

	.reparto__grilla {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
		gap: var(--e-3);
	}

	.reparto__campo {
		display: grid;
		gap: var(--e-1);
	}

	.reparto__etiqueta {
		font-size: var(--texto-xs);
		font-weight: 600;
		color: var(--tinta-suave);
	}

	.reparto__total {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.reparto__total--error,
	.reparto__error {
		color: var(--peligro);
	}

	.reparto__error {
		margin: 0;
		font-size: var(--texto-xs);
		font-weight: 600;
	}
</style>
