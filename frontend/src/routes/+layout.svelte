<script>
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { loadMe, logout, session } from '$lib/session.svelte.js';
	import Toaster from '$lib/Toaster.svelte';

	let { children } = $props();

	const PROTEGIDAS = ['/perfil', '/mis-pools', '/unidos', '/pools/nuevo'];
	const EDITAR = /^\/pools\/[^/]+\/editar$/;

	const NAV = [
		{ href: '/', texto: 'Inicio', exacto: true, publico: true },
		{ href: '/pools', texto: 'Pools', publico: true },
		{ href: '/pools/nuevo', texto: 'Crear pool' },
		{ href: '/mis-pools', texto: 'Mis Pools' },
		{ href: '/unidos', texto: 'Unidos' }
	];

	let menuAbierto = $state(false);
	let botonMenu = $state();

	const visibles = $derived(session.access ? NAV : NAV.filter((enlace) => enlace.publico));

	$effect(() => {
		const { pathname } = page.url;
		const protegida =
			PROTEGIDAS.some((p) => pathname === p || pathname.startsWith(`${p}/`)) ||
			EDITAR.test(pathname);
		if (!session.access && protegida) goto(resolve('/login'));
	});

	$effect(() => {
		// Cierra el menú móvil al cambiar de ruta.
		void page.url.pathname;
		menuAbierto = false;
	});

	if (session.access) loadMe();

	function activa(enlace) {
		const { pathname } = page.url;
		if (enlace.exacto) return pathname === enlace.href;
		if (enlace.href === '/pools') {
			return pathname === '/pools' || (pathname.startsWith('/pools/') && pathname !== '/pools/nuevo');
		}
		return pathname === enlace.href;
	}

	function cerrarSesion() {
		logout();
		goto(resolve('/'));
	}

	function alTeclear(event) {
		if (event.key === 'Escape' && menuAbierto) {
			menuAbierto = false;
			botonMenu?.focus();
		}
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<svelte:window onkeydown={alTeclear} />

<a class="saltar" href="#contenido">Saltar al contenido</a>

<header class="cabecera">
	<div class="contenedor cabecera__interior">
		<a class="marca" href={resolve('/')}>PoolShop</a>

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
					<a class="nav__enlace" href={resolve('/perfil')} aria-current={activa({ href: '/perfil' }) ? 'page' : undefined}>
						Mi perfil
					</a>
					<button class="btn btn--ghost btn--sm" type="button" onclick={cerrarSesion}>
						Cerrar sesión
					</button>
				{:else}
					<a class="btn btn--ghost btn--sm" href={resolve('/login')}>Ingresar</a>
					<a class="btn btn--primario btn--sm" href={resolve('/registro')}>Crear cuenta</a>
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
						<a class="menu-movil__enlace" href={resolve('/perfil')}>Mi perfil</a>
						<button class="btn btn--secundario btn--bloque" type="button" onclick={cerrarSesion}>
							Cerrar sesión
						</button>
					{:else}
						<a class="btn btn--secundario btn--bloque" href={resolve('/login')}>Ingresar</a>
						<a class="btn btn--primario btn--bloque" href={resolve('/registro')}>Crear cuenta</a>
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
			<span class="marca marca--pie">PoolShop</span>
			<p>Compras colectivas entre vecinos, al por mayor.</p>
		</div>
		<nav class="pie__nav" aria-label="Navegación del pie">
			<a href={resolve('/pools')}>Pools</a>
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
		background: var(--acento);
		color: #fff;
		font-weight: 600;
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
		background: rgba(245, 243, 238, 0.88);
		backdrop-filter: blur(12px);
		border-bottom: 1px solid var(--linea);
	}

	.cabecera__interior {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-5);
		min-height: var(--alto-cabecera);
	}

	.marca {
		font-family: var(--fuente-display);
		font-size: 1.35rem;
		font-weight: 600;
		letter-spacing: -0.025em;
		color: var(--tinta);
	}

	.marca::after {
		content: '.';
		color: var(--acento);
	}

	.marca:hover {
		text-decoration: none;
	}

	.marca--pie {
		font-size: 1.2rem;
	}

	.nav-escritorio {
		display: flex;
		align-items: center;
		gap: var(--e-5);
	}

	.nav__lista {
		display: flex;
		align-items: center;
		gap: var(--e-5);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.nav__enlace {
		position: relative;
		padding: 0.35rem 0;
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
		font-weight: 500;
	}

	.nav__enlace:hover {
		color: var(--tinta);
		text-decoration: none;
	}

	.nav__enlace.activo {
		color: var(--tinta);
	}

	.nav__enlace.activo::after {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		height: 2px;
		border-radius: 2px;
		background: var(--acento);
	}

	.nav__sesion {
		display: flex;
		align-items: center;
		gap: var(--e-2);
		padding-left: var(--e-5);
		border-left: 1px solid var(--linea);
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
		color: var(--acento);
	}

	.menu-movil__enlace.activo {
		color: var(--acento);
	}

	.menu-movil__sesion {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		margin-top: var(--e-4);
	}

	main {
		padding-block: clamp(2rem, 5vw, 3.25rem);
		scroll-margin-top: var(--alto-cabecera);
	}

	main:focus {
		outline: none;
	}

	main:focus-visible {
		outline: 2px solid var(--acento);
		outline-offset: -3px;
	}

	.pie {
		margin-top: var(--e-9);
		border-top: 1px solid var(--linea);
		background: var(--superficie-alt);
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
		color: var(--acento);
	}

	.pie__legal {
		margin: 0;
		color: var(--tinta-tenue);
		font-size: var(--texto-xs);
	}

	@media (max-width: 860px) {
		.nav-escritorio {
			display: none;
		}

		.hamburguesa {
			display: flex;
		}
	}
</style>
