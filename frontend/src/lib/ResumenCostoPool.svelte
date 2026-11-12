<script>
	// Evidencia de costo final para quien todavía no se unió: el comparador del
	// pool es público y read-only. Si no hay comparación, no ocupa espacio.
	import { api } from '$lib/api.js';
	import { moneda } from '$lib/formato.js';
	import PanelComparador from '$lib/PanelComparador.svelte';

	let { poolId, cantidad = 1 } = $props();

	let comparacion = $state(null);
	let cargando = $state(true);

	$effect(() => {
		const id = poolId;
		cargando = true;
		api(`/comparaciones/de-pool/${id}/`, { auth: false })
			.then((r) => (comparacion = r))
			.catch(() => (comparacion = null))
			.finally(() => (cargando = false));
	});

	const mejorTotal = $derived.by(() => {
		const totales = (comparacion?.ofertas ?? [])
			.map((oferta) => Number(oferta.costo?.total))
			.filter((total) => Number.isFinite(total) && total > 0);
		return totales.length ? Math.min(...totales) : null;
	});

	const unidades = $derived(
		Number(comparacion?.cantidad ?? cantidad) === 1 ? '1 unidad' : `${comparacion?.cantidad ?? cantidad} unidades`
	);
</script>

{#if comparacion && (comparacion.ofertas?.length ?? 0) > 0}
	<div class="resumen-costo">
		<p class="resumen-costo__titulo">Costo final comparado</p>
		{#if mejorTotal !== null}
			<p class="resumen-costo__dato">
				Mejor total: <strong>{moneda(mejorTotal)}</strong> para {unidades}.
			</p>
		{/if}
		<details class="resumen-costo__detalle">
			<summary>Ver comparación de costos</summary>
			<PanelComparador {comparacion} nivel={3} />
		</details>
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

	.resumen-costo__detalle summary {
		display: flex;
		align-items: center;
		min-height: var(--alto-tap);
		color: var(--marca-fuerte);
		font-size: var(--texto-sm);
		font-weight: 600;
		cursor: pointer;
	}

	.resumen-costo__detalle :global(.comparador) {
		margin-top: var(--e-3);
	}
</style>
