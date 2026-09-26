<script>
	import { resolve } from '$app/paths';
	import { api } from '$lib/api.js';
	import PoolCard from '$lib/PoolCard.svelte';

	let pools = $state([]);
	let cargando = $state(true);

	$effect(() => {
		api('/pools/mios/')
			.then((r) => (pools = r.results))
			.catch(() => {})
			.finally(() => (cargando = false));
	});
</script>

<h1>Mis Pools</h1>
{#if cargando}
	<p class="muted">Cargando…</p>
{:else if pools.length}
	<div class="grid">
		{#each pools as pool (pool.id)}
			<PoolCard {pool} />
		{/each}
	</div>
{:else}
	<p class="muted">
		Todavía no creaste ningún pool. <a href={resolve('/pools/nuevo')}>Creá uno</a>.
	</p>
{/if}
