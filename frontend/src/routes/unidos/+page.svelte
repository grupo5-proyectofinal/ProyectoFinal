<script>
	import { resolve } from '$app/paths';
	import { api } from '$lib/api.js';
	import PoolCard from '$lib/PoolCard.svelte';
	import PoolCardSkeleton from '$lib/PoolCardSkeleton.svelte';

	let pools = $state([]);
	let cargando = $state(true);
	let error = $state(false);

	$effect(() => {
		api('/pools/unidos/')
			.then((r) => (pools = r.results))
			.catch(() => (error = true))
			.finally(() => (cargando = false));
	});
</script>

<svelte:head>
	<title>Unidos — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Unidos</h1>
		<p>Los pools en los que reservaste una cantidad.</p>
	</div>
	<div class="cabecera-pagina__acciones">
		<a class="btn btn--secundario" href={resolve('/pools')}>Ver pools</a>
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
		No se pudieron cargar los pools en los que participás. Recargá la página para volver a
		intentar.
	</div>
{:else if pools.length}
	<h2 class="sr-only">Pools en los que participás</h2>
	<div class="grilla-pools">
		{#each pools as pool (pool.id)}
			<PoolCard {pool} contexto="unidos" />
		{/each}
	</div>
{:else}
	<div class="vacio">
		<h3>No te uniste a ningún pool todavía</h3>
		<p>Explorá las compras abiertas y reservá la cantidad que necesites.</p>
		<a class="btn btn--primario" href={resolve('/pools')}>Ver pools</a>
	</div>
{/if}
