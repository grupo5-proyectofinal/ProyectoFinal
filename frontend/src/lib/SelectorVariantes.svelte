<script>
	// Al unirse (o cambiar la reserva) en un pool con variantes: filas de
	// "Talle · Color · cantidad". La cantidad reservada es la suma de las filas.
	import { filaVacia, sumaFilas } from '$lib/variantes.js';

	let { variantes = [], filas = $bindable([]), maximo = null, error = '' } = $props();

	const total = $derived(sumaFilas(filas));

	function agregar() {
		filas = [...filas, filaVacia(variantes, 1)];
	}

	function quitar(indice) {
		filas = filas.filter((_, i) => i !== indice);
	}

	function cambiar(indice, nombre, valor) {
		filas = filas.map((fila, i) =>
			i === indice ? { ...fila, atributos: { ...fila.atributos, [nombre]: valor } } : fila
		);
	}

	function cambiarCantidad(indice, valor) {
		filas = filas.map((fila, i) => (i === indice ? { ...fila, cantidad: valor } : fila));
	}
</script>

<fieldset class="filas" aria-describedby={error ? 'variantes-error' : undefined}>
	<legend class="filas__titulo">Qué querés pedir</legend>
	{#each filas as fila, i (i)}
		<div class="fila">
			{#each variantes as variante (variante.nombre)}
				<label class="fila__campo">
					<span class="fila__rotulo">{variante.nombre}</span>
					<select
						id={`variante-${i}-${variante.nombre}`}
						value={fila.atributos[variante.nombre]}
						onchange={(e) => cambiar(i, variante.nombre, e.currentTarget.value)}
					>
						{#each variante.opciones as opcion (opcion)}
							<option value={opcion}>{opcion}</option>
						{/each}
					</select>
				</label>
			{/each}
			<label class="fila__campo fila__campo--cantidad">
				<span class="fila__rotulo">Cantidad</span>
				<input
					id={`variante-${i}-cantidad`}
					type="number"
					inputmode="numeric"
					min="1"
					value={fila.cantidad}
					oninput={(e) => cambiarCantidad(i, e.currentTarget.value)}
				/>
			</label>
			{#if filas.length > 1}
				<button
					type="button"
					class="fila__quitar"
					aria-label={`Quitar la variante ${i + 1}`}
					onclick={() => quitar(i)}
				>
					✕
				</button>
			{/if}
		</div>
	{/each}
	<div class="filas__pie">
		<button type="button" class="filas__agregar" onclick={agregar}>+ Agregar otra variante</button>
		<span class="filas__total">
			Total: <b>{total} {total === 1 ? 'unidad' : 'unidades'}</b>
			{#if maximo !== null}<span class="filas__max">(hasta {maximo})</span>{/if}
		</span>
	</div>
	{#if error}
		<p id="variantes-error" class="filas__error" role="alert">{error}</p>
	{/if}
</fieldset>

<style>
	.filas {
		display: grid;
		gap: var(--e-2);
		margin: 0;
		padding: 0;
		border: 0;
	}

	.filas__titulo {
		margin-bottom: var(--e-1);
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.fila {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
		align-items: end;
		padding: var(--e-2);
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
	}

	.fila__campo {
		display: grid;
		flex: 1 1 5.5rem;
		gap: 2px;
	}

	.fila__campo--cantidad {
		flex: 0 1 5rem;
	}

	.fila__rotulo {
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.fila__quitar {
		align-self: center;
		border: 0;
		background: none;
		padding: var(--e-1);
		color: var(--tinta-tenue);
		cursor: pointer;
	}

	.fila__quitar:hover {
		color: var(--peligro);
	}

	.filas__pie {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: var(--e-2);
		font-size: var(--texto-sm);
	}

	.filas__agregar {
		border: 0;
		background: none;
		padding: 0;
		font: inherit;
		font-weight: 600;
		color: var(--marca-fuerte);
		cursor: pointer;
	}

	.filas__max {
		color: var(--tinta-tenue);
	}

	.filas__error {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--texto-peligro);
	}
</style>
