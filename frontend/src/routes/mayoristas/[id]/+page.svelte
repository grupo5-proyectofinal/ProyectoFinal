<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api } from '$lib/api.js';
	import { moneda } from '$lib/formato.js';
	import PanelEnlace from '$lib/PanelEnlace.svelte';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let proveedor = $state(null);
	let error = $state('');

	$effect(() => {
		const id = page.params.id;
		api(`/proveedores/${id}/`, { auth: false })
			.then((r) => (proveedor = r))
			.catch((e) => (error = e?.status === 404 ? 'Ese mayorista no está en el directorio.' : 'No se pudo cargar.'));
	});

	const datos = $derived(
		proveedor
			? [
					['Ubicación', [proveedor.ciudad, proveedor.provincia].filter(Boolean).join(', ')],
					['Compra mínima', proveedor.compra_minima],
					['Envío', proveedor.envio],
					['Medios de pago', proveedor.medios_pago],
					['Rubros', proveedor.rubros_nombres.join(' · ')]
				].filter(([, valor]) => valor)
			: []
	);
</script>

<svelte:head>
	<title>{proveedor?.nombre ?? 'Mayorista'} — PoolShop</title>
</svelte:head>

<a class="volver" href={resolve('/mayoristas')}>← Volver a mayoristas</a>

{#if error}
	<Aviso variante="error">{error}</Aviso>
{:else if proveedor}
	<div class="cabecera-pagina">
		<div>
			<h1>{proveedor.nombre} {#if proveedor.verificado}<Badge variante="abierto">✓ Verificado</Badge>{/if}</h1>
			<p><a href={proveedor.sitio_url} target="_blank" rel="noopener noreferrer">{proveedor.dominio} ↗</a></p>
			{#if proveedor.descripcion}<p>{proveedor.descripcion}</p>{/if}
		</div>
		<div class="cabecera-pagina__acciones">
			<Boton variante="primario" href={resolve(`/pools/nuevo?enlace=${encodeURIComponent(proveedor.sitio_url)}`)}>
				Crear pool con este sitio
			</Boton>
		</div>
	</div>

	<div class="columnas">
		<div class="columnas__principal">
			{#if datos.length}
				<Tarjeta class="relleno">
					<dl class="datos">
						{#each datos as [rotulo, valor] (rotulo)}
							<div><dt>{rotulo}</dt><dd>{valor}</dd></div>
						{/each}
					</dl>
				</Tarjeta>
			{/if}
			<PanelEnlace analisis={proveedor.analisis} />
		</div>
		<aside>
			<Tarjeta class="relleno">
				<h2 class="lateral__titulo">Pools con este sitio</h2>
				<p class="lateral__dato">
					{proveedor.pools_total === 1 ? '1 pool usó' : `${proveedor.pools_total} pools usaron`} este sitio en PoolShop.
				</p>
				{#if proveedor.pools_activos.length}
					<ul class="lateral__lista">
						{#each proveedor.pools_activos as pool (pool.id)}
							<li>
								<a href={resolve(`/pools/${pool.id}`)}>{pool.titulo}</a>
								<span>{moneda(pool.precio_unitario)} c/u</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="lateral__dato">No hay pools abiertos ahora.</p>
				{/if}
			</Tarjeta>
		</aside>
	</div>
{:else}
	<p>Cargando…</p>
{/if}

<style>
	.volver {
		display: inline-block;
		margin-bottom: var(--e-4);
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.columnas {
		display: grid;
		grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
		gap: var(--e-5);
	}

	.columnas__principal {
		display: grid;
		gap: var(--e-5);
		align-content: start;
	}

	.datos {
		display: grid;
		gap: var(--e-3);
		margin: 0;
	}

	.datos dt {
		font-size: var(--texto-sm);
		color: var(--tinta-tenue);
	}

	.datos dd {
		margin: 0;
	}

	.lateral__titulo {
		margin: 0 0 var(--e-2);
		font-size: 1.1rem;
	}

	.lateral__dato {
		margin: 0 0 var(--e-2);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.lateral__lista {
		display: grid;
		gap: var(--e-2);
		margin: 0;
		padding: 0;
		list-style: none;
		font-size: var(--texto-sm);
	}

	.lateral__lista li {
		display: flex;
		justify-content: space-between;
		gap: var(--e-2);
	}

	@media (max-width: 800px) {
		.columnas {
			grid-template-columns: 1fr;
		}
	}
</style>
