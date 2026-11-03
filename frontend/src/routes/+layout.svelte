<script>
	import '../app.css';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { destinoGuardAdmin, esStaff, nombreUsuario } from '$lib/admin.js';
	import { bandeja, refrescarBandeja } from '$lib/bandeja.svelte.js';
	import { contadorCampana, etiquetaCampana } from '$lib/notificaciones.js';
	import Logo from '$lib/Logo.svelte';
	import { loadMe, logout, session } from '$lib/session.svelte.js';
	import { esTabAutenticada, navActiva, normalizarTab } from '$lib/pestanas.js';
	import Toaster from '$lib/Toaster.svelte';
	import Avatar from '$lib/ui/Avatar.svelte';
	import Boton from '$lib/ui/Boton.svelte';

	let { children } = $props();

	const PROTEGIDAS = ['/perfil', '/mis-pools', '/unidos', '/pools/nuevo', '/notificaciones'];
	// Cada cuánto se consulta el contador de la campana (pausado con la pestaña oculta).
	const INTERVALO_BANDEJA = 30000;
	const EDITAR = /^\/pools\/[^/]+\/editar$/;
	const ADMIN = /^\/admin(\/|$)/;

	const NAV = [
		{ href: '/', texto: 'Inicio', exacto: true, publico: true },
		{ href: '/pools', texto: 'Explorar', publico: true },
		{ href: '/pools?tab=mios', texto: 'Mis Pools', tab: 'mios' },
		{ href: '/admin/usuarios', texto: 'Admin', staff: true, prefijo: true }
	];

	let menuAbierto = $state(false);
	let menuUsuarioAbierto = $state(false);
	let botonMenu = $state();
	let botonUsuario = $state();
	let contenedorUsuario = $state();
	let termino = $state('');

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
			if (destino) goto(resolve(destino));
			return;
		}
		const tab = normalizarTab(page.url.searchParams.get('tab'));
		const protegida =
			PROTEGIDAS.some((p) => pathname === p || pathname.startsWith(`${p}/`)) ||
			EDITAR.test(pathname) ||
			(pathname === '/pools' && esTabAutenticada(tab));
		if (!session.access && protegida) goto(resolve('/login'));
	});

	$effect(() => {
		// Cierra los menús al cambiar de ruta.
		void page.url.pathname;
		menuAbierto = false;
		menuUsuarioAbierto = false;
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
		return navActiva(enlace, page.url.pathname, normalizarTab(page.url.searchParams.get('tab')));
	}

	function cerrarSesion() {
		logout();
		goto(resolve('/'));
	}

	function alTeclear(event) {
		if (event.key !== 'Escape') return;
		if (menuUsuarioAbierto) {
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
	}

	function buscar(event) {
		event.preventDefault();
		const q = termino.trim();
		goto(resolve(q ? `/pools?q=${encodeURIComponent(q)}` : '/pools'));
	}
</script>

<svelte:window onkeydown={alTeclear} onclick={alClicFuera} />

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

{#snippet buscador()}
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
			type="search"
			placeholder="Buscar pools, productos o usuarios…"
			aria-label="Buscar"
			bind:value={termino}
		/>
	</form>
{/snippet}

<header class="cabecera">
	<div class="contenedor cabecera__interior">
		<a class="marca" href={resolve('/')} aria-label="PoolShop — Inicio">
			<Logo class="marca--cabecera" />
		</a>

		<div class="cabecera__buscador">{@render buscador()}</div>

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
						Crear Pool
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

	<nav id="menu-movil" class="menu-movil" hidden={!menuAbierto} aria-label="Navegación principal">
		<div class="contenedor">
			<div class="menu-movil__buscador">{@render buscador()}</div>
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
			<a href={resolve('/pools/nuevo')}>Crear pool</a>
			<a href={resolve('/perfil')}>Mi perfil</a>
		</nav>
		<p class="pie__legal">© {new Date().getFullYear()} PoolShop</p>
	</div>
</footer>

<Toaster />

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
		border-bottom: 1px solid var(--linea);
	}

	.cabecera__interior {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-5);
		min-height: var(--alto-cabecera);
		padding-block: var(--e-2);
	}

	.marca {
		display: inline-flex;
		color: var(--tinta);
	}

	.marca:hover {
		text-decoration: none;
	}

	.cabecera__buscador {
		flex: 1 1 280px;
		max-width: 420px;
	}

	.buscar {
		display: flex;
		align-items: center;
		gap: 0.65rem;
		height: 44px;
		padding: 0 1rem;
		border: 1px solid var(--linea-fuerte);
		border-radius: var(--radio-sm);
		background: var(--crema);
	}

	.buscar:focus-within {
		outline: 2px solid var(--marca);
		outline-offset: 2px;
		border-color: var(--marca);
	}

	.buscar__icono {
		flex: none;
		width: 18px;
		height: 18px;
		color: var(--tinta-tenue);
	}

	.buscar__input {
		flex: 1;
		min-width: 0;
		height: 100%;
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
		gap: var(--e-5);
	}

	.nav__lista {
		display: flex;
		align-items: center;
		gap: 2px;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.nav__enlace {
		padding: 0.6rem 0.85rem;
		border-radius: var(--radio-sm);
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
		font-weight: 500;
	}

	.nav__enlace:hover {
		color: var(--tinta);
		text-decoration: none;
	}

	.nav__enlace.activo {
		color: var(--marca-fuerte);
		font-weight: 700;
		background: var(--melocoton);
	}

	.nav__sesion {
		display: flex;
		align-items: center;
		gap: var(--e-2);
		padding-left: var(--e-5);
		border-left: 1px solid var(--linea);
	}

	.campana {
		position: relative;
		display: grid;
		place-items: center;
		width: var(--alto-tap);
		height: var(--alto-tap);
		border-radius: var(--radio-full);
		color: var(--tinta-suave);
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
		gap: var(--e-2);
		min-height: var(--alto-tap);
		padding: 0.25rem 0.6rem 0.25rem 0.25rem;
		border: 1px solid transparent;
		border-radius: var(--radio-full);
		background: transparent;
		color: var(--tinta);
		font-family: inherit;
		font-size: var(--texto-sm);
		font-weight: 500;
		cursor: pointer;
		transition: background-color var(--transicion);
	}

	.usuario__boton:hover {
		background: var(--crema);
	}

	.usuario__boton::after {
		content: '';
		width: 0;
		height: 0;
		border-left: 4px solid transparent;
		border-right: 4px solid transparent;
		border-top: 5px solid var(--tinta-tenue);
		transition: transform var(--transicion);
	}

	.usuario__boton[aria-expanded='true']::after {
		transform: rotate(180deg);
	}

	.usuario__nombre {
		max-width: 14ch;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.usuario__menu {
		position: absolute;
		top: calc(100% + var(--e-2));
		right: 0;
		z-index: 60;
		min-width: 12rem;
		padding: var(--e-2);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--superficie);
		box-shadow: var(--sombra-md);
	}

	.usuario__enlace {
		display: block;
		width: 100%;
		padding: 0.55rem 0.75rem;
		border: 0;
		border-radius: var(--radio-sm);
		background: transparent;
		color: var(--tinta);
		font-family: inherit;
		font-size: var(--texto-sm);
		font-weight: 500;
		text-align: left;
		cursor: pointer;
	}

	.usuario__enlace:hover {
		background: var(--melocoton);
		color: var(--marca-fuerte);
		text-decoration: none;
	}

	.usuario__enlace.activo {
		color: var(--marca-fuerte);
	}

	.hamburguesa {
		display: none;
		flex-direction: column;
		justify-content: center;
		gap: 5px;
		width: var(--alto-tap);
		height: var(--alto-tap);
		padding: 0;
		border: 1px solid var(--linea-fuerte);
		border-radius: var(--radio-sm);
		background: var(--superficie);
		cursor: pointer;
	}

	.hamburguesa__linea {
		display: block;
		width: 18px;
		height: 2px;
		margin-inline: auto;
		border-radius: 2px;
		background: var(--tinta);
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
		border-top: 1px solid var(--linea);
		border-bottom: 1px solid var(--linea);
		background: var(--superficie);
		padding: var(--e-4) 0 var(--e-5);
		box-shadow: var(--sombra-md);
	}

	.menu-movil__buscador {
		margin-bottom: var(--e-3);
	}

	.menu-movil__lista {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.menu-movil__enlace {
		display: block;
		padding: 0.7rem 0.25rem;
		border-bottom: 1px solid var(--linea);
		color: var(--tinta);
		font-size: var(--texto-md);
		font-weight: 500;
	}

	.menu-movil__enlace:hover {
		text-decoration: none;
		color: var(--marca-fuerte);
	}

	.menu-movil__enlace.activo {
		color: var(--marca-fuerte);
	}

	.menu-movil__sesion {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		margin-top: var(--e-4);
	}

	.menu-movil__identidad {
		display: flex;
		align-items: center;
		gap: var(--e-3);
		padding: 0.35rem 0.25rem 0.7rem;
		border-bottom: 1px solid var(--linea);
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

	@media (max-width: 860px) {
		.nav-escritorio,
		.cabecera__buscador {
			display: none;
		}

		.hamburguesa {
			display: flex;
		}
	}
</style>
