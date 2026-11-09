<script>
	import '../app.css';
	import { tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api } from '$lib/api.js';
	import { destinoGuardAdmin, esStaff, nombreUsuario } from '$lib/admin.js';
	import { bandeja, refrescarBandeja } from '$lib/bandeja.svelte.js';
	import { contadorCampana, etiquetaCampana } from '$lib/notificaciones.js';
	import Logo from '$lib/Logo.svelte';
	import { loadMe, logout, session } from '$lib/session.svelte.js';
	import { urlLogin } from '$lib/sesion.js';
	import { esTabAutenticada, navActiva, normalizarTab } from '$lib/pestanas.js';
	import Toaster from '$lib/Toaster.svelte';
	import Confirmacion from '$lib/Confirmacion.svelte';
	import Avatar from '$lib/ui/Avatar.svelte';
	import Boton from '$lib/ui/Boton.svelte';

	let { children } = $props();

	const PROTEGIDAS = ['/perfil', '/mis-pools', '/unidos', '/pools/nuevo', '/notificaciones', '/comparar'];
	// Cada cuánto se consulta el contador de la campana (pausado con la pestaña oculta).
	const INTERVALO_BANDEJA = 30000;
	const EDITAR = /^\/pools\/[^/]+\/editar$/;
	const ADMIN = /^\/admin(\/|$)/;

	// "Mis pools" y "Mis uniones" viven como pestañas dentro de /pools: no se
	// repiten en el header.
	const NAV = [
		{ href: '/', texto: 'Inicio', exacto: true, publico: true },
		{ href: '/pools', texto: 'Explorar', publico: true },
		{ href: '/mayoristas', texto: 'Mayoristas', publico: true, prefijo: true },
		{ href: '/admin/usuarios', texto: 'Admin', staff: true, prefijo: true }
	];

	let menuAbierto = $state(false);
	let menuUsuarioAbierto = $state(false);
	let desplazado = $state(false);
	let botonMenu = $state();
	let botonUsuario = $state();
	let contenedorUsuario = $state();
	let termino = $state('');
	// Sugerencias del buscador: pools y personas mientras se escribe.
	let sugerencias = $state({ pools: [], perfiles: [] });
	let buscandoSugerencias = $state(false);
	let mostrarSugerencias = $state(false);
	let recientes = $state(leerRecientes());
	let pedidoSugerencias = 0;
	let temporizadorBusqueda;

	const CLAVE_RECIENTES = 'poolshop:buscadas';

	function leerRecientes() {
		if (typeof localStorage === 'undefined') return [];
		try {
			const guardadas = JSON.parse(localStorage.getItem(CLAVE_RECIENTES) ?? '[]');
			return Array.isArray(guardadas) ? guardadas.slice(0, 5) : [];
		} catch {
			return [];
		}
	}

	function guardarReciente(q) {
		if (!q) return;
		recientes = [q, ...recientes.filter((item) => item !== q)].slice(0, 5);
		try {
			localStorage.setItem(CLAVE_RECIENTES, JSON.stringify(recientes));
		} catch {
			// Sin almacenamiento: las sugerencias funcionan igual en esta sesión.
		}
	}

	function alEscribir() {
		clearTimeout(temporizadorBusqueda);
		mostrarSugerencias = true;
		const q = termino.trim();
		if (q.length < 2) {
			pedidoSugerencias += 1;
			buscandoSugerencias = false;
			sugerencias = { pools: [], perfiles: [] };
			return;
		}
		buscandoSugerencias = true;
		temporizadorBusqueda = setTimeout(() => buscarSugerencias(q), 250);
	}

	async function buscarSugerencias(q) {
		const actual = ++pedidoSugerencias;
		try {
			const [pools, perfiles] = await Promise.all([
				api('/pools/', { query: { q }, auth: false }),
				api('/usuarios/', { query: { q }, auth: false })
			]);
			if (actual !== pedidoSugerencias) return;
			sugerencias = {
				pools: (pools.results ?? []).slice(0, 4),
				perfiles: (perfiles.results ?? []).slice(0, 3)
			};
		} catch {
			if (actual === pedidoSugerencias) sugerencias = { pools: [], perfiles: [] };
		} finally {
			if (actual === pedidoSugerencias) buscandoSugerencias = false;
		}
	}

	function cerrarSugerencias() {
		mostrarSugerencias = false;
		clearTimeout(temporizadorBusqueda);
	}

	function elegirSugerencia(href, q) {
		guardarReciente(q);
		cerrarSugerencias();
		goto(resolve(href));
	}

	const visibles = $derived(
		NAV.filter(
			(enlace) => (session.access || enlace.publico) && (!enlace.staff || esStaff(session.user))
		)
	);

	// Identidad de sesión: nombre visible para el menú y el monograma.
	const nombreSesion = $derived(nombreUsuario(session.user));

	$effect(() => {
		const { pathname } = page.url;
		if (ADMIN.test(pathname)) {
			const destino = destinoGuardAdmin(session.access, session.user);
			if (destino) goto(resolve(destino === '/login' ? urlLogin(pathname, page.url.search) : destino));
			return;
		}
		const tab = normalizarTab(page.url.searchParams.get('tab'));
		const protegida =
			PROTEGIDAS.some((p) => pathname === p || pathname.startsWith(`${p}/`)) ||
			EDITAR.test(pathname) ||
			(pathname === '/pools' && esTabAutenticada(tab));
		// Vuelve a esta misma página después de iniciar sesión (?next=).
		if (!session.access && protegida) goto(resolve(urlLogin(pathname, page.url.search)));
	});

	$effect(() => {
		// Cierra los menús al cambiar de ruta.
		void page.url.pathname;
		menuAbierto = false;
		menuUsuarioAbierto = false;
		mostrarSugerencias = false;
		alDesplazar();
	});

	if (session.access) loadMe();

	$effect(() => {
		if (!session.access) {
			bandeja.noLeidas = 0;
			return;
		}
		refrescarBandeja();
		const intervalo = setInterval(() => {
			if (document.visibilityState === 'visible') refrescarBandeja();
		}, INTERVALO_BANDEJA);
		return () => clearInterval(intervalo);
	});

	// Al cambiar de ruta se actualiza el globito (p. ej. al volver de la bandeja).
	$effect(() => {
		void page.url.pathname;
		if (session.access) refrescarBandeja();
	});

	function activa(enlace) {
		return navActiva(enlace, page.url.pathname);
	}

	function cerrarSesion() {
		logout();
		goto(resolve('/'));
	}

	function alTeclear(event) {
		if (event.key !== 'Escape') return;
		if (mostrarSugerencias) {
			// Sin preventDefault, Escape en <input type="search"> lo vacía y el
			// evento input vuelve a abrir el panel con las búsquedas recientes.
			event.preventDefault();
			cerrarSugerencias();
		} else if (menuUsuarioAbierto) {
			menuUsuarioAbierto = false;
			botonUsuario?.focus();
		} else if (menuAbierto) {
			menuAbierto = false;
			botonMenu?.focus();
		}
	}

	function alClicFuera(event) {
		if (menuUsuarioAbierto && !contenedorUsuario?.contains(event.target)) {
			menuUsuarioAbierto = false;
		}
		if (menuAbierto && !event.target.closest?.('.cabecera')) {
			menuAbierto = false;
		}
		if (mostrarSugerencias && !event.target.closest?.('.buscador-panel')) {
			cerrarSugerencias();
		}
	}

	function alDesplazar() {
		desplazado = window.scrollY > 2;
	}

	function buscar(event) {
		event.preventDefault();
		const q = termino.trim();
		guardarReciente(q);
		cerrarSugerencias();
		goto(resolve(q ? `/pools?q=${encodeURIComponent(q)}` : '/pools'));
	}

	// En mobile el buscador vive dentro del menú: este atajo lo abre y enfoca.
	async function abrirBusquedaMovil() {
		menuAbierto = true;
		await tick();
		document.getElementById('buscador-movil')?.focus();
	}
</script>

<svelte:window onkeydown={alTeclear} onclick={alClicFuera} onscroll={alDesplazar} />

<a class="saltar" href="#contenido">Saltar al contenido</a>

{#snippet identidad()}
	<Avatar nombre={nombreSesion} foto={session.user?.foto} tamano="sm" aria-hidden="true" />
	{#if nombreSesion}
		<span class="usuario__nombre">{nombreSesion}</span>
	{/if}
{/snippet}

{#snippet campana()}
	<a
		class="campana"
		class:activo={page.url.pathname === '/notificaciones'}
		href={resolve('/notificaciones')}
		aria-label={etiquetaCampana(bandeja.noLeidas)}
		aria-current={page.url.pathname === '/notificaciones' ? 'page' : undefined}
	>
		<svg
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
			<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
		</svg>
		{#if contadorCampana(bandeja.noLeidas)}
			<span class="campana__contador" aria-hidden="true">{contadorCampana(bandeja.noLeidas)}</span>
		{/if}
	</a>
{/snippet}

{#snippet buscador(id)}
	<div class="buscador-panel">
		<form class="buscar" role="search" onsubmit={buscar}>
			<svg
				class="buscar__icono"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				aria-hidden="true"
			>
				<circle cx="11" cy="11" r="7"></circle>
				<path d="M20 20l-3.5-3.5"></path>
			</svg>
			<input
				class="buscar__input"
				id={id}
				type="search"
				placeholder="Buscar pools o personas…"
				aria-label="Buscar"
				aria-controls={`${id}-lista`}
				autocomplete="off"
				bind:value={termino}
				oninput={alEscribir}
				onfocus={() => (mostrarSugerencias = true)}
			/>
		</form>
		{#if mostrarSugerencias}
			<div class="buscador-panel__lista" id={`${id}-lista`} aria-live="polite">
				{#if termino.trim().length < 2}
					{#if recientes.length}
						<p class="buscador-panel__titulo">Búsquedas recientes</p>
						<ul class="buscador-panel__grupo">
							{#each recientes as q (q)}
								<li>
									<button
										type="button"
										class="buscador-panel__item"
										onclick={() =>
											elegirSugerencia(`/pools?q=${encodeURIComponent(q)}`, q)}
									>
										<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
											<circle cx="12" cy="12" r="9" />
											<path d="M12 7v5l3 2" />
										</svg>
										<span>{q}</span>
									</button>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="buscador-panel__vacio">
							Buscá pools por título, producto o ciudad, o personas por su usuario.
						</p>
					{/if}
				{:else if buscandoSugerencias}
					<p class="buscador-panel__vacio" role="status">Buscando…</p>
				{:else}
					{#if sugerencias.pools.length}
						<p class="buscador-panel__titulo">Pools</p>
						<ul class="buscador-panel__grupo">
							{#each sugerencias.pools as pool (pool.id)}
								<li>
									<button
										type="button"
										class="buscador-panel__item"
										onclick={() => elegirSugerencia(`/pools/${pool.id}`, termino.trim())}
									>
										<span class="buscador-panel__nombre">{pool.titulo}</span>
										<span class="buscador-panel__meta">
											{pool.categoria_nombre}{#if pool.ciudad} · {pool.ciudad}{/if}
										</span>
									</button>
								</li>
							{/each}
						</ul>
					{/if}
					{#if sugerencias.perfiles.length}
						<p class="buscador-panel__titulo">Personas</p>
						<ul class="buscador-panel__grupo">
							{#each sugerencias.perfiles as perfil (perfil.id)}
								<li>
									<button
										type="button"
										class="buscador-panel__item"
										onclick={() => elegirSugerencia(`/usuarios/${perfil.id}`, termino.trim())}
									>
										<span class="buscador-panel__nombre">@{perfil.username}</span>
										{#if perfil.ciudad}
											<span class="buscador-panel__meta">{perfil.ciudad}</span>
										{/if}
									</button>
								</li>
							{/each}
						</ul>
					{/if}
					{#if !sugerencias.pools.length && !sugerencias.perfiles.length}
						<p class="buscador-panel__vacio">
							No encontramos resultados para “{termino.trim()}”.
						</p>
					{/if}
				{/if}
				{#if termino.trim().length >= 2}
					<button
						type="button"
						class="buscador-panel__todos"
						onclick={() =>
							elegirSugerencia(`/pools?q=${encodeURIComponent(termino.trim())}`, termino.trim())}
					>
						Ver todos los resultados para “{termino.trim()}”
					</button>
				{/if}
			</div>
		{/if}
	</div>
{/snippet}

<header class="cabecera" class:desplazada={desplazado}>
	<div class="contenedor cabecera__interior">
		<a class="marca" href={resolve('/')} aria-label="PoolShop — Inicio">
			<Logo class="marca--cabecera" />
		</a>

		<div class="cabecera__buscador">{@render buscador('buscador-escritorio')}</div>

		<nav class="nav-escritorio" aria-label="Navegación principal">
			<ul class="nav__lista">
				{#each visibles as enlace (enlace.href)}
					<li>
						<a
							class="nav__enlace"
							class:activo={activa(enlace)}
							href={resolve(enlace.href)}
							aria-current={activa(enlace) ? 'page' : undefined}>{enlace.texto}</a
						>
					</li>
				{/each}
			</ul>
			<div class="nav__sesion">
				{#if session.access}
					<Boton variante="primario" href={resolve('/pools/nuevo')}>
						<!-- El mockup (17) muestra el "+" en el CTA; tamaño explícito para que no quede 0×0. -->
						<svg
							width="18"
							height="18"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							aria-hidden="true"
						>
							<circle cx="12" cy="12" r="9.5" />
							<path d="M12 8v8M8 12h8" />
						</svg>
						Crear pool
					</Boton>
					{@render campana()}
					<div class="usuario" bind:this={contenedorUsuario}>
						<button
							class="usuario__boton"
							type="button"
							bind:this={botonUsuario}
							aria-expanded={menuUsuarioAbierto}
							aria-controls="menu-usuario"
							aria-label={nombreSesion ? undefined : 'Menú de cuenta'}
							onclick={() => (menuUsuarioAbierto = !menuUsuarioAbierto)}
						>
							{@render identidad()}
							<svg
								class="usuario__chevron"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2.4"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
							>
								<path d="m6 9 6 6 6-6" />
							</svg>
						</button>
						<div id="menu-usuario" class="usuario__menu" hidden={!menuUsuarioAbierto}>
							<a
								class="usuario__enlace"
								class:activo={activa({ href: '/perfil' })}
								href={resolve('/perfil')}
								aria-current={activa({ href: '/perfil' }) ? 'page' : undefined}
								onclick={() => (menuUsuarioAbierto = false)}
							>
								Mi perfil
							</a>
							<a
								class="usuario__enlace"
								href={resolve('/comparar')}
								onclick={() => (menuUsuarioAbierto = false)}
							>
								Comparar costos
							</a>
							{#if session.user}
								<a
									class="usuario__enlace"
									href={resolve(`/usuarios/${session.user.id}`)}
									onclick={() => (menuUsuarioAbierto = false)}
								>
									Ver mi perfil público
								</a>
							{/if}
							<a
								class="usuario__enlace"
								href={resolve('/notificaciones')}
								onclick={() => (menuUsuarioAbierto = false)}
							>
								Notificaciones
							</a>
							<button class="usuario__enlace" type="button" onclick={cerrarSesion}>
								Cerrar sesión
							</button>
						</div>
					</div>
				{:else}
					<Boton variante="ghost" tamano="sm" href={resolve('/login')}>Ingresar</Boton>
					<Boton variante="primario" tamano="sm" href={resolve('/registro')}>Crear cuenta</Boton>
				{/if}
			</div>
		</nav>

		<div class="acciones-movil">
			<button
				class="buscar-movil"
				type="button"
				aria-label="Abrir buscador"
				onclick={abrirBusquedaMovil}
			>
				<svg
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					aria-hidden="true"
				>
					<circle cx="11" cy="11" r="7" />
					<path d="M20 20l-3.5-3.5" />
				</svg>
			</button>

			<button
				class="hamburguesa"
				type="button"
				bind:this={botonMenu}
				aria-expanded={menuAbierto}
				aria-controls="menu-movil"
				aria-label={menuAbierto ? 'Cerrar menú' : 'Abrir menú'}
				onclick={() => (menuAbierto = !menuAbierto)}
			>
				<span class="hamburguesa__linea"></span>
				<span class="hamburguesa__linea"></span>
				<span class="hamburguesa__linea"></span>
			</button>
		</div>
	</div>

	<nav id="menu-movil" class="menu-movil" hidden={!menuAbierto} aria-label="Navegación principal">
		<div class="contenedor">
			<div class="menu-movil__buscador">{@render buscador('buscador-movil')}</div>
			<ul class="menu-movil__lista">
				{#each visibles as enlace (enlace.href)}
					<li>
						<a
							class="menu-movil__enlace"
							class:activo={activa(enlace)}
							href={resolve(enlace.href)}
							aria-current={activa(enlace) ? 'page' : undefined}>{enlace.texto}</a
						>
					</li>
				{/each}
			</ul>
			<div class="menu-movil__sesion">
				{#if session.access}
					<div class="menu-movil__identidad">{@render identidad()}</div>
					<a class="menu-movil__enlace" href={resolve('/perfil')}>Mi perfil</a>
					<a class="menu-movil__enlace" href={resolve('/comparar')}>Comparar costos</a>
					<a class="menu-movil__enlace" href={resolve('/notificaciones')}>
						{etiquetaCampana(bandeja.noLeidas)}
					</a>
					<Boton variante="secundario" bloque onclick={cerrarSesion}>Cerrar sesión</Boton>
				{:else}
					<Boton variante="secundario" bloque href={resolve('/login')}>Ingresar</Boton>
					<Boton variante="primario" bloque href={resolve('/registro')}>Crear cuenta</Boton>
				{/if}
			</div>
		</div>
	</nav>
</header>

<main id="contenido" tabindex="-1">
	<div class="contenedor">
		{@render children()}
	</div>
</main>

<footer class="pie">
	<div class="contenedor pie__interior">
		<div class="pie__marca">
			<Logo class="marca--pie" />
			<p>Compras colectivas entre vecinos, al por mayor.</p>
		</div>
		<nav class="pie__nav" aria-label="Navegación del pie">
			<a href={resolve('/pools')}>Explorar</a>
			<a href={resolve(session.access ? '/pools/nuevo' : '/registro')}>
				{session.access ? 'Crear pool' : 'Crear cuenta'}
			</a>
			<a href={resolve(session.access ? '/perfil' : '/login')}>
				{session.access ? 'Mi perfil' : 'Ingresar'}
			</a>
		</nav>
		<p class="pie__legal">© {new Date().getFullYear()} PoolShop</p>
	</div>
</footer>

<Toaster />
<Confirmacion />

<style>
	.saltar {
		position: absolute;
		left: var(--e-4);
		top: -100%;
		z-index: 100;
		padding: 0.6rem 1rem;
		border-radius: var(--radio-sm);
		background: var(--marca);
		color: #fff;
		font-weight: 700;
		transition: top var(--transicion);
	}

	.saltar:focus {
		top: var(--e-3);
		text-decoration: none;
	}

	.cabecera {
		position: sticky;
		top: 0;
		z-index: 50;
		background: var(--fondo);
		background: color-mix(in srgb, var(--fondo) 92%, transparent);
		border-bottom: 1px solid transparent;
		backdrop-filter: blur(14px) saturate(1.35);
		-webkit-backdrop-filter: blur(14px) saturate(1.35);
		transition:
			background-color var(--transicion),
			border-color var(--transicion),
			box-shadow var(--transicion);
	}

	/* Filo de marca: da identidad sin cargar la barra. */
	.cabecera::before {
		content: '';
		position: absolute;
		inset: 0 0 auto 0;
		height: 3px;
		background: linear-gradient(90deg, var(--marca), var(--acento-naranja));
	}

	.cabecera.desplazada {
		background: var(--fondo);
		background: color-mix(in srgb, var(--fondo) 86%, transparent);
		border-bottom-color: var(--linea);
		box-shadow: 0 12px 28px -24px rgba(31, 21, 18, 0.55);
	}

	.cabecera__interior {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: clamp(0.9rem, 1.6vw, 1.35rem);
		min-height: var(--alto-cabecera);
		padding-block: var(--e-2);
	}

	.marca {
		display: inline-flex;
		flex: none;
		color: var(--tinta);
		transition: opacity var(--transicion);
	}

	.marca:hover {
		text-decoration: none;
		opacity: 0.86;
	}

	.cabecera__buscador {
		flex: 1 1 260px;
		max-width: 460px;
	}

	.buscador-panel {
		position: relative;
	}

	.buscador-panel__lista {
		position: absolute;
		top: calc(100% + 6px);
		left: 0;
		right: 0;
		z-index: 70;
		max-height: min(24rem, 70vh);
		overflow-y: auto;
		padding: var(--e-2);
		border: 1px solid var(--linea);
		border-radius: 16px;
		background: var(--superficie);
		box-shadow: var(--sombra-lg);
		transform-origin: top center;
		animation: aparecer 150ms cubic-bezier(0.2, 0.6, 0.3, 1) both;
	}

	.buscador-panel__titulo {
		margin: var(--e-2) var(--e-2) var(--e-1);
		font-size: var(--texto-xs);
		font-weight: 700;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--tinta-tenue);
	}

	.buscador-panel__grupo {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.buscador-panel__item {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 2px;
		width: 100%;
		min-height: var(--alto-tap);
		padding: 0.45rem 0.65rem;
		border: 0;
		border-radius: var(--radio-sm);
		background: transparent;
		color: var(--tinta);
		font: inherit;
		text-align: left;
		cursor: pointer;
	}

	.buscador-panel__item:has(svg) {
		flex-direction: row;
		align-items: center;
		gap: 0.6rem;
	}

	.buscador-panel__item:hover,
	.buscador-panel__item:focus-visible {
		background: var(--melocoton);
	}

	.buscador-panel__item svg {
		flex: none;
		width: 16px;
		height: 16px;
		color: var(--tinta-tenue);
	}

	.buscador-panel__nombre {
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.buscador-panel__meta {
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.buscador-panel__vacio {
		margin: 0;
		padding: var(--e-3) var(--e-2);
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
	}

	.buscador-panel__todos {
		display: block;
		width: 100%;
		min-height: var(--alto-tap);
		margin-top: var(--e-1);
		padding: 0.6rem 0.65rem;
		border: 0;
		border-top: 1px solid var(--linea);
		background: transparent;
		color: var(--marca-fuerte);
		font: inherit;
		font-size: var(--texto-sm);
		font-weight: 700;
		text-align: left;
		cursor: pointer;
	}

	.buscador-panel__todos:hover {
		text-decoration: underline;
	}

	.buscar {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		height: 44px;
		padding: 0 1rem 0 1.05rem;
		border: 1px solid var(--linea);
		border-radius: var(--radio-full);
		background: var(--crema);
		transition:
			border-color var(--transicion),
			background-color var(--transicion),
			box-shadow var(--transicion);
	}

	.buscar:hover {
		border-color: color-mix(in srgb, var(--linea-control) 55%, var(--linea));
		background: var(--superficie);
	}

	.buscar:focus-within {
		outline: none;
		border-color: var(--marca);
		background: var(--superficie);
		box-shadow: 0 0 0 4px color-mix(in srgb, var(--marca) 12%, transparent);
	}

	.buscar__icono {
		flex: none;
		width: 18px;
		height: 18px;
		color: var(--tinta-tenue);
		transition: color var(--transicion);
	}

	.buscar:focus-within .buscar__icono {
		color: var(--marca);
	}

	.buscar__input {
		flex: 1;
		min-width: 0;
		height: 100%;
		padding: 0;
		border: 0;
		outline: 0;
		background: transparent;
		font: inherit;
		font-size: var(--texto-sm);
		color: var(--tinta);
	}

	.buscar__input::placeholder {
		color: var(--tinta-tenue);
	}

	.nav-escritorio {
		display: flex;
		align-items: center;
		gap: clamp(0.6rem, 1.1vw, 1rem);
		flex: none;
	}

	.nav__lista {
		display: flex;
		align-items: center;
		gap: 2px;
		margin: 0;
		padding: 3px;
		list-style: none;
		border-radius: var(--radio-full);
		background: var(--crema);
	}

	.nav__enlace {
		padding: 0.5rem 0.7rem;
		border-radius: var(--radio-full);
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
		font-weight: 600;
		white-space: nowrap;
		transition:
			background-color var(--transicion),
			color var(--transicion),
			box-shadow var(--transicion);
	}

	.nav__enlace:hover {
		color: var(--tinta);
		background: color-mix(in srgb, var(--fondo) 65%, transparent);
		text-decoration: none;
	}

	.nav__enlace.activo {
		color: var(--marca-fuerte);
		font-weight: 700;
		background: var(--superficie);
		box-shadow: var(--sombra-sm);
	}

	.nav__sesion {
		display: flex;
		align-items: center;
		gap: var(--e-2);
		padding-left: clamp(0.75rem, 1.4vw, 1.25rem);
		border-left: 1px solid var(--linea);
	}

	.nav__sesion :global(.ui-boton--primario) {
		border-radius: var(--radio-full);
		box-shadow: 0 7px 16px -9px rgba(180, 35, 24, 0.75);
	}

	.nav__sesion :global(.ui-boton--primario):hover {
		box-shadow: 0 9px 20px -9px rgba(180, 35, 24, 0.8);
	}

	.campana {
		position: relative;
		display: grid;
		place-items: center;
		width: var(--alto-tap);
		height: var(--alto-tap);
		border-radius: var(--radio-full);
		color: var(--tinta-suave);
		transition:
			background-color var(--transicion),
			color var(--transicion);
	}

	.campana:hover,
	.campana.activo {
		background: var(--melocoton);
		color: var(--marca-fuerte);
		text-decoration: none;
	}

	.campana svg {
		width: 22px;
		height: 22px;
	}

	.campana__contador {
		position: absolute;
		top: 4px;
		right: 2px;
		min-width: 18px;
		height: 18px;
		padding: 0 4px;
		border: 2px solid var(--fondo);
		border-radius: var(--radio-full);
		background: var(--marca);
		color: #fff;
		font-size: 10px;
		font-weight: 700;
		line-height: 14px;
		text-align: center;
	}

	.usuario {
		position: relative;
	}

	.usuario__boton {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		min-height: var(--alto-tap);
		padding: 0.22rem 0.55rem 0.22rem 0.25rem;
		border: 1px solid var(--linea);
		border-radius: var(--radio-full);
		background: var(--superficie);
		color: var(--tinta);
		font-family: inherit;
		font-size: var(--texto-sm);
		font-weight: 600;
		cursor: pointer;
		box-shadow: var(--sombra-sm);
		transition:
			background-color var(--transicion),
			border-color var(--transicion),
			box-shadow var(--transicion);
	}

	.usuario__boton:hover {
		background: var(--crema);
		border-color: color-mix(in srgb, var(--linea-control) 55%, var(--linea));
	}

	.usuario__boton[aria-expanded='true'] {
		background: var(--crema);
		border-color: var(--marca);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--marca) 12%, transparent);
	}

	.usuario__chevron {
		flex: none;
		width: 14px;
		height: 14px;
		color: var(--tinta-tenue);
		transition: transform var(--transicion);
	}

	.usuario__boton[aria-expanded='true'] .usuario__chevron {
		transform: rotate(180deg);
	}

	.usuario__nombre {
		max-width: 10ch;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.usuario__menu {
		position: absolute;
		top: calc(100% + 0.6rem);
		right: 0;
		z-index: 60;
		min-width: 14rem;
		padding: 0.4rem;
		border: 1px solid var(--linea);
		border-radius: 16px;
		background: var(--superficie);
		box-shadow: var(--sombra-lg);
		transform-origin: top right;
		animation: aparecer 150ms cubic-bezier(0.2, 0.6, 0.3, 1) both;
	}

	.usuario__enlace {
		display: block;
		width: 100%;
		padding: 0.6rem 0.7rem;
		border: 0;
		border-radius: 10px;
		background: transparent;
		color: var(--tinta);
		font-family: inherit;
		font-size: var(--texto-sm);
		font-weight: 600;
		text-align: left;
		cursor: pointer;
		transition:
			background-color var(--transicion),
			color var(--transicion);
	}

	.usuario__enlace:hover {
		background: var(--crema);
		color: var(--marca-fuerte);
		text-decoration: none;
	}

	.usuario__enlace.activo {
		background: var(--melocoton);
		color: var(--marca-fuerte);
	}

	/* Cerrar sesión queda separado del resto de las acciones. */
	.usuario__menu button.usuario__enlace {
		margin-top: 0.3rem;
		padding-top: 0.7rem;
		border-top: 1px solid var(--linea);
		color: var(--tinta-suave);
	}

	/* En escritorio no ocupa lugar: antes dejaba un hueco de separación de más. */
	.acciones-movil {
		display: none;
		align-items: center;
		gap: var(--e-2);
		flex: none;
	}

	.hamburguesa {
		display: none;
		flex-direction: column;
		justify-content: center;
		gap: 5px;
		width: var(--alto-tap);
		height: var(--alto-tap);
		padding: 0;
		border: 1px solid transparent;
		border-radius: var(--radio-sm);
		background: var(--crema);
		color: var(--tinta);
		cursor: pointer;
		transition:
			background-color var(--transicion),
			color var(--transicion);
	}

	.buscar-movil {
		display: none;
		place-items: center;
		width: var(--alto-tap);
		height: var(--alto-tap);
		border: 1px solid transparent;
		border-radius: var(--radio-sm);
		background: var(--crema);
		color: var(--tinta-suave);
		cursor: pointer;
		transition:
			background-color var(--transicion),
			color var(--transicion);
	}

	.hamburguesa:hover,
	.buscar-movil:hover {
		background: var(--melocoton);
		color: var(--marca-fuerte);
	}

	.buscar-movil svg {
		width: 20px;
		height: 20px;
	}

	.hamburguesa__linea {
		display: block;
		width: 18px;
		height: 2px;
		margin-inline: auto;
		border-radius: 2px;
		background: currentColor;
		transition: transform var(--transicion), opacity var(--transicion);
	}

	.hamburguesa[aria-expanded='true'] .hamburguesa__linea:nth-child(1) {
		transform: translateY(7px) rotate(45deg);
	}

	.hamburguesa[aria-expanded='true'] .hamburguesa__linea:nth-child(2) {
		opacity: 0;
	}

	.hamburguesa[aria-expanded='true'] .hamburguesa__linea:nth-child(3) {
		transform: translateY(-7px) rotate(-45deg);
	}

	.menu-movil {
		max-height: calc(100vh - var(--alto-cabecera));
		max-height: calc(100dvh - var(--alto-cabecera));
		overflow-y: auto;
		overscroll-behavior: contain;
		border-top: 1px solid var(--linea);
		border-bottom: 1px solid var(--linea);
		background: var(--superficie);
		padding: var(--e-4) 0 var(--e-5);
		box-shadow: 0 24px 40px -30px rgba(31, 21, 18, 0.5);
		animation: aparecer 180ms cubic-bezier(0.2, 0.6, 0.3, 1) both;
	}

	.menu-movil__buscador {
		margin-bottom: var(--e-3);
	}

	.menu-movil__lista {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.menu-movil__enlace {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-2);
		padding: 0.75rem 0.7rem;
		border-radius: var(--radio-sm);
		color: var(--tinta);
		font-size: var(--texto-md);
		font-weight: 600;
		transition:
			background-color var(--transicion),
			color var(--transicion);
	}

	.menu-movil__enlace::after {
		content: '';
		width: 0.45rem;
		height: 0.45rem;
		border-right: 2px solid currentColor;
		border-bottom: 2px solid currentColor;
		transform: rotate(-45deg);
		opacity: 0.4;
	}

	.menu-movil__enlace:hover,
	.menu-movil__enlace.activo {
		background: var(--crema);
		color: var(--marca-fuerte);
		text-decoration: none;
	}

	.menu-movil__sesion {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		margin-top: var(--e-4);
		padding-top: var(--e-4);
		border-top: 1px solid var(--linea);
	}

	.menu-movil__identidad {
		display: flex;
		align-items: center;
		gap: var(--e-3);
		padding: 0.65rem 0.8rem;
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--crema);
		font-weight: 600;
	}

	main {
		padding-block: clamp(2rem, 5vw, 3.25rem);
		scroll-margin-top: var(--alto-cabecera);
	}

	main:focus {
		outline: none;
	}

	main:focus-visible {
		outline: 2px solid var(--marca);
		outline-offset: -3px;
	}

	.pie {
		margin-top: var(--e-9);
		border-top: 1px solid var(--linea);
		background: var(--crema);
	}

	.pie__interior {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-5);
		padding-block: var(--e-6);
	}

	.pie__marca p {
		margin: var(--e-2) 0 0;
		max-width: 34ch;
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
	}

	.pie__nav {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-4);
	}

	.pie__nav a {
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
	}

	.pie__nav a:hover {
		color: var(--marca-fuerte);
	}

	.pie__legal {
		margin: 0;
		color: var(--tinta-tenue);
		font-size: var(--texto-xs);
	}

	/* En pantallas medianas el nombre cede lugar al buscador y la navegación. */
	@media (max-width: 1279px) {
		/* Solo en la barra: en el menú móvil el nombre sigue siendo la identidad. */
		.usuario__boton .usuario__nombre {
			display: none;
		}
	}

	@media (max-width: 1180px) {
		.nav-escritorio,
		.cabecera__buscador {
			display: none;
		}

		.acciones-movil {
			display: flex;
		}

		.hamburguesa {
			display: flex;
		}

		.buscar-movil {
			display: grid;
		}
	}

	@media (max-width: 420px) {
		.cabecera__interior {
			gap: var(--e-3);
		}
	}
</style>
