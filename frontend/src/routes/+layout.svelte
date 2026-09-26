<script>
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { loadMe, logout, session } from '$lib/session.svelte.js';

	let { children } = $props();

	const PROTEGIDAS = ['/perfil', '/pools', '/mis-pools', '/unidos'];

	$effect(() => {
		const { pathname } = page.url;
		const protegida = PROTEGIDAS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
		if (!session.access && protegida) goto(resolve('/login'));
	});

	if (session.access) loadMe();

	function cerrarSesion() {
		logout();
		goto(resolve('/'));
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>PoolShop</title>
</svelte:head>

<header class="barra">
	<a class="marca" href={resolve('/')}>PoolShop</a>
	<nav>
		<a href={resolve('/')}>Inicio</a>
		{#if session.access}
			<a href={resolve('/pools')}>Pools</a>
			<a href={resolve('/pools/nuevo')}>Crear pool</a>
			<a href={resolve('/mis-pools')}>Mis Pools</a>
			<a href={resolve('/unidos')}>Unidos</a>
			<a href={resolve('/perfil')}>Mi perfil</a>
			<button class="enlace" type="button" onclick={cerrarSesion}>Cerrar sesión</button>
		{:else}
			<a href={resolve('/login')}>Ingresar</a>
			<a href={resolve('/registro')}>Registrarse</a>
		{/if}
	</nav>
</header>

<main>
	{@render children()}
</main>
