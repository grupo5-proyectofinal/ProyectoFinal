<script>
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { loadMe, logout, session } from '$lib/session.svelte.js';

	let { children } = $props();

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
