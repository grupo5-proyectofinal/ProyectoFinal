<script>
	// Directorio curado de sitios mayoristas (Iteración 3). Público; con sesión se
	// puede sugerir un sitio, que el equipo revisa antes de publicarlo.
	import { onDestroy, onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import { api, fieldErrors } from '$lib/api.js';
	import { session } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';
	import { raices } from '$lib/variantes.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Bolsitas from '$lib/Bolsitas.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
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
	let total = $state(0);
	let temporizador;
	let cargandoRubros = $state(true);

	const hayFiltros = $derived(
		Boolean(filtros.q || filtros.rubro || filtros.provincia || filtros.verificado)
	);

	function limpiarFiltros() {
		filtros = { q: '', rubro: '', provincia: '', verificado: '' };
		cargar({ ...filtros });
	}

	function quitar(clave) {
		filtros[clave] = '';
		cargar({ ...filtros });
	}

	// Los selects aplican al instante; lo que se escribe espera una pausa corta.
	function programarCarga(demora = 0) {
		clearTimeout(temporizador);
		temporizador = setTimeout(() => cargar({ ...filtros }), demora);
	}

	onDestroy(() => clearTimeout(temporizador));

	onMount(() => {
		cargar({ ...filtros });
		api('/categories/')
			.then((r) => {
				categorias = raices(r.results ?? r);
				cargandoRubros = false;
			})
			.catch(() => {
				cargandoRubros = false;
			});
	});

	async function cargar(f) {
		const actual = ++pedido;
		cargando = true;
		error = false;
		try {
			const r = await api('/proveedores/', { query: f, auth: false });
			if (actual === pedido) {
				proveedores = r.results ?? r;
				total = r.count ?? proveedores.length;
			}
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
			<Campo id="sugerencia-nombre" etiqueta="Nombre" requerido error={erroresSugerencia.nombre}>
				{#snippet children(props)}
					<input
						id="sugerencia-nombre"
						bind:value={sugerencia.nombre}
						required
						maxlength="120"
						{...props}
					/>
				{/snippet}
			</Campo>
			<Campo
				id="sugerencia-sitio"
				etiqueta="Sitio web"
				requerido
				error={erroresSugerencia.sitio_url}
			>
				{#snippet children(props)}
					<input
						id="sugerencia-sitio"
						type="url"
						bind:value={sugerencia.sitio_url}
						required
						placeholder="https://…"
						{...props}
					/>
				{/snippet}
			</Campo>
			<Campo
				id="sugerencia-descripcion"
				etiqueta="¿Qué vende?"
				ayuda="Opcional."
				error={erroresSugerencia.descripcion}
			>
				{#snippet children(props)}
					<textarea
						id="sugerencia-descripcion"
						rows="2"
						bind:value={sugerencia.descripcion}
						{...props}
					></textarea>
				{/snippet}
			</Campo>
			{#if erroresSugerencia.detail}<Aviso variante="error">{erroresSugerencia.detail}</Aviso>{/if}
			<div class="acciones">
				<Boton variante="secundario" onclick={() => (formularioAbierto = false)}>Cancelar</Boton>
				<Boton tipo="submit" variante="primario" disabled={sugiriendo}>Enviar sugerencia</Boton>
			</div>
		</form>
	</Tarjeta>
{/if}

<!-- Mismo armado que Pools: filtros en una tarjeta a la izquierda, resultados a la derecha. -->
<div class="directorio">
	<aside aria-label="Filtros">
		<Tarjeta>
			<form
				class="filtros"
				role="search"
				onsubmit={(e) => {
					e.preventDefault();
					programarCarga();
				}}
			>
				<div class="filtros__cabecera">
					<h2 class="filtros__titulo">Filtros</h2>
					{#if hayFiltros}
						<button class="filtros__limpiar" type="button" onclick={limpiarFiltros}>
							Limpiar
						</button>
					{/if}
				</div>
				{#if hayFiltros}
					<div class="chips" role="group" aria-label="Filtros aplicados">
						{#if filtros.q}
							<button type="button" class="chip" onclick={() => quitar('q')}>
								“{filtros.q}” ✕
							</button>
						{/if}
						{#if filtros.rubro}
							{@const rubro = categorias.find((c) => String(c.id) === filtros.rubro)}
							<button type="button" class="chip" onclick={() => quitar('rubro')}>
								{rubro?.nombre ?? 'Rubro'} ✕
							</button>
						{/if}
						{#if filtros.provincia}
							<button type="button" class="chip" onclick={() => quitar('provincia')}>
								{filtros.provincia} ✕
							</button>
						{/if}
						{#if filtros.verificado}
							<button type="button" class="chip" onclick={() => quitar('verificado')}>
								Solo verificados ✕
							</button>
						{/if}
					</div>
				{/if}
				<Campo id="filtro-q" etiqueta="Buscar">
					{#snippet children(props)}
						<input
							id="filtro-q"
							type="search"
							placeholder="Nombre o sitio"
							bind:value={filtros.q}
							oninput={() => programarCarga(350)}
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo id="filtro-rubro" etiqueta="Rubro">
					{#snippet children(props)}
						<select
							id="filtro-rubro"
							bind:value={filtros.rubro}
							onchange={() => programarCarga()}
							disabled={cargandoRubros}
							{...props}
						>
							<option value="">{cargandoRubros ? 'Cargando rubros…' : 'Todos'}</option>
							{#each categorias as categoria (categoria.id)}
								<option value={String(categoria.id)}>{categoria.nombre}</option>
							{/each}
						</select>
					{/snippet}
				</Campo>
				<Campo id="filtro-provincia" etiqueta="Provincia">
					{#snippet children(props)}
						<input
							id="filtro-provincia"
							bind:value={filtros.provincia}
							placeholder="Ej.: Córdoba"
							oninput={() => programarCarga(350)}
							{...props}
						/>
					{/snippet}
				</Campo>
				<label class="check">
					<input
						type="checkbox"
						checked={filtros.verificado === 'true'}
						onchange={(e) => {
							filtros.verificado = e.currentTarget.checked ? 'true' : '';
							programarCarga();
						}}
					/>
					Solo verificados
				</label>
			</form>
		</Tarjeta>
	</aside>

	<div class="resultados">
		{#if cargando && !proveedores.length}
			<p class="estado" role="status">Cargando mayoristas…</p>
		{:else if error}
			<Aviso variante="error">No se pudo cargar el directorio. Probá de nuevo en un rato.</Aviso>
		{:else if !proveedores.length}
			<div class="vacio">
				<Bolsitas variante={hayFiltros ? 'buscando' : 'durmiendo'} />
				<h3>{hayFiltros ? 'No hay mayoristas con esos filtros' : 'Todavía no hay mayoristas'}</h3>
				<p>
					{hayFiltros
						? 'Probá quitar algún filtro o buscar con otras palabras.'
						: 'Estamos armando el directorio. Si conocés un sitio confiable, sugerilo.'}
				</p>
				{#if hayFiltros}
					<Boton variante="secundario" onclick={limpiarFiltros}>Limpiar filtros</Boton>
				{/if}
			</div>
		{:else}
			<p class="resultado-cuenta" role="status">
				{total} {total === 1 ? 'mayorista' : 'mayoristas'}
			</p>
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
									<div>
										<dt>Ubicación</dt>
										<dd>{[proveedor.ciudad, proveedor.provincia].filter(Boolean).join(', ')}</dd>
									</div>
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
	</div>
</div>

<style>
	.sugerir {
		display: grid;
		max-width: 36rem;
	}

	.sugerir h2 {
		margin: 0 0 var(--e-4);
	}

	:global(.ui-tarjeta.relleno):has(.sugerir) {
		margin-bottom: var(--e-6);
	}

	.directorio {
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

	.check {
		display: flex;
		gap: var(--e-2);
		align-items: center;
		min-height: var(--alto-tap);
		font-size: var(--texto-sm);
		font-weight: 600;
		cursor: pointer;
	}

	.check input {
		width: 20px;
		height: 20px;
		min-height: 0;
	}

	@media (max-width: 900px) {
		.directorio {
			grid-template-columns: 1fr;
			gap: var(--e-4);
		}
	}

	.estado {
		color: var(--tinta-suave);
	}

	.resultado-cuenta {
		margin: 0 0 var(--e-3);
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
	}

	.chips {
		margin-bottom: var(--e-4);
	}

	.filtros :global(.chip) {
		min-height: var(--alto-tap);
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
		border-radius: var(--radio);
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
