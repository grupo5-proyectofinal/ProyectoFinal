<script>
	import { resolve } from '$app/paths';
	import { api } from '$lib/api.js';
	import PoolCard from '$lib/PoolCard.svelte';
	import PoolCardSkeleton from '$lib/PoolCardSkeleton.svelte';

	let pools = $state([]);
	let cargando = $state(true);
	let error = $state(false);

	$effect(() => {
		api('/pools/mios/')
			.then((r) => (pools = r.results))
			.catch(() => (error = true))
			.finally(() => (cargando = false));
	});
</script>

<svelte:head>
	<title>Mis Pools — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Mis Pools</h1>
		<p>Las compras colectivas que organizás vos.</p>
	</div>
	<div class="cabecera-pagina__acciones">
		<a class="btn btn--primario" href={resolve('/pools/nuevo')}>Crear pool</a>
	</div>
</div>

{#if cargando}
	<p class="sr-only" role="status">Cargando pools…</p>
	<div class="grilla-pools" aria-hidden="true">
		{#each [0, 1, 2] as i (i)}
			<PoolCardSkeleton />
		{/each}
	</div>
{:else if error}
	<div class="alerta alerta--error" role="alert">
		No se pudieron cargar tus pools. Recargá la página para volver a intentar.
	</div>
{:else if pools.length}
	<h2 class="sr-only">Pools que organizás</h2>
	<div class="grilla-pools">
		{#each pools as pool (pool.id)}
			<PoolCard {pool} contexto="mis-pools" />
		{/each}
	</div>
{:else}
	<div class="vacio">
		<h3>Todavía no creaste ningún pool</h3>
		<p>Armá tu primera compra colectiva y compartila con quien quieras.</p>
		<a class="btn btn--primario" href={resolve('/pools/nuevo')}>Crear pool</a>
	</div>
{/if}
