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
	import Aviso from '$lib/ui/Aviso.svelte';
	import Avatar from '$lib/ui/Avatar.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

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
		['-vistas', 'Más vistos'],
		['restante', 'Cerca de completarse']
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
	let perfiles = $state([]);
	let pedidoPerfiles = 0;

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

	// La búsqueda del header también encuentra perfiles por nombre de usuario.
	const terminoPerfiles = $derived(
		tab === 'todos' ? (page.url.searchParams.get('q') ?? '').trim() : ''
	);

	$effect(() => {
		buscarPerfiles(terminoPerfiles);
	});

	async function buscarPerfiles(q) {
		const actual = ++pedidoPerfiles;
		if (q.length < 2) {
			perfiles = [];
			return;
		}
		try {
			const r = await api('/usuarios/', { query: { q }, auth: false });
			if (actual === pedidoPerfiles) perfiles = r.results;
		} catch {
			if (actual === pedidoPerfiles) perfiles = [];
		}
	}

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
		<h1>{TITULOS[tab]}</h1>
		<p>{SUBTITULOS[tab]}</p>
	</div>
	<div class="cabecera-pagina__acciones">
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
		<Boton variante="primario" href={resolve('/pools/nuevo')}>Crear pool</Boton>
	</div>
</div>

<div class="explorar">
	<aside aria-label="Filtros">
		<Tarjeta>
			<form class="filtros" onsubmit={aplicar}>
				<div class="filtros__cabecera">
					<h2 class="filtros__titulo">Filtros</h2>
					<a class="filtros__limpiar" href={resolve(rutaTab(tab))}>Limpiar</a>
				</div>

				<Campo id="q" etiqueta="Buscar">
					{#snippet children(props)}
						<input
							id="q"
							name="q"
							type="search"
							placeholder="Título, producto o usuario"
							bind:value={filtros.q}
							{...props}
						/>
					{/snippet}
				</Campo>

				<Campo id="categoria" etiqueta="Categoría">
					{#snippet children(props)}
						{#key categorias}
							<select id="categoria" name="categoria" bind:value={filtros.categoria} {...props}>
								<option value="">Todas</option>
								{#each categorias as categoria (categoria.id)}
									<option value={String(categoria.id)}>{categoria.nombre}</option>
								{/each}
							</select>
						{/key}
					{/snippet}
				</Campo>
				{#if errorCategorias}
					<div class="filtros__aviso">
						<Aviso variante="aviso">
							No se pudieron cargar las categorías. Podés filtrar por el resto de los campos.
						</Aviso>
					</div>
				{/if}

				<div class="filtros__par">
					<Campo id="precio_min" etiqueta="Precio mínimo">
						{#snippet children(props)}
							<input
								id="precio_min"
								name="precio_min"
								type="number"
								min="0"
								bind:value={filtros.precio_min}
								{...props}
							/>
						{/snippet}
					</Campo>
					<Campo id="precio_max" etiqueta="Precio máximo">
						{#snippet children(props)}
							<input
								id="precio_max"
								name="precio_max"
								type="number"
								min="0"
								bind:value={filtros.precio_max}
								{...props}
							/>
						{/snippet}
					</Campo>
				</div>

				<Campo id="ciudad" etiqueta="Ciudad">
					{#snippet children(props)}
						<input id="ciudad" name="ciudad" type="text" bind:value={filtros.ciudad} {...props} />
					{/snippet}
				</Campo>

				<Campo id="estado" etiqueta="Estado">
					{#snippet children(props)}
						<select id="estado" name="estado" bind:value={filtros.estado} {...props}>
							<option value="">Todos</option>
							{#each ESTADOS as estado (estado)}
								<option value={estado}>{etiquetaEstado(estado)}</option>
							{/each}
						</select>
					{/snippet}
				</Campo>

				<Campo id="ordering" etiqueta="Orden">
					{#snippet children(props)}
						<select id="ordering" name="ordering" bind:value={filtros.ordering} {...props}>
							{#each ORDENES as [valor, texto] (valor)}
								<option value={valor}>{texto}</option>
							{/each}
						</select>
					{/snippet}
				</Campo>

				<div class="filtros__acciones">
					<Boton tipo="submit" variante="primario">Filtrar</Boton>
					<Boton variante="ghost" href={resolve(rutaTab(tab))}>Limpiar filtros</Boton>
				</div>
			</form>
		</Tarjeta>
	</aside>

	<div class="resultados">
		{#if perfiles.length}
			<section class="perfiles" aria-labelledby="titulo-perfiles">
				<h2 id="titulo-perfiles" class="perfiles__titulo">
					{perfiles.length === 1 ? '1 perfil' : `${perfiles.length} perfiles`} que coinciden
				</h2>
				<ul class="perfiles__lista">
					{#each perfiles as perfil (perfil.id)}
						<li>
							<a class="perfil-chip" href={resolve(`/usuarios/${perfil.id}`)}>
								<Avatar nombre={perfil.username} foto={perfil.foto} tamano="sm" aria-hidden="true" />
								<span class="perfil-chip__datos">
									<span class="perfil-chip__nombre">@{perfil.username}</span>
									{#if perfil.ciudad}<span class="perfil-chip__ciudad">{perfil.ciudad}</span>{/if}
								</span>
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/if}
		{#if cargando}
			<p class="sr-only" role="status">Cargando pools…</p>
			<div class="grilla-pools" aria-hidden="true">
				{#each [0, 1, 2, 3, 4, 5] as i (i)}
					<PoolCardSkeleton />
				{/each}
			</div>
		{:else if error}
			<Aviso variante="error">
				No se pudieron cargar los pools. Recargá la página para volver a intentar.
			</Aviso>
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
				<Boton
					variante="secundario"
					disabled={paginaActual <= 1}
					onclick={() => irAPagina(paginaActual - 1)}
				>
					Anterior
				</Boton>
				<span class="paginacion__estado">Página {paginaActual}</span>
				<Boton variante="secundario" disabled={!data.next} onclick={() => irAPagina(paginaActual + 1)}>
					Siguiente
				</Boton>
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
						<Boton variante="secundario" href={resolve(rutaTab(tab))}>Limpiar filtros</Boton>
					{/if}
					{#if tab === 'unidos'}
						<Boton variante="primario" href={resolve(rutaTab('todos'))}>Ver pools</Boton>
					{:else}
						<Boton variante="primario" href={resolve('/pools/nuevo')}>Crear pool</Boton>
					{/if}
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.pestanas {
		display: flex;
		gap: 2px;
		padding: 5px;
		border-radius: var(--radio);
		background: var(--melocoton-fuerte);
	}

	.pestanas__enlace {
		display: flex;
		align-items: center;
		min-height: var(--alto-tap);
		padding: 0 1.25rem;
		border-radius: var(--radio-sm);
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
		font-weight: 700;
		white-space: nowrap;
	}

	.pestanas__enlace:hover {
		color: var(--marca-fuerte);
		text-decoration: none;
	}

	.pestanas__enlace.activo {
		background: var(--superficie);
		color: var(--marca-fuerte);
	}

	.explorar {
		display: grid;
		grid-template-columns: minmax(240px, 280px) minmax(0, 1fr);
		gap: var(--e-6);
		align-items: start;
	}

	.filtros {
		display: flex;
		flex-direction: column;
		padding: var(--e-5);
	}

	.filtros__cabecera {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--e-3);
		margin-bottom: var(--e-4);
	}

	.filtros__titulo {
		font-size: var(--texto-lg);
	}

	.filtros__limpiar {
		font-size: var(--texto-sm);
		font-weight: 700;
	}

	.filtros__par {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0 var(--e-3);
	}

	.filtros__aviso {
		margin-bottom: var(--e-4);
	}

	.filtros__acciones {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3);
		margin-top: var(--e-2);
		padding-top: var(--e-4);
		border-top: 1px solid var(--linea);
	}

	.perfiles {
		margin-bottom: var(--e-6);
		padding-bottom: var(--e-5);
		border-bottom: 1px solid var(--linea);
	}

	.perfiles__titulo {
		margin-bottom: var(--e-3);
		font-size: var(--texto-lg);
	}

	.perfiles__lista {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.perfil-chip {
		display: flex;
		align-items: center;
		gap: var(--e-2);
		min-height: var(--alto-tap);
		padding: 0.35rem 1rem 0.35rem 0.35rem;
		border: 1px solid var(--linea-fuerte);
		border-radius: var(--radio-full);
		background: var(--superficie);
		color: var(--tinta);
	}

	.perfil-chip:hover {
		border-color: var(--marca);
		background: var(--melocoton);
		text-decoration: none;
	}

	.perfil-chip__datos {
		display: flex;
		flex-direction: column;
		line-height: 1.2;
	}

	.perfil-chip__nombre {
		font-size: var(--texto-sm);
		font-weight: 700;
	}

	.perfil-chip__ciudad {
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.resultado-cuenta {
		margin-bottom: var(--e-4);
		font-family: var(--fuente-display);
		font-size: var(--texto-lg);
		font-weight: 800;
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

	@media (max-width: 900px) {
		.explorar {
			grid-template-columns: 1fr;
		}
	}
</style>
