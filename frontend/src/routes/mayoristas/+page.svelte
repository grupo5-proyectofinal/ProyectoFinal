<script>
	// Directorio curado de sitios mayoristas (Iteración 3). Público; con sesión se
	// puede sugerir un sitio, que el equipo revisa antes de publicarlo.
	import { resolve } from '$app/paths';
	import { api, fieldErrors } from '$lib/api.js';
	import { session } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';
	import { raices } from '$lib/variantes.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let proveedores = $state([]);
	let categorias = $state([]);
	let cargando = $state(true);
	let error = $state(false);
	let filtros = $state({ q: '', rubro: '', provincia: '', verificado: '' });
	let sugerencia = $state({ nombre: '', sitio_url: '', descripcion: '' });
	let erroresSugerencia = $state({});
	let sugiriendo = $state(false);
	let formularioAbierto = $state(false);
	let pedido = 0;

	$effect(() => {
		api('/categories/').then((r) => (categorias = raices(r.results ?? r))).catch(() => {});
	});

	$effect(() => {
		cargar({ ...filtros });
	});

	async function cargar(f) {
		const actual = ++pedido;
		cargando = true;
		error = false;
		try {
			const r = await api('/proveedores/', { query: f, auth: false });
			if (actual === pedido) proveedores = r.results ?? r;
		} catch {
			if (actual === pedido) error = true;
		} finally {
			if (actual === pedido) cargando = false;
		}
	}

	async function sugerir(evento) {
		evento.preventDefault();
		erroresSugerencia = {};
		sugiriendo = true;
		try {
			await api('/proveedores/', { method: 'POST', body: sugerencia });
			sugerencia = { nombre: '', sitio_url: '', descripcion: '' };
			formularioAbierto = false;
			notificar('¡Gracias! Lo revisamos y, si cumple, lo sumamos al directorio.');
		} catch (e) {
			erroresSugerencia =
				e?.status === 429
					? { detail: 'Ya sugeriste varios sitios. Probá de nuevo más tarde.' }
					: fieldErrors(e.data);
		} finally {
			sugiriendo = false;
		}
	}
</script>

<svelte:head>
	<title>Mayoristas — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Mayoristas</h1>
		<p>
			Sitios para comprar al por mayor, revisados por el equipo de PoolShop. Abrí uno para ver su
			análisis de confianza y los pools que ya compraron ahí.
		</p>
	</div>
	<div class="cabecera-pagina__acciones">
		{#if session.access}
			<Boton variante="secundario" onclick={() => (formularioAbierto = !formularioAbierto)}>
				{formularioAbierto ? 'Cerrar' : 'Sugerir un sitio'}
			</Boton>
		{/if}
		<Boton variante="primario" href={resolve('/comparar')}>Comparar costos</Boton>
	</div>
</div>

{#if formularioAbierto}
	<Tarjeta class="relleno">
		<form class="sugerir" onsubmit={sugerir}>
			<h2>Sugerir un mayorista</h2>
			<label class="campo">
				<span>Nombre *</span>
				<input bind:value={sugerencia.nombre} required maxlength="120" />
				{#if erroresSugerencia.nombre}<small class="error">{erroresSugerencia.nombre}</small>{/if}
			</label>
			<label class="campo">
				<span>Sitio web *</span>
				<input type="url" bind:value={sugerencia.sitio_url} required placeholder="https://…" />
				{#if erroresSugerencia.sitio_url}<small class="error">{erroresSugerencia.sitio_url}</small>{/if}
			</label>
			<label class="campo">
				<span>¿Qué vende? (opcional)</span>
				<textarea rows="2" bind:value={sugerencia.descripcion}></textarea>
			</label>
			{#if erroresSugerencia.detail}<Aviso variante="error">{erroresSugerencia.detail}</Aviso>{/if}
			<Boton type="submit" variante="primario" disabled={sugiriendo}>Enviar sugerencia</Boton>
		</form>
	</Tarjeta>
{/if}

<form class="filtros" role="search" onsubmit={(e) => e.preventDefault()}>
	<label class="campo">
		<span>Buscar</span>
		<input type="search" placeholder="Nombre o sitio" bind:value={filtros.q} />
	</label>
	<label class="campo">
		<span>Rubro</span>
		<select bind:value={filtros.rubro}>
			<option value="">Todos</option>
			{#each categorias as categoria (categoria.id)}
				<option value={String(categoria.id)}>{categoria.nombre}</option>
			{/each}
		</select>
	</label>
	<label class="campo">
		<span>Provincia</span>
		<input bind:value={filtros.provincia} placeholder="Ej.: Córdoba" />
	</label>
	<label class="check">
		<input
			type="checkbox"
			checked={filtros.verificado === 'true'}
			onchange={(e) => (filtros.verificado = e.currentTarget.checked ? 'true' : '')}
		/>
		Solo verificados
	</label>
</form>

{#if cargando && !proveedores.length}
	<p class="estado">Cargando mayoristas…</p>
{:else if error}
	<Aviso variante="error">No se pudo cargar el directorio. Probá de nuevo en un rato.</Aviso>
{:else if !proveedores.length}
	<p class="estado">
		{filtros.q || filtros.rubro || filtros.provincia || filtros.verificado
			? 'No hay mayoristas con esos filtros.'
			: 'Todavía no hay mayoristas en el directorio.'}
	</p>
{:else}
	<ul class="grilla">
		{#each proveedores as proveedor (proveedor.id)}
			<li>
				<a class="tarjeta" href={resolve(`/mayoristas/${proveedor.id}`)}>
					<div class="tarjeta__cabecera">
						<h2>{proveedor.nombre}</h2>
						{#if proveedor.verificado}<Badge variante="abierto">✓ Verificado</Badge>{/if}
					</div>
					<p class="tarjeta__dominio">{proveedor.dominio}</p>
					{#if proveedor.rubros_nombres.length}
						<p class="tarjeta__rubros">{proveedor.rubros_nombres.join(' · ')}</p>
					{/if}
					<dl class="tarjeta__datos">
						{#if proveedor.provincia || proveedor.ciudad}
							<div><dt>Ubicación</dt><dd>{[proveedor.ciudad, proveedor.provincia].filter(Boolean).join(', ')}</dd></div>
						{/if}
						{#if proveedor.compra_minima}
							<div><dt>Compra mínima</dt><dd>{proveedor.compra_minima}</dd></div>
						{/if}
					</dl>
				</a>
			</li>
		{/each}
	</ul>
{/if}

<style>
	.sugerir {
		display: grid;
		gap: var(--e-3);
		max-width: 36rem;
	}

	.sugerir h2 {
		margin: 0;
	}

	.filtros {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-3);
		align-items: end;
		margin: var(--e-5) 0;
	}

	.campo {
		display: grid;
		gap: var(--e-1);
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.check {
		display: flex;
		gap: var(--e-2);
		align-items: center;
		padding-bottom: 0.6rem;
		font-size: var(--texto-sm);
	}

	.error {
		color: var(--texto-peligro);
		font-weight: 400;
	}

	.estado {
		color: var(--tinta-suave);
	}

	.grilla {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: var(--e-4);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.tarjeta {
		display: grid;
		gap: var(--e-2);
		height: 100%;
		padding: var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio-md, 12px);
		background: var(--superficie);
		color: inherit;
		text-decoration: none;
	}

	.tarjeta:hover {
		border-color: var(--linea-control);
		text-decoration: none;
	}

	.tarjeta__cabecera {
		display: flex;
		justify-content: space-between;
		gap: var(--e-2);
		align-items: flex-start;
	}

	.tarjeta h2 {
		margin: 0;
		font-size: 1.1rem;
	}

	.tarjeta__dominio,
	.tarjeta__rubros {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-tenue);
	}

	.tarjeta__datos {
		display: grid;
		gap: var(--e-1);
		margin: 0;
		font-size: var(--texto-sm);
	}

	.tarjeta__datos div {
		display: flex;
		gap: var(--e-2);
	}

	.tarjeta__datos dt {
		color: var(--tinta-tenue);
	}

	.tarjeta__datos dd {
		margin: 0;
	}
</style>
