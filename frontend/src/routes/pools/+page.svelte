<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api } from '$lib/api.js';
	import { etiquetaEstado } from '$lib/estados.js';
	import PoolCard from '$lib/PoolCard.svelte';
	import PoolCardSkeleton from '$lib/PoolCardSkeleton.svelte';

	const VACIO = {
		q: '',
		categoria: '',
		precio_min: '',
		precio_max: '',
		ciudad: '',
		estado: '',
		ordering: ''
	};
	const ESTADOS = ['abierto', 'listo', 'en_curso', 'finalizado', 'cancelado'];
	const ORDENES = [
		['', 'Más recientes'],
		['fecha_caducidad', 'Caducan primero'],
		['-fecha_caducidad', 'Caducan último'],
		['precio_unitario', 'Precio menor'],
		['-precio_unitario', 'Precio mayor'],
		['-vistas', 'Más vistos']
	];

	let filtros = $state({ ...VACIO });
	let categorias = $state([]);
	let data = $state(null);
	let cargando = $state(true);

	$effect(() => {
		const params = page.url.searchParams;
		sincronizar(params);
		cargar(params);
	});

	$effect(() => {
		api('/categories/')
			.then((r) => (categorias = r.results))
			.catch(() => {});
	});

	function sincronizar(params) {
		for (const key of Object.keys(VACIO)) filtros[key] = params.get(key) ?? '';
	}

	async function cargar(params) {
		cargando = true;
		try {
			data = await api('/pools/', { query: Object.fromEntries(params) });
		} catch {
			data = { results: [], count: 0, next: null, previous: null };
		} finally {
			cargando = false;
		}
	}

	function aplicar(event) {
		event.preventDefault();
		const params = new URLSearchParams();
		for (const [key, value] of Object.entries(filtros)) {
			if (value) params.set(key, value);
		}
		const query = params.toString();
		goto(resolve(query ? `/pools?${query}` : '/pools'));
	}

	const paginaActual = $derived(Number(page.url.searchParams.get('page') ?? 1));

	function irAPagina(n) {
		const params = new URLSearchParams(page.url.searchParams);
		params.set('page', n);
		goto(resolve(`/pools?${params}`));
	}

	const hayFiltros = $derived(Object.values(filtros).some((valor) => valor !== ''));
</script>

<svelte:head>
	<title>Pools — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Pools</h1>
		<p>Buscá una compra colectiva abierta en tu ciudad y sumate con la cantidad que necesites.</p>
	</div>
	<div class="cabecera-pagina__acciones">
		<a class="btn btn--primario" href={resolve('/pools/nuevo')}>Crear pool</a>
	</div>
</div>

<form class="panel filtros" onsubmit={aplicar}>
	<div class="campo filtros__busqueda">
		<label for="q">Buscar</label>
		<input
			id="q"
			name="q"
			type="search"
			bind:value={filtros.q}
			placeholder="Título, producto o descripción"
		/>
	</div>

	<div class="filtros__grilla">
		<div class="campo">
			<label for="categoria">Categoría</label>
			<select id="categoria" name="categoria" bind:value={filtros.categoria}>
				<option value="">Todas</option>
				{#each categorias as categoria (categoria.id)}
					<option value={categoria.id}>{categoria.nombre}</option>
				{/each}
			</select>
		</div>
		<div class="campo">
			<label for="precio_min">Precio mínimo</label>
			<input id="precio_min" name="precio_min" type="number" min="0" bind:value={filtros.precio_min} />
		</div>
		<div class="campo">
			<label for="precio_max">Precio máximo</label>
			<input id="precio_max" name="precio_max" type="number" min="0" bind:value={filtros.precio_max} />
		</div>
		<div class="campo">
			<label for="ciudad">Ciudad</label>
			<input id="ciudad" name="ciudad" type="text" bind:value={filtros.ciudad} />
		</div>
		<div class="campo">
			<label for="estado">Estado</label>
			<select id="estado" name="estado" bind:value={filtros.estado}>
				<option value="">Todos</option>
				{#each ESTADOS as estado (estado)}
					<option value={estado}>{etiquetaEstado(estado)}</option>
				{/each}
			</select>
		</div>
		<div class="campo">
			<label for="ordering">Orden</label>
			<select id="ordering" name="ordering" bind:value={filtros.ordering}>
				{#each ORDENES as [valor, texto] (valor)}
					<option value={valor}>{texto}</option>
				{/each}
			</select>
		</div>
	</div>

	<div class="filtros__acciones">
		<button class="btn btn--primario" type="submit">Filtrar</button>
		<a class="btn btn--ghost" href={resolve('/pools')}>Limpiar filtros</a>
	</div>
</form>

{#if cargando}
	<p class="sr-only" role="status">Cargando pools…</p>
	<div class="grilla-pools" aria-hidden="true">
		{#each [0, 1, 2, 3, 4, 5] as i (i)}
			<PoolCardSkeleton />
		{/each}
	</div>
{:else if data?.results?.length}
	<h2 class="sr-only">Resultados de la búsqueda</h2>
	<p class="resultado-cuenta" role="status">
		{data.count}
		{data.count === 1 ? 'pool encontrado' : 'pools encontrados'}
	</p>
	<div class="grilla-pools">
		{#each data.results as pool (pool.id)}
			<PoolCard {pool} />
		{/each}
	</div>
	<nav class="paginacion" aria-label="Paginación de pools">
		<button
			class="btn btn--secundario"
			type="button"
			disabled={paginaActual <= 1}
			onclick={() => irAPagina(paginaActual - 1)}
		>
			Anterior
		</button>
		<span class="paginacion__estado">Página {paginaActual}</span>
		<button
			class="btn btn--secundario"
			type="button"
			disabled={!data.next}
			onclick={() => irAPagina(paginaActual + 1)}
		>
			Siguiente
		</button>
	</nav>
{:else}
	<div class="vacio">
		<h3>No se encontraron pools</h3>
		<p>
			{#if hayFiltros}
				Probá quitar algún filtro o buscar con otras palabras.
			{:else}
				Todavía no hay pools publicados. Creá el primero.
			{/if}
		</p>
		<div class="vacio__acciones">
			{#if hayFiltros}
				<a class="btn btn--secundario" href={resolve('/pools')}>Limpiar filtros</a>
			{/if}
			<a class="btn btn--primario" href={resolve('/pools/nuevo')}>Crear pool</a>
		</div>
	</div>
{/if}

<style>
	.filtros {
		padding: clamp(1.25rem, 2.5vw, 1.75rem);
		margin-bottom: var(--e-6);
	}

	.filtros__busqueda input {
		min-height: 44px;
		font-size: var(--texto-base);
	}

	.filtros__grilla {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
		gap: 0 var(--e-4);
	}

	.filtros__acciones {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3);
		margin-top: var(--e-3);
		padding-top: var(--e-4);
		border-top: 1px solid var(--linea);
	}

	.resultado-cuenta {
		margin-bottom: var(--e-4);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.vacio__acciones {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: var(--e-3);
	}

	.paginacion {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-4);
		margin-top: var(--e-7);
		padding-top: var(--e-5);
		border-top: 1px solid var(--linea);
	}

	.paginacion__estado {
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}
</style>
