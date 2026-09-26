<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api } from '$lib/api.js';
	import PoolCard from '$lib/PoolCard.svelte';
	import { session } from '$lib/session.svelte.js';

	let pools = $state([]);
	let categorias = $state([]);
	let cargando = $state(false);
	let q = $state('');

	$effect(() => {
		if (!session.access) return;
		cargar();
	});

	async function cargar() {
		cargando = true;
		try {
			const [lista, cats] = await Promise.all([
				api('/pools/', { query: { ordering: '-id' } }),
				api('/categories/')
			]);
			pools = lista.results.slice(0, 6);
			categorias = cats.results;
		} catch {
			pools = [];
		} finally {
			cargando = false;
		}
	}

	function buscar(event) {
		event.preventDefault();
		goto(resolve(q ? `/pools?q=${encodeURIComponent(q)}` : '/pools'));
	}
</script>

<section class="tarjeta">
	<h1>Comprá en grupo, pagá menos</h1>
	<p class="muted">
		PoolShop organiza compras colectivas: creás un pool, se suman vecinos y compran al por
		mayor.
	</p>
	{#if session.access}
		<form class="buscador" onsubmit={buscar}>
			<input type="search" placeholder="Buscar pools…" bind:value={q} aria-label="Buscar pools" />
			<button class="btn" type="submit">Buscar</button>
			<a class="btn secundario" href={resolve('/pools/nuevo')}>Crear pool</a>
		</form>
		{#if categorias.length}
			<div class="chips">
				{#each categorias as categoria (categoria.id)}
					<a class="chip" href={resolve(`/pools?categoria=${categoria.id}`)}>
						{categoria.nombre}
					</a>
				{/each}
			</div>
		{/if}
	{:else}
		<a class="btn" href={resolve('/registro')}>Crear cuenta</a>
		<a class="btn secundario" href={resolve('/login')}>Ingresar</a>
	{/if}
</section>

{#if session.access}
	<h2>Pools recientes</h2>
	{#if cargando}
		<p class="muted">Cargando…</p>
	{:else if pools.length}
		<div class="grid">
			{#each pools as pool (pool.id)}
				<PoolCard {pool} />
			{/each}
		</div>
	{:else}
		<p class="muted">Todavía no hay pools. ¡Creá el primero!</p>
	{/if}
{/if}
