<script>
	import { resolve } from '$app/paths';
	import { api } from '$lib/api.js';
	import PoolCard from '$lib/PoolCard.svelte';

	let pools = $state([]);
	let cargando = $state(true);

	$effect(() => {
		api('/pools/unidos/')
			.then((r) => (pools = r.results))
			.catch(() => {})
			.finally(() => (cargando = false));
	});
</script>

<h1>Unidos</h1>
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
		No te uniste a ningún pool todavía. <a href={resolve('/pools')}>Ver pools</a>.
	</p>
{/if}
