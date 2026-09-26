<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api } from '$lib/api.js';
	import { tonoCategoria } from '$lib/estados.js';
	import PoolCard from '$lib/PoolCard.svelte';
	import PoolCardSkeleton from '$lib/PoolCardSkeleton.svelte';
	import { session } from '$lib/session.svelte.js';

	const PASOS = [
		{
			tono: 'azul',
			titulo: 'Creá el pool',
			texto: 'Elegís el producto, el precio por unidad y cuántas unidades hacen falta.'
		},
		{
			tono: 'verde',
			titulo: 'Se suma la gente',
			texto: 'Vecinos y conocidos se unen desde la página del pool y reservan su cantidad.'
		},
		{
			tono: 'ambar',
			titulo: 'Compran juntos',
			texto: 'Cuando se completa, se confirma el pedido y se reparte entre los integrantes.'
		}
	];

	let pools = $state([]);
	let categorias = $state([]);
	let cargando = $state(true);
	let error = $state(false);
	let q = $state('');

	$effect(() => {
		cargar();
	});

	async function cargar() {
		cargando = true;
		error = false;
		try {
			const [lista, cats] = await Promise.all([
				api('/pools/', { query: { ordering: '-id' } }),
				api('/categories/')
			]);
			pools = lista.results.slice(0, 3);
			categorias = cats.results;
		} catch {
			pools = [];
			error = true;
		} finally {
			cargando = false;
		}
	}

	function buscar(event) {
		event.preventDefault();
		goto(resolve(q ? `/pools?q=${encodeURIComponent(q)}` : '/pools'));
	}

	const enlaceVacio = $derived(session.access ? '/pools/nuevo' : '/registro');
	const textoVacio = $derived(session.access ? 'Crear un pool' : 'Crear una cuenta');
</script>

<svelte:head>
	<title>PoolShop — compras colectivas entre vecinos</title>
</svelte:head>

<section class="hero">
	<div>
		<h1 class="hero__titulo">Comprá en grupo, pagá menos</h1>
		<p class="hero__bajada">
			PoolShop organiza compras colectivas: creás un pool, se suman vecinos y compran al por
			mayor. Sin intermediarios.
		</p>

		<form class="buscador" role="search" onsubmit={buscar}>
			<label class="sr-only" for="busqueda">Buscar pools</label>
			<input
				id="busqueda"
				name="q"
				type="search"
				placeholder="¿Qué querés comprar? Ej.: yerba, lavarropas…"
				bind:value={q}
			/>
			<button class="btn btn--primario" type="submit">Buscar</button>
		</form>

		<div class="hero__acciones">
			{#if session.access}
				<a class="btn btn--secundario" href={resolve('/pools/nuevo')}>Crear un pool</a>
			{:else}
				<a class="btn btn--secundario" href={resolve('/registro')}>Crear una cuenta</a>
			{/if}
			<a class="btn btn--ghost" href={resolve('/pools')}>Ver todos los pools</a>
		</div>

		<ul class="senales">
			<li>
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<path d="m5 12 4 4L19 6" />
				</svg>
				Sin intermediarios
			</li>
			<li>
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<path d="M20.59 13.41 13.42 20.58a2 2 0 0 1-2.83 0L2 12V4a2 2 0 0 1 2-2h8l8.59 8.59a2 2 0 0 1 0 2.82Z" />
					<circle cx="7.5" cy="7.5" r="1.5" />
				</svg>
				Precios al por mayor
			</li>
			<li>
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<circle cx="12" cy="8" r="3.5" />
					<path d="M5 20a7 7 0 0 1 14 0" />
				</svg>
				Coordinás en el pool
			</li>
		</ul>
	</div>

	<aside class="hero__panel" aria-labelledby="como-funciona">
		<h2 class="hero__panel-titulo" id="como-funciona">Cómo funciona</h2>
		<ol class="pasos">
			{#each PASOS as paso, i (paso.titulo)}
				<li class="paso tono-{paso.tono}">
					<span class="paso__numero" aria-hidden="true">{i + 1}</span>
					<div>
						<h3 class="paso__titulo">{paso.titulo}</h3>
						<p class="paso__texto">{paso.texto}</p>
					</div>
				</li>
			{/each}
		</ol>
	</aside>
</section>

{#if categorias.length}
	<section class="categorias" aria-labelledby="categorias-titulo">
		<h2 class="seccion-titulo" id="categorias-titulo">Explorar por categoría</h2>
		<div class="chips">
			{#each categorias as categoria (categoria.id)}
				<a
					class="chip chip--color tono-{tonoCategoria(categoria.id)}"
					href={resolve(`/pools?categoria=${categoria.id}`)}>{categoria.nombre}</a
				>
			{/each}
		</div>
	</section>
{/if}

<section class="destacados animar" aria-labelledby="destacados-titulo">
	<div class="destacados__cabecera">
		<h2 class="seccion-titulo" id="destacados-titulo">Pools recientes</h2>
		<a class="destacados__enlace" href={resolve('/pools')}>Ver todos</a>
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
			No se pudieron cargar los pools recientes. Recargá la página para volver a intentar.
		</div>
	{:else if pools.length}
		<div class="grilla-pools">
			{#each pools as pool (pool.id)}
				<PoolCard {pool} />
			{/each}
		</div>
	{:else}
		<div class="vacio">
			<h3>Todavía no hay pools</h3>
			<p>Sé la primera persona en armar una compra colectiva en tu barrio.</p>
			<a class="btn btn--primario" href={resolve(enlaceVacio)}>
				{textoVacio}
			</a>
		</div>
	{/if}
</section>

<style>
	.hero {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		gap: var(--e-7);
		align-items: center;
		padding-bottom: var(--e-8);
	}

	.hero__titulo {
		max-width: 15ch;
		font-size: var(--texto-3xl);
		font-weight: 600;
		letter-spacing: -0.03em;
	}

	.hero__bajada {
		max-width: 52ch;
		margin-top: var(--e-4);
		font-size: var(--texto-md);
		color: var(--tinta-suave);
	}

	.buscador {
		display: flex;
		gap: var(--e-2);
		max-width: 34rem;
		margin-top: var(--e-5);
	}

	.hero__acciones {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-3);
		margin-top: var(--e-4);
	}

	.senales {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2) var(--e-5);
		margin: var(--e-4) 0 0;
		padding: 0;
		list-style: none;
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
	}

	.senales li {
		display: inline-flex;
		align-items: center;
		gap: var(--e-2);
	}

	.senales svg {
		flex: none;
		color: var(--acento);
	}

	.hero__panel {
		padding: var(--e-6);
		border: 1px solid var(--linea);
		border-radius: var(--radio-lg);
		background: var(--superficie-alt);
	}

	.hero__panel-titulo {
		font-size: var(--texto-md);
	}

	.pasos {
		display: flex;
		flex-direction: column;
		gap: var(--e-5);
		margin: var(--e-5) 0 0;
		padding: 0;
		list-style: none;
	}

	.paso {
		display: flex;
		gap: var(--e-4);
	}

	.paso__numero {
		flex: none;
		width: 1.9rem;
		height: 1.9rem;
		display: grid;
		place-items: center;
		border: 1px solid var(--c-t);
		border-radius: 50%;
		background: var(--t-t);
		color: var(--c-t);
		font-family: var(--fuente-display);
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.paso__titulo {
		font-size: var(--texto-base);
	}

	.paso__texto {
		margin: var(--e-1) 0 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.seccion-titulo {
		font-size: var(--texto-xl);
	}

	.categorias {
		padding-block: var(--e-6);
		border-top: 1px solid var(--linea);
	}

	.categorias .chips {
		margin-top: var(--e-4);
	}

	.destacados {
		margin-top: var(--e-7);
		padding: var(--e-6);
		border-radius: var(--radio-lg);
		background: var(--tinte-azul);
	}

	@media (min-width: 900px) {
		.destacados .grilla-pools {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}

	.destacados__cabecera {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--e-4);
		margin-bottom: var(--e-5);
	}

	.destacados__enlace {
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	@media (max-width: 900px) {
		.hero {
			grid-template-columns: 1fr;
			gap: var(--e-6);
		}

		.hero__titulo {
			max-width: 18ch;
		}
	}
</style>
