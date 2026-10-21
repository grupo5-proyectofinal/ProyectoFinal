<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api } from '$lib/api.js';
	import { bandeja, refrescarBandeja } from '$lib/bandeja.svelte.js';
	import { mensajeError } from '$lib/eliminacion.js';
	import {
		PREFERENCIAS,
		PREFERENCIA_EMAIL,
		etiquetaTipo,
		textoNoLeidas,
		tiempoRelativo
	} from '$lib/notificaciones.js';
	import { session, updateMe } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	const FILTROS = [
		{ id: 'todas', texto: 'Todas' },
		{ id: 'no-leidas', texto: 'No leídas' }
	];

	let filtro = $state('todas');
	let avisos = $state([]);
	let siguiente = $state(null);
	let cargando = $state(true);
	let cargandoMas = $state(false);
	let error = $state('');
	let guardando = $state('');
	let pedido = 0;

	$effect(() => {
		if (session.access) cargar(filtro);
	});

	function query(filtroActivo, pagina) {
		return { leida: filtroActivo === 'no-leidas' ? 'false' : undefined, page: pagina };
	}

	async function cargar(filtroActivo) {
		const actual = ++pedido;
		cargando = true;
		error = '';
		try {
			const r = await api('/notificaciones/', { query: query(filtroActivo) });
			if (actual !== pedido) return;
			avisos = r.results;
			siguiente = r.next;
		} catch (e) {
			if (actual !== pedido) return;
			avisos = [];
			error = mensajeError(e);
		} finally {
			if (actual === pedido) cargando = false;
		}
	}

	async function verMas() {
		if (!siguiente) return;
		const actual = pedido;
		cargandoMas = true;
		try {
			const pagina = new URL(siguiente, window.location.origin).searchParams.get('page');
			const r = await api('/notificaciones/', { query: query(filtro, pagina) });
			if (actual !== pedido) return;
			avisos = [...avisos, ...r.results];
			siguiente = r.next;
		} catch (e) {
			notificar(mensajeError(e), 'error');
		} finally {
			cargandoMas = false;
		}
	}

	async function abrir(aviso) {
		if (!aviso.leida) {
			try {
				await api(`/notificaciones/${aviso.id}/leer/`, { method: 'POST' });
				aviso.leida = true;
				refrescarBandeja();
			} catch {
				// Si falla la marca igual se navega: el aviso queda sin leer.
			}
		}
		if (aviso.pool) goto(resolve(`/pools/${aviso.pool}`));
	}

	async function leerTodas() {
		try {
			await api('/notificaciones/leer-todas/', { method: 'POST' });
			for (const aviso of avisos) aviso.leida = true;
			if (filtro === 'no-leidas') avisos = [];
			bandeja.noLeidas = 0;
			notificar('Marcamos todas como leídas.');
		} catch (e) {
			notificar(mensajeError(e), 'error');
		}
	}

	async function cambiarPreferencia(clave, casilla) {
		const valor = casilla.checked;
		guardando = clave;
		try {
			await updateMe({ [clave]: valor });
			notificar('Preferencias guardadas.');
		} catch (e) {
			// No se guardó: la casilla vuelve a mostrar lo que sigue vigente.
			casilla.checked = !valor;
			notificar(mensajeError(e), 'error');
		} finally {
			guardando = '';
		}
	}

	const ICONOS = {
		estado: 'M3 8l9-5 9 5v8l-9 5-9-5zM3 8l9 5 9-5M12 13v8',
		mensaje: 'M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z',
		union: 'M15 19a6 6 0 0 0-12 0M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M19 8v6M16 11h6'
	};
</script>

<svelte:head>
	<title>Notificaciones — PoolShop</title>
</svelte:head>

<div class="bandeja">
	<div class="bandeja__principal">
		<div class="bandeja__cabecera">
			<div>
				<h1>Notificaciones</h1>
				<p class="muted">{textoNoLeidas(bandeja.noLeidas)}</p>
			</div>
			<div class="bandeja__acciones">
				<div class="filtros" role="group" aria-label="Filtrar notificaciones">
					{#each FILTROS as f (f.id)}
						<button
							type="button"
							class="filtros__boton"
							class:activo={filtro === f.id}
							aria-pressed={filtro === f.id}
							onclick={() => (filtro = f.id)}>{f.texto}</button
						>
					{/each}
				</div>
				<Boton variante="ghost" disabled={!bandeja.noLeidas} onclick={leerTodas}>
					Marcar todas como leídas
				</Boton>
			</div>
		</div>

		{#if cargando}
			<p class="muted" role="status">Cargando notificaciones…</p>
		{:else if error}
			<Aviso variante="error">{error}</Aviso>
		{:else if avisos.length}
			<Tarjeta>
				<ul class="avisos">
					{#each avisos as aviso (aviso.id)}
						<li>
							<button
								type="button"
								class="aviso"
								class:aviso--nuevo={!aviso.leida}
								onclick={() => abrir(aviso)}
							>
								<span class="aviso__icono aviso__icono--{aviso.tipo}" aria-hidden="true">
									<svg
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.8"
										stroke-linecap="round"
										stroke-linejoin="round"
									>
										<path d={ICONOS[aviso.tipo] ?? ICONOS.estado} />
									</svg>
								</span>
								<span class="aviso__cuerpo">
									<span class="aviso__titulo">
										{aviso.titulo}
										<span class="aviso__etiqueta">{etiquetaTipo(aviso)}</span>
									</span>
									{#if aviso.texto}<span class="aviso__texto">{aviso.texto}</span>{/if}
									<span class="aviso__fecha">{tiempoRelativo(aviso.actualizado)}</span>
								</span>
								{#if !aviso.leida}
									<span class="aviso__punto"><span class="sr-only">Sin leer</span></span>
								{/if}
							</button>
						</li>
					{/each}
				</ul>
			</Tarjeta>
			{#if siguiente}
				<div class="bandeja__mas">
					<Boton variante="secundario" disabled={cargandoMas} onclick={verMas}>
						{cargandoMas ? 'Cargando…' : 'Ver más'}
					</Boton>
				</div>
			{/if}
		{:else}
			<div class="vacio">
				<h2>{filtro === 'no-leidas' ? 'Estás al día' : 'Todavía no tenés notificaciones'}</h2>
				<p>
					Te avisamos acá cuando cambie el estado de un pool en el que participás o haya mensajes
					nuevos en su chat.
				</p>
				<Boton variante="primario" href={resolve('/pools')}>Explorar pools</Boton>
			</div>
		{/if}
	</div>

	<aside class="bandeja__lateral" aria-labelledby="titulo-preferencias">
		<Tarjeta>
			<div class="preferencias">
				<h2 id="titulo-preferencias" class="preferencias__titulo">Qué querés recibir</h2>
				{#if session.user}
					{#each PREFERENCIAS as pref (pref.clave)}
						<label class="preferencia">
							<span>
								<span class="preferencia__texto">{pref.texto}</span>
								<span class="preferencia__ayuda">{pref.ayuda}</span>
							</span>
							<input
								type="checkbox"
								checked={session.user[pref.clave]}
								disabled={guardando === pref.clave}
								onchange={(e) => cambiarPreferencia(pref.clave, e.currentTarget)}
							/>
						</label>
					{/each}
					<h3 class="preferencias__subtitulo">Canales</h3>
					<label class="preferencia">
						<span>
							<span class="preferencia__texto">En la app</span>
							<span class="preferencia__ayuda">Siempre activo para los avisos elegidos</span>
						</span>
						<input type="checkbox" checked disabled />
					</label>
					<label class="preferencia">
						<span>
							<span class="preferencia__texto">{PREFERENCIA_EMAIL.texto}</span>
							<span class="preferencia__ayuda">{PREFERENCIA_EMAIL.ayuda}</span>
						</span>
						<input
							type="checkbox"
							checked={session.user[PREFERENCIA_EMAIL.clave]}
							disabled={guardando === PREFERENCIA_EMAIL.clave}
							onchange={(e) => cambiarPreferencia(PREFERENCIA_EMAIL.clave, e.currentTarget)}
						/>
					</label>
				{:else}
					<p class="muted">Cargando preferencias…</p>
				{/if}
			</div>
		</Tarjeta>
	</aside>
</div>

<style>
	.bandeja {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(260px, 340px);
		gap: var(--e-6);
		align-items: start;
	}

	.bandeja__cabecera {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--e-4);
		margin-bottom: var(--e-5);
	}

	.bandeja__cabecera h1 {
		margin-bottom: var(--e-1);
	}

	.bandeja__cabecera p {
		margin: 0;
	}

	.bandeja__acciones {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3);
	}

	.filtros {
		display: flex;
		gap: var(--e-2);
	}

	.filtros__boton {
		min-height: 40px;
		padding: 0 1.1rem;
		border: 1px solid var(--linea-fuerte);
		border-radius: var(--radio-full);
		background: var(--superficie);
		color: var(--tinta);
		font: inherit;
		font-size: var(--texto-sm);
		cursor: pointer;
	}

	.filtros__boton.activo {
		border-color: var(--tinta);
		background: var(--tinta);
		color: var(--superficie);
		font-weight: 700;
	}

	.avisos {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.avisos li + li {
		border-top: 1px solid var(--linea);
	}

	.aviso {
		display: flex;
		align-items: flex-start;
		gap: var(--e-4);
		width: 100%;
		padding: var(--e-4) var(--e-5);
		border: 0;
		background: transparent;
		color: inherit;
		font: inherit;
		text-align: left;
		cursor: pointer;
	}

	.aviso:hover {
		background: var(--crema);
	}

	.aviso--nuevo {
		background: var(--melocoton);
	}

	.aviso__icono {
		display: grid;
		flex: none;
		place-items: center;
		width: 44px;
		height: 44px;
		border-radius: var(--radio-sm);
		background: var(--melocoton-fuerte);
		color: var(--marca);
	}

	.aviso__icono--mensaje,
	.aviso__icono--union {
		background: var(--tinte-ambar);
		color: var(--naranja-oscuro);
	}

	.aviso__icono svg {
		width: 20px;
		height: 20px;
	}

	.aviso__cuerpo {
		display: flex;
		flex: 1;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}

	.aviso__titulo {
		font-weight: 700;
	}

	.aviso__etiqueta {
		display: inline-block;
		margin-left: var(--e-2);
		padding: 1px 8px;
		border-radius: var(--radio-full);
		background: var(--melocoton-fuerte);
		color: var(--marca-fuerte);
		font-size: var(--texto-xs);
		font-weight: 700;
		vertical-align: middle;
	}

	.aviso__texto {
		color: var(--tinta-suave);
		overflow-wrap: anywhere;
	}

	.aviso__fecha {
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.aviso__punto {
		flex: none;
		width: 10px;
		height: 10px;
		margin-top: 6px;
		border-radius: 50%;
		background: var(--marca);
	}

	.bandeja__mas {
		display: flex;
		justify-content: center;
		margin-top: var(--e-4);
	}

	.preferencias {
		padding: var(--e-5);
	}

	.preferencias__titulo {
		margin-bottom: var(--e-4);
		font-size: var(--texto-lg);
	}

	.preferencias__subtitulo {
		margin: var(--e-4) 0 var(--e-2);
		padding-top: var(--e-4);
		border-top: 1px solid var(--linea);
		font-size: var(--texto-sm);
	}

	.preferencia {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-3);
		padding: var(--e-2) 0;
		cursor: pointer;
	}

	.preferencia > span {
		display: flex;
		flex-direction: column;
	}

	.preferencia__texto {
		font-size: var(--texto-sm);
	}

	.preferencia__ayuda {
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.preferencia input {
		flex: none;
		width: 20px;
		height: 20px;
		accent-color: var(--marca);
	}

	@media (max-width: 900px) {
		.bandeja {
			grid-template-columns: 1fr;
		}
	}
</style>
