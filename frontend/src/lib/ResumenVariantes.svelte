<script>
	// Para el organizador: cuántas unidades de cada variante pidieron en total
	// (lo que hay que pedirle al proveedor) y la descarga en CSV.
	import { csvVariantes, resumenVariantes } from '$lib/variantes.js';
	import Boton from '$lib/ui/Boton.svelte';

	let { pool } = $props();

	const resumen = $derived(resumenVariantes(pool.miembros, pool.variantes));
	const total = $derived(resumen.reduce((suma, fila) => suma + fila.cantidad, 0));

	function descargar() {
		// BOM para que Excel abra bien los acentos.
		const blob = new Blob(['﻿', csvVariantes(resumen, pool.variantes)], {
			type: 'text/csv;charset=utf-8'
		});
		const url = URL.createObjectURL(blob);
		const enlace = document.createElement('a');
		enlace.href = url;
		enlace.download = `pedido-pool-${pool.id}.csv`;
		enlace.click();
		setTimeout(() => URL.revokeObjectURL(url), 10_000);
	}
</script>

<section class="resumen-variantes" aria-labelledby="resumen-variantes-titulo">
	<div class="resumen-variantes__cabecera">
		<h3 id="resumen-variantes-titulo">Pedido por variante</h3>
		{#if resumen.length}
			<Boton variante="secundario" tamano="sm" onclick={descargar}>Descargar CSV</Boton>
		{/if}
	</div>
	{#if resumen.length}
		<table class="resumen-variantes__tabla">
			<thead>
				<tr>
					<th scope="col">Variante</th>
					<th scope="col" class="num">Unidades</th>
				</tr>
			</thead>
			<tbody>
				{#each resumen as fila (fila.etiqueta)}
					<tr>
						<td>{fila.etiqueta}</td>
						<td class="num">{fila.cantidad}</td>
					</tr>
				{/each}
			</tbody>
			<tfoot>
				<tr>
					<th scope="row">Total de los integrantes</th>
					<td class="num">{total}</td>
				</tr>
			</tfoot>
		</table>
		<p class="resumen-variantes__nota">
			No incluye tus {pool.cantidad_creador}
			{pool.cantidad_creador === 1 ? 'unidad' : 'unidades'}: sumalas al hacer el pedido.
		</p>
	{:else}
		<p class="resumen-variantes__nota">Todavía nadie eligió variantes.</p>
	{/if}
</section>

<style>
	.resumen-variantes {
		display: grid;
		gap: var(--e-3);
		margin-top: var(--e-5);
	}

	.resumen-variantes__cabecera {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-3);
	}

	.resumen-variantes__cabecera h3 {
		margin: 0;
	}

	.resumen-variantes__tabla {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--texto-sm);
	}

	.resumen-variantes__tabla th,
	.resumen-variantes__tabla td {
		padding: 0.5rem 0.25rem;
		border-bottom: 1px solid var(--linea);
		text-align: left;
	}

	.resumen-variantes__tabla .num {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.resumen-variantes__tabla tfoot th,
	.resumen-variantes__tabla tfoot td {
		border-bottom: 0;
		font-weight: 700;
	}

	.resumen-variantes__nota {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-tenue);
	}
</style>
