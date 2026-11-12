<script>
	// Evidencia de costo final para quien todavía no se unió: el comparador del
	// pool es público y read-only. En el lateral se muestra un resumen compacto;
	// la tabla completa no entra en el ancho de la compra.
	import { api } from '$lib/api.js';
	import { moneda } from '$lib/formato.js';

	let { poolId, cantidad = 1 } = $props();

	let comparacion = $state(null);

	$effect(() => {
		const id = poolId;
		api(`/comparaciones/de-pool/${id}/`, { auth: false })
			.then((r) => (comparacion = r))
			.catch(() => (comparacion = null));
	});

	const ofertas = $derived(
		[...(comparacion?.ofertas ?? [])].sort((a, b) => {
			const totalA = Number(a.costo?.total);
			const totalB = Number(b.costo?.total);
			if (!Number.isFinite(totalA)) return 1;
			if (!Number.isFinite(totalB)) return -1;
			return totalA - totalB;
		})
	);
	const mejorTotal = $derived(
		Number.isFinite(Number(ofertas[0]?.costo?.total)) ? Number(ofertas[0].costo.total) : null
	);
	const unidades = $derived(
		Number(comparacion?.cantidad ?? cantidad) === 1
			? '1 unidad'
			: `${comparacion?.cantidad ?? cantidad} unidades`
	);
</script>

{#if comparacion && ofertas.length}
	<div class="resumen-costo">
		<p class="resumen-costo__titulo">Costo final comparado</p>
		{#if mejorTotal !== null}
			<p class="resumen-costo__dato">
				Mejor total: <strong>{moneda(mejorTotal)}</strong> para {unidades}.
			</p>
		{/if}
		<ul class="resumen-costo__lista">
			{#each ofertas.slice(0, 3) as oferta (oferta.id)}
				<li>
					<span class="resumen-costo__tienda">{oferta.tienda}</span>
					<span class="resumen-costo__precio">
						{#if oferta.costo?.total != null}
							<strong>{moneda(oferta.costo.total)}</strong>
							<small>{moneda(oferta.costo.por_unidad)} por unidad</small>
						{:else}
							<span>Sin convertir</span>
						{/if}
					</span>
				</li>
			{/each}
		</ul>
		<p class="resumen-costo__nota">
			Incluye envío, impuestos y aduana estimada. Los integrantes del pool ven el desglose
			completo.
		</p>
	</div>
{/if}

<style>
	.resumen-costo {
		margin-top: var(--e-4);
		padding-top: var(--e-4);
		border-top: 1px solid var(--linea);
	}

	.resumen-costo__titulo {
		margin: 0;
		font-size: var(--texto-sm);
		font-weight: 700;
		color: var(--tinta);
	}

	.resumen-costo__dato {
		margin: var(--e-1) 0 var(--e-2);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.resumen-costo__lista {
		display: grid;
		gap: var(--e-1);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.resumen-costo__lista li {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--e-3);
		padding: var(--e-2) 0;
		border-bottom: 1px solid var(--linea);
		font-size: var(--texto-sm);
	}

	.resumen-costo__lista li:last-child {
		border-bottom: 0;
	}

	.resumen-costo__tienda {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: var(--tinta);
	}

	.resumen-costo__precio {
		display: flex;
		flex: none;
		flex-direction: column;
		align-items: flex-end;
		gap: 1px;
		font-variant-numeric: tabular-nums;
	}

	.resumen-costo__precio small {
		color: var(--tinta-tenue);
		font-size: var(--texto-xs);
	}

	.resumen-costo__nota {
		margin: var(--e-2) 0 0;
		color: var(--tinta-tenue);
		font-size: var(--texto-xs);
	}
</style>
