<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api } from '$lib/api.js';
	import Estrellas from '$lib/Estrellas.svelte';
	import { fecha } from '$lib/formato.js';
	import { fechaHora } from '$lib/historial.js';
	import PoolCard from '$lib/PoolCard.svelte';
	import PoolCardSkeleton from '$lib/PoolCardSkeleton.svelte';
	import { etiquetaRol, formatoPuntaje, textoResenas } from '$lib/resenas.js';
	import { session } from '$lib/session.svelte.js';
	import Avatar from '$lib/ui/Avatar.svelte';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let perfil = $state(null);
	let error = $state('');
	let cargando = $state(true);
	let pools = $state(null);
	let errorPools = $state(false);
	let resenas = $state([]);
	let siguienteResenas = $state(null);
	let totalResenas = $state(0);
	let errorResenas = $state(false);
	let cargandoMas = $state(false);
	let pedido = 0;

	const id = $derived(page.params.id);
	const esPropio = $derived(session.user != null && String(session.user.id) === String(id));

	$effect(() => {
		cargar(id);
	});

	async function cargar(usuarioId) {
		const actual = ++pedido;
		cargando = true;
		error = '';
		pools = null;
		resenas = [];
		errorPools = false;
		errorResenas = false;
		try {
			const datos = await api(`/usuarios/${usuarioId}/`);
			if (actual !== pedido) return;
			perfil = datos;
		} catch (e) {
			if (actual !== pedido) return;
			perfil = null;
			error = e?.status === 404 ? 'Este usuario no existe.' : 'No se pudo cargar el perfil.';
			return;
		} finally {
			if (actual === pedido) cargando = false;
		}
		cargarPools(usuarioId, actual);
		cargarResenas(`/usuarios/${usuarioId}/resenas/`, actual, false);
	}

	async function cargarPools(usuarioId, actual) {
		try {
			const r = await api('/pools/', { query: { creador: usuarioId } });
			if (actual === pedido) pools = r;
		} catch {
			if (actual === pedido) errorPools = true;
		}
	}

	async function cargarResenas(ruta, actual, sumar, query) {
		try {
			const r = await api(ruta, { query });
			if (actual !== pedido) return;
			resenas = sumar ? [...resenas, ...r.results] : r.results;
			totalResenas = r.count;
			siguienteResenas = r.next;
		} catch {
			if (actual === pedido) errorResenas = true;
		}
	}

	async function verMasResenas() {
		if (!siguienteResenas) return;
		cargandoMas = true;
		const pagina = new URL(siguienteResenas, window.location.origin).searchParams.get('page');
		await cargarResenas(`/usuarios/${id}/resenas/`, pedido, true, { page: pagina });
		cargandoMas = false;
	}
</script>

<svelte:head>
	<title>{perfil ? `@${perfil.username}` : 'Perfil'} — PoolShop</title>
</svelte:head>

{#if cargando}
	<p class="muted" role="status">Cargando perfil…</p>
{:else if error}
	<div class="vacio">
		<h1>{error}</h1>
		<Boton variante="primario" href={resolve('/pools')}>Explorar pools</Boton>
	</div>
{:else if perfil}
	<div class="publico">
		<aside class="publico__lateral">
			<div class="publico__tarjeta">
				<Avatar
					class="publico__avatar"
					nombre={perfil.username}
					foto={perfil.foto}
					tamano="lg"
					aria-hidden="true"
				/>
				<h1 class="publico__nombre">@{perfil.username}</h1>
				<p class="publico__meta">
					{#if perfil.ciudad}{perfil.ciudad}&nbsp;·&nbsp;{/if}En PoolShop desde {fecha(perfil.antiguedad)}
				</p>
				<p class="publico__puntaje">
					{#if perfil.cantidad_resenas}
						<Estrellas puntaje={perfil.puntaje_promedio} tamano={16} />
						<b>{formatoPuntaje(perfil.puntaje_promedio)}</b>
						<span>({textoResenas(perfil.cantidad_resenas)})</span>
					{:else}
						<span>Todavía sin reseñas</span>
					{/if}
				</p>
				{#if esPropio}
					<Boton variante="secundario" tamano="sm" href={resolve('/perfil')}>Editar mi perfil</Boton>
				{/if}
			</div>

			<dl class="publico__cifras">
				<div class="cifra">
					<dt>Pools creados</dt>
					<dd>{perfil.pools_creados}</dd>
				</div>
				<div class="cifra">
					<dt>Participaciones</dt>
					<dd>{perfil.pools_unidos}</dd>
				</div>
				<div class="cifra">
					<dt>Reseñas</dt>
					<dd>{perfil.cantidad_resenas}</dd>
				</div>
			</dl>

			{#if perfil.pools_en_comun.length}
				<Tarjeta>
					<div class="en-comun">
						<h2 class="en-comun__titulo">Pools en común</h2>
						<ul class="en-comun__lista">
							{#each perfil.pools_en_comun as pool (pool.id)}
								<li><a href={resolve(`/pools/${pool.id}`)}>{pool.titulo}</a></li>
							{/each}
						</ul>
					</div>
				</Tarjeta>
			{/if}
		</aside>

		<div class="publico__principal">
			<section class="bloque" aria-labelledby="titulo-pools">
				<div class="bloque__cabecera">
					<h2 id="titulo-pools">Pools creados</h2>
					{#if pools}<span class="bloque__nota">{pools.count} en total</span>{/if}
				</div>
				{#if errorPools}
					<Aviso variante="error">No se pudieron cargar los pools de este usuario.</Aviso>
				{:else if !pools}
					<div class="grilla-pools" aria-hidden="true">
						{#each [0, 1, 2] as i (i)}
							<PoolCardSkeleton />
						{/each}
					</div>
				{:else if pools.results.length}
					<div class="grilla-pools">
						{#each pools.results as pool (pool.id)}
							<PoolCard {pool} />
						{/each}
					</div>
				{:else}
					<p class="muted">Todavía no creó ningún pool.</p>
				{/if}
			</section>

			<Tarjeta>
				<section class="resenas" aria-labelledby="titulo-resenas">
					<div class="bloque__cabecera">
						<h2 id="titulo-resenas">Reseñas recibidas</h2>
						{#if totalResenas}
							<span class="bloque__nota">{resenas.length} de {totalResenas}</span>
						{/if}
					</div>
					{#if errorResenas}
						<Aviso variante="error">No se pudieron cargar las reseñas.</Aviso>
					{:else if resenas.length}
						<ul class="resenas__lista">
							{#each resenas as resena (resena.id)}
								<li class="resena">
									<Avatar
										nombre={resena.autor.username}
										foto={resena.autor.foto}
										tamano="sm"
										aria-hidden="true"
									/>
									<div class="resena__cuerpo">
										<p class="resena__cabecera">
											<a class="resena__autor" href={resolve(`/usuarios/${resena.autor.id}`)}
												>{resena.autor.username}</a
											>
											<Estrellas puntaje={resena.puntaje} />
											<span class="resena__contexto">
												{etiquetaRol(resena.rol)} ·
												<a href={resolve(`/pools/${resena.pool}`)}>{resena.pool_titulo}</a>
											</span>
										</p>
										{#if resena.comentario}
											<p class="resena__texto">{resena.comentario}</p>
										{/if}
										<p class="resena__fecha">{fechaHora(resena.creado)}</p>
									</div>
								</li>
							{/each}
						</ul>
						{#if siguienteResenas}
							<Boton variante="secundario" disabled={cargandoMas} onclick={verMasResenas}>
								{cargandoMas ? 'Cargando…' : 'Ver más reseñas'}
							</Boton>
						{/if}
					{:else}
						<p class="muted">Nadie lo calificó todavía.</p>
					{/if}
				</section>
			</Tarjeta>
		</div>
	</div>
{/if}

<style>
	.publico {
		display: grid;
		grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
		gap: var(--e-6);
		align-items: start;
	}

	.publico__lateral {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
	}

	.publico__tarjeta {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--e-2);
		padding: var(--e-6) var(--e-5);
		border-radius: var(--radio-lg);
		background: var(--melocoton);
		text-align: center;
	}

	.publico__tarjeta :global(.publico__avatar) {
		width: 112px;
		height: 112px;
		border: 4px solid var(--superficie);
		font-size: var(--texto-2xl);
	}

	.publico__nombre {
		margin: var(--e-2) 0 0;
		font-size: var(--texto-2xl);
		word-break: break-word;
	}

	.publico__meta {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.publico__puntaje {
		display: inline-flex;
		align-items: center;
		gap: var(--e-2);
		margin: var(--e-2) 0;
		padding: 0.35rem 0.9rem;
		border-radius: var(--radio-full);
		background: var(--superficie);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.publico__puntaje b {
		color: var(--tinta);
	}

	.publico__cifras {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--e-2);
		margin: 0;
	}

	.cifra {
		display: flex;
		flex-direction: column-reverse;
		align-items: center;
		padding: var(--e-3) var(--e-2);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--superficie);
		text-align: center;
	}

	.cifra dd {
		margin: 0;
		font-family: var(--fuente-display);
		font-size: var(--texto-xl);
		font-weight: 800;
	}

	.cifra dt {
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.en-comun {
		padding: var(--e-4);
	}

	.en-comun__titulo {
		margin-bottom: var(--e-2);
		font-size: var(--texto-md);
	}

	.en-comun__lista {
		margin: 0;
		padding-left: var(--e-4);
		font-size: var(--texto-sm);
	}

	.publico__principal {
		display: flex;
		flex-direction: column;
		gap: var(--e-6);
		min-width: 0;
	}

	.bloque__cabecera {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--e-3);
		margin-bottom: var(--e-4);
	}

	.bloque__nota {
		font-size: var(--texto-sm);
		color: var(--tinta-tenue);
	}

	.resenas {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--e-3);
		padding: var(--e-5);
	}

	.resenas .bloque__cabecera {
		align-self: stretch;
		margin-bottom: 0;
	}

	.resenas__lista {
		align-self: stretch;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.resena {
		display: flex;
		gap: var(--e-3);
		padding: var(--e-4) 0;
		border-top: 1px solid var(--linea);
	}

	.resena__cuerpo {
		min-width: 0;
	}

	.resena__cabecera {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2);
		margin: 0;
	}

	.resena__autor {
		font-weight: 700;
		color: var(--tinta);
	}

	.resena__contexto,
	.resena__fecha {
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.resena__texto {
		margin: var(--e-1) 0 0;
		color: var(--tinta-suave);
	}

	.resena__fecha {
		margin: var(--e-1) 0 0;
	}

	@media (max-width: 900px) {
		.publico {
			grid-template-columns: 1fr;
		}
	}
</style>
