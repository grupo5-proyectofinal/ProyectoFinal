<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api } from '$lib/api.js';
	import { etiquetaEstado } from '$lib/estados.js';
	import {
		TABS,
		contextoDeTab,
		endpointDeTab,
		normalizarTab,
		paginaDeParams,
		paramsDeFiltros,
		queryDeApi,
		rutaTab
	} from '$lib/pestanas.js';
	import { logout } from '$lib/session.svelte.js';
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
	const SUBTITULOS = {
		todos: 'Buscá una compra colectiva abierta en tu ciudad y sumate con la cantidad que necesites.',
		mios: 'Las compras colectivas que organizás vos.',
		unidos: 'Los pools en los que reservaste una cantidad.'
	};
	const TITULOS = { todos: 'Pools', mios: 'Mis pools', unidos: 'Unidos' };
	const VACIOS = {
		todos: ['No se encontraron pools', 'Todavía no hay pools publicados. Creá el primero.'],
		mios: [
			'Todavía no creaste ningún pool',
			'Armá tu primera compra colectiva y compartila con quien quieras.'
		],
		unidos: [
			'No te uniste a ningún pool todavía',
			'Explorá las compras abiertas y reservá la cantidad que necesites.'
		]
	};

	let filtros = $state({ ...VACIO });
	let categorias = $state([]);
	let data = $state(null);
	let cargando = $state(true);
	let error = $state(false);
	let errorCategorias = $state(false);
	let pedido = 0;

	const tab = $derived(normalizarTab(page.url.searchParams.get('tab')));

	$effect(() => {
		const params = page.url.searchParams;
		sincronizar(params);
		cargar(tab, params);
	});

	$effect(() => {
		api('/categories/')
			.then((r) => {
				categorias = r.results;
				errorCategorias = false;
			})
			.catch(() => {
				errorCategorias = true;
			});
	});

	function sincronizar(params) {
		for (const key of Object.keys(VACIO)) filtros[key] = params.get(key) ?? '';
	}

	async function cargar(tabActivo, params) {
		const actual = ++pedido;
		cargando = true;
		error = false;
		try {
			const query = queryDeApi(params);
			if (query.page !== undefined) query.page = paginaDeParams(params);
			const r = await api(endpointDeTab(tabActivo), { query });
			if (actual !== pedido) return;
			data = r;
		} catch (e) {
			if (actual !== pedido) return;
			data = { results: [], count: 0, next: null, previous: null };
			if (e?.status === 401) logout();
			error = true;
		} finally {
			if (actual === pedido) cargando = false;
		}
	}

	function aplicar(event) {
		event.preventDefault();
		goto(resolve(`/pools?${paramsDeFiltros(filtros, tab)}`));
	}

	const paginaActual = $derived(paginaDeParams(page.url.searchParams));

	function irAPagina(n) {
		const params = new URLSearchParams(page.url.searchParams);
		params.set('page', n);
		goto(resolve(`/pools?${params}`));
	}

	const hayFiltros = $derived(Object.values(filtros).some((valor) => valor !== ''));
</script>

<svelte:head>
	<title>{TITULOS[tab]} — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Pools</h1>
		<p>{SUBTITULOS[tab]}</p>
	</div>
	<div class="cabecera-pagina__acciones">
		<a class="btn btn--primario" href={resolve('/pools/nuevo')}>Crear pool</a>
	</div>
</div>

<nav class="pestanas" aria-label="Pestañas de pools">
	{#each TABS as t (t.id)}
		<a
			class="pestanas__enlace"
			class:activo={tab === t.id}
			href={resolve(rutaTab(t.id, page.url.searchParams, tab))}
			aria-current={tab === t.id ? 'page' : undefined}>{t.texto}</a
		>
	{/each}
</nav>

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
			{#key categorias}
				<select id="categoria" name="categoria" bind:value={filtros.categoria}>
					<option value="">Todas</option>
					{#each categorias as categoria (categoria.id)}
						<option value={String(categoria.id)}>{categoria.nombre}</option>
					{/each}
				</select>
			{/key}
			{#if errorCategorias}
				<p class="alerta alerta--aviso" role="alert">
					No se pudieron cargar las categorías. Podés filtrar por el resto de los campos.
				</p>
			{/if}
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
		<a class="btn btn--ghost" href={resolve(rutaTab(tab))}>Limpiar filtros</a>
	</div>
</form>

{#if cargando}
	<p class="sr-only" role="status">Cargando pools…</p>
	<div class="grilla-pools" aria-hidden="true">
		{#each [0, 1, 2, 3, 4, 5] as i (i)}
			<PoolCardSkeleton />
		{/each}
	</div>
{:else if error}
	<div class="alerta alerta--error" role="alert">
		No se pudieron cargar los pools. Recargá la página para volver a intentar.
	</div>
{:else if data?.results?.length}
	<h2 class="sr-only">Resultados de la búsqueda</h2>
	<p class="resultado-cuenta" role="status">
		{data.count}
		{data.count === 1 ? 'pool encontrado' : 'pools encontrados'}
	</p>
	<div class="grilla-pools">
		{#each data.results as pool (pool.id)}
			<PoolCard {pool} contexto={contextoDeTab(tab)} />
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
		<h3>{VACIOS[tab][0]}</h3>
		<p>
			{#if hayFiltros}
				Probá quitar algún filtro o buscar con otras palabras.
			{:else}
				{VACIOS[tab][1]}
			{/if}
		</p>
		<div class="vacio__acciones">
			{#if hayFiltros}
				<a class="btn btn--secundario" href={resolve(rutaTab(tab))}>Limpiar filtros</a>
			{/if}
			{#if tab === 'unidos'}
				<a class="btn btn--primario" href={resolve(rutaTab('todos'))}>Ver pools</a>
			{:else}
				<a class="btn btn--primario" href={resolve('/pools/nuevo')}>Crear pool</a>
			{/if}
		</div>
	</div>
{/if}

<style>
	.pestanas {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
		margin-bottom: var(--e-5);
		border-bottom: 1px solid var(--linea);
	}

	.pestanas__enlace {
		padding: 0.55rem 0.9rem;
		border-bottom: 2px solid transparent;
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
		font-weight: 500;
	}

	.pestanas__enlace:hover {
		color: var(--tinta);
		text-decoration: none;
	}

	.pestanas__enlace.activo {
		color: var(--tinta);
		border-color: var(--acento);
	}

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
