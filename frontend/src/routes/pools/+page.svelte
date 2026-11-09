<script>
	import { notificar } from '$lib/toast.svelte.js';
	import Bolsitas from '$lib/Bolsitas.svelte';
	import { onDestroy } from 'svelte';
	import { hijas, raices } from '$lib/variantes.js';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api } from '$lib/api.js';
	import { moneda } from '$lib/formato.js';
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
	import PoolCard from '$lib/PoolCard.svelte';
	import PoolCardSkeleton from '$lib/PoolCardSkeleton.svelte';
	import { session } from '$lib/session.svelte.js';
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
	const NOMBRE_ORDEN = Object.fromEntries(ORDENES);
	const SUBTITULOS = {
		todos: 'Buscá una compra colectiva abierta en tu ciudad y sumate con la cantidad que necesites.',
		mios: 'Las compras colectivas que organizás vos.',
		unidos: 'Los pools en los que reservaste una cantidad.'
	};
	const TITULOS = { todos: 'Pools', mios: 'Mis pools', unidos: 'Mis uniones' };
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
	// Los filtros se aplican solos; el timer evita un pedido por tecla.
	let temporizadorFiltros;

	const tab = $derived(normalizarTab(page.url.searchParams.get('tab')));
	// Las pestañas personales no se muestran sin sesión: al tocarlas solo
	// llevarían al login y suman ruido a la primera visita.
	const tabsVisibles = $derived(
		TABS.filter((t) => t.id === 'todos' || Boolean(session.access))
	);
	const ctaCrear = $derived(
		session.access
			? { texto: 'Crear pool', href: '/pools/nuevo' }
			: { texto: 'Crear cuenta', href: '/registro' }
	);
	let filtrosAbiertos = $state(false);
	// "Ver más" (como en notificaciones y reseñas): suma la página siguiente a la lista.
	let paginaCargada = 1;
	let cargandoMas = $state(false);

	$effect(() => {
		const params = page.url.searchParams;
		sincronizar(params);
		cargar(tab, params);
	});

	$effect(() => {
		api('/categories/')
			.then((r) => {
				categorias = r.results ?? r;
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
			paginaCargada = query.page ?? 1;
		} catch (e) {
			if (actual !== pedido) return;
			data = { results: [], count: 0, next: null, previous: null };
			error = true;
		} finally {
			if (actual === pedido) cargando = false;
		}
	}

	function aplicar() {
		clearTimeout(temporizadorFiltros);
		goto(resolve(`/pools?${paramsDeFiltros(filtros, tab)}`));
	}

	/** Aplica al instante los selects y con una pausa corta lo que se escribe. */
	function programarAplicar(demora = 0) {
		clearTimeout(temporizadorFiltros);
		temporizadorFiltros = setTimeout(aplicar, demora);
	}

	function alEnviarFiltros(event) {
		event.preventDefault();
		aplicar();
	}

	function quitarFiltro(clave) {
		filtros[clave] = '';
		aplicar();
	}

	function limpiarFiltros() {
		Object.assign(filtros, VACIO);
		aplicar();
	}

	onDestroy(() => clearTimeout(temporizadorFiltros));

	const hayFiltros = $derived(Object.values(filtros).some((valor) => valor !== ''));

	const chips = $derived.by(() => {
		const lista = [];
		if (filtros.q) lista.push({ clave: 'q', texto: `“${filtros.q}”` });
		if (filtros.categoria) {
			const nombre =
				categorias.find((c) => String(c.id) === String(filtros.categoria))?.nombre ??
				filtros.categoria;
			lista.push({ clave: 'categoria', texto: nombre });
		}
		if (filtros.precio_min)
			lista.push({ clave: 'precio_min', texto: `Desde ${moneda(filtros.precio_min)}` });
		if (filtros.precio_max)
			lista.push({ clave: 'precio_max', texto: `Hasta ${moneda(filtros.precio_max)}` });
		if (filtros.ciudad) lista.push({ clave: 'ciudad', texto: filtros.ciudad });
		if (filtros.estado)
			lista.push({ clave: 'estado', texto: etiquetaEstado(filtros.estado) });
		if (filtros.ordering)
			lista.push({ clave: 'ordering', texto: NOMBRE_ORDEN[filtros.ordering] });
		return lista;
	});

	// Cantidad de filtros activos: alimenta el botón plegable de mobile.
	const cantidadFiltros = $derived(chips.length);

	async function verMas() {
		if (!data?.next || cargandoMas) return;
		const actual = pedido;
		cargandoMas = true;
		try {
			const query = { ...queryDeApi(page.url.searchParams), page: paginaCargada + 1 };
			const r = await api(endpointDeTab(tab), { query });
			if (actual !== pedido) return;
			data = { ...r, results: [...data.results, ...r.results] };
			paginaCargada += 1;
		} catch {
			notificar('No se pudieron cargar más pools.', 'error');
		} finally {
			cargandoMas = false;
		}
	}
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
			{#each tabsVisibles as t (t.id)}
				<a
					class="pestanas__enlace"
					class:activo={tab === t.id}
					href={resolve(rutaTab(t.id, page.url.searchParams, tab))}
					aria-current={tab === t.id ? 'page' : undefined}>{t.texto}</a
				>
			{/each}
		</nav>
		<!-- En escritorio el encabezado ya tiene "Crear pool": acá solo hace falta en pantallas chicas. -->
		<Boton
			variante="primario"
			class={session.access ? 'pools__crear' : ''}
			href={resolve(ctaCrear.href)}>{ctaCrear.texto}</Boton
		>
	</div>
</div>

<div class="explorar">
	<div class="filtros-movil">
		<button
			class="filtros-movil__toggle"
			type="button"
			aria-expanded={filtrosAbiertos}
			aria-controls="panel-filtros"
			onclick={() => (filtrosAbiertos = !filtrosAbiertos)}
		>
			<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
				<path d="M4 6h16M7 12h10M10 18h4" />
			</svg>
			<span>Filtros</span>
			{#if cantidadFiltros}
				<span class="filtros-movil__contador">{cantidadFiltros}</span>
			{/if}
			<svg class="filtros-movil__chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
				<path d="m6 9 6 6 6-6" />
			</svg>
		</button>
		{#if hayFiltros}
			<button class="filtros-movil__limpiar" type="button" onclick={limpiarFiltros}>
				Limpiar
			</button>
		{/if}
	</div>

	<aside
		id="panel-filtros"
		class="filtros-panel"
		class:filtros-panel--abierto={filtrosAbiertos}
		aria-label="Filtros"
	>
		<Tarjeta>
			<form class="filtros" onsubmit={alEnviarFiltros}>
				<div class="filtros__cabecera">
					<h2 class="filtros__titulo">Filtros</h2>
					{#if hayFiltros}
						<button class="filtros__limpiar" type="button" onclick={limpiarFiltros}>
							Limpiar
						</button>
					{/if}
				</div>

				<Campo id="q" etiqueta="Buscar">
					{#snippet children(props)}
						<input
							id="q"
							name="q"
							type="search"
							placeholder="Título, producto o usuario"
							bind:value={filtros.q}
							oninput={() => programarAplicar(350)}
							{...props}
						/>
					{/snippet}
				</Campo>

				<Campo id="categoria" etiqueta="Categoría">
					{#snippet children(props)}
						{#key categorias}
							<select id="categoria" name="categoria" bind:value={filtros.categoria} onchange={() => programarAplicar()} {...props}>
								<option value="">Todas</option>
								<!-- Principal y debajo sus tipos: filtrar por "Ropa" incluye todos. -->
								{#each raices(categorias) as categoria (categoria.id)}
									<option value={String(categoria.id)}>{categoria.nombre}</option>
									{#each hijas(categorias, categoria.id) as hija (hija.id)}
										<option value={String(hija.id)}>&nbsp;&nbsp;— {hija.nombre}</option>
									{/each}
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
								oninput={() => programarAplicar(500)}
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
								oninput={() => programarAplicar(500)}
								{...props}
							/>
						{/snippet}
					</Campo>
				</div>

				<Campo id="ciudad" etiqueta="Ciudad">
					{#snippet children(props)}
						<input id="ciudad" name="ciudad" type="text" bind:value={filtros.ciudad} oninput={() => programarAplicar(350)} {...props} />
					{/snippet}
				</Campo>

				<Campo id="estado" etiqueta="Estado">
					{#snippet children(props)}
						<select id="estado" name="estado" bind:value={filtros.estado} onchange={() => programarAplicar()} {...props}>
							<option value="">Todos</option>
							{#each ESTADOS as estado (estado)}
								<option value={estado}>{etiquetaEstado(estado)}</option>
							{/each}
						</select>
					{/snippet}
				</Campo>

				<Campo id="ordering" etiqueta="Orden">
					{#snippet children(props)}
						<select id="ordering" name="ordering" bind:value={filtros.ordering} onchange={() => programarAplicar()} {...props}>
							{#each ORDENES as [valor, texto] (valor)}
								<option value={valor}>{texto}</option>
							{/each}
						</select>
					{/snippet}
				</Campo>

				<p class="filtros__pista">Se aplican solos mientras elegís.</p>
			</form>
		</Tarjeta>
	</aside>

	<div class="resultados">
		{#if chips.length}
			<div class="chips" aria-label="Filtros aplicados">
				<span class="chips__texto">Filtros:</span>
				{#each chips as chip (chip.clave)}
					<button
						type="button"
						class="chip"
						onclick={() => quitarFiltro(chip.clave)}
						aria-label={`Quitar filtro ${chip.texto}`}
					>
						{chip.texto}
						<span class="chip__equis" aria-hidden="true">×</span>
					</button>
				{/each}
				<button type="button" class="chips__limpiar" onclick={limpiarFiltros}>
					Limpiar todo
				</button>
			</div>
		{/if}
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
			{#if data.next}
				<div class="ver-mas">
					<Boton variante="secundario" disabled={cargandoMas} onclick={verMas}>
						{cargandoMas ? 'Cargando…' : 'Ver más'}
					</Boton>
				</div>
			{/if}
		{:else}
			<div class="vacio">
				<Bolsitas variante={hayFiltros ? 'buscando' : 'durmiendo'} />
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
						<Boton variante="primario" href={resolve(ctaCrear.href)}>{ctaCrear.texto}</Boton>
					{/if}
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
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
		padding: 0;
		border: 0;
		background: transparent;
		color: var(--marca-fuerte);
		font-family: inherit;
		font-size: var(--texto-sm);
		font-weight: 700;
		cursor: pointer;
	}

	.filtros__limpiar:hover {
		text-decoration: underline;
	}

	.filtros__pista {
		margin: var(--e-1) 0 0;
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.chips {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2);
		margin-bottom: var(--e-4);
	}

	.chips__texto {
		font-size: var(--texto-sm);
		font-weight: 700;
		color: var(--tinta-suave);
	}

	.chip {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		min-height: 38px;
		padding: 0 0.85rem;
		border: 1px solid var(--linea-fuerte);
		border-radius: var(--radio-full);
		background: var(--superficie);
		color: var(--tinta);
		font: inherit;
		font-size: var(--texto-sm);
		cursor: pointer;
	}

	.chip:hover {
		border-color: var(--marca);
		background: var(--melocoton);
		color: var(--marca-fuerte);
	}

	.chip__equis {
		font-size: 1rem;
		line-height: 1;
		color: var(--tinta-tenue);
	}

	.chips__limpiar {
		min-height: 38px;
		padding: 0 0.5rem;
		border: 0;
		background: transparent;
		color: var(--marca-fuerte);
		font: inherit;
		font-size: var(--texto-sm);
		font-weight: 700;
		cursor: pointer;
	}

	.chips__limpiar:hover {
		text-decoration: underline;
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

	.filtros-movil {
		display: none;
	}

	@media (min-width: 1181px) {
		/* Más específico que el display propio de Boton. */
		.cabecera-pagina__acciones :global(.ui-boton.pools__crear) {
			display: none;
		}
	}

	@media (max-width: 900px) {
		.explorar {
			grid-template-columns: 1fr;
			gap: var(--e-4);
		}

		.cabecera-pagina__acciones {
			width: 100%;
		}

		.filtros-movil {
			display: flex;
			align-items: center;
			gap: var(--e-3);
		}

		.filtros-movil__toggle {
			display: flex;
			flex: 1;
			align-items: center;
			gap: var(--e-2);
			min-height: var(--alto-tap);
			padding: 0 var(--e-4);
			border: 1px solid var(--linea-fuerte);
			border-radius: var(--radio-sm);
			background: var(--superficie);
			color: var(--tinta);
			font: inherit;
			font-size: var(--texto-sm);
			font-weight: 700;
			cursor: pointer;
		}

		.filtros-movil__toggle svg {
			flex: none;
			width: 18px;
			height: 18px;
			color: var(--tinta-suave);
		}

		.filtros-movil__toggle:hover {
			border-color: var(--marca);
			color: var(--marca-fuerte);
		}

		.filtros-movil__chevron {
			margin-left: auto;
			transition: transform var(--transicion);
		}

		.filtros-movil__toggle[aria-expanded='true'] .filtros-movil__chevron {
			transform: rotate(180deg);
		}

		.filtros-movil__contador {
			display: grid;
			place-items: center;
			min-width: 22px;
			height: 22px;
			padding: 0 0.4rem;
			border-radius: var(--radio-full);
			background: var(--marca-fuerte);
			color: var(--superficie);
			font-size: var(--texto-xs);
			font-weight: 800;
		}

		.filtros-movil__limpiar {
			min-height: var(--alto-tap);
			padding: 0 var(--e-2);
			border: 0;
			background: transparent;
			color: var(--marca-fuerte);
			font: inherit;
			font-size: var(--texto-sm);
			font-weight: 700;
			cursor: pointer;
		}

		.filtros-panel {
			display: none;
		}

		.filtros-panel--abierto {
			display: block;
		}
	}
</style>
