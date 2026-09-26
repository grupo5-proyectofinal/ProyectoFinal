<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api } from '$lib/api.js';
	import { etiquetaEstado } from '$lib/estados.js';
	import PoolCard from '$lib/PoolCard.svelte';

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
</script>

<h1>Pools</h1>

<form class="tarjeta" onsubmit={aplicar}>
	<div class="filtros">
		<div class="campo">
			<label for="q">Buscar</label>
			<input id="q" type="search" bind:value={filtros.q} />
		</div>
		<div class="campo">
			<label for="categoria">Categoría</label>
			<select id="categoria" bind:value={filtros.categoria}>
				<option value="">Todas</option>
				{#each categorias as categoria (categoria.id)}
					<option value={categoria.id}>{categoria.nombre}</option>
				{/each}
			</select>
		</div>
		<div class="campo">
			<label for="precio_min">Precio mín.</label>
			<input id="precio_min" type="number" min="0" bind:value={filtros.precio_min} />
		</div>
		<div class="campo">
			<label for="precio_max">Precio máx.</label>
			<input id="precio_max" type="number" min="0" bind:value={filtros.precio_max} />
		</div>
		<div class="campo">
			<label for="ciudad">Ciudad</label>
			<input id="ciudad" type="text" bind:value={filtros.ciudad} />
		</div>
		<div class="campo">
			<label for="estado">Estado</label>
			<select id="estado" bind:value={filtros.estado}>
				<option value="">Todos</option>
				{#each ESTADOS as estado (estado)}
					<option value={estado}>{etiquetaEstado(estado)}</option>
				{/each}
			</select>
		</div>
		<div class="campo">
			<label for="ordering">Orden</label>
			<select id="ordering" bind:value={filtros.ordering}>
				{#each ORDENES as [valor, texto] (valor)}
					<option value={valor}>{texto}</option>
				{/each}
			</select>
		</div>
	</div>
	<div class="acciones">
		<button class="btn" type="submit">Filtrar</button>
		<a class="btn secundario" href={resolve('/pools')}>Limpiar</a>
		<a class="btn secundario" href={resolve('/pools/nuevo')}>Crear pool</a>
	</div>
</form>

{#if cargando}
	<p class="muted">Cargando…</p>
{:else if data?.results?.length}
	<div class="grid">
		{#each data.results as pool (pool.id)}
			<PoolCard {pool} />
		{/each}
	</div>
	<div class="paginacion">
		<button
			class="btn secundario"
			type="button"
			disabled={paginaActual <= 1}
			onclick={() => irAPagina(paginaActual - 1)}
		>
			Anterior
		</button>
		<span class="muted">Página {paginaActual} · {data.count} pools</span>
		<button
			class="btn secundario"
			type="button"
			disabled={!data.next}
			onclick={() => irAPagina(paginaActual + 1)}
		>
			Siguiente
		</button>
	</div>
{:else}
	<p class="muted">No se encontraron resultados.</p>
{/if}
