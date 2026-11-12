<script>
	// Marco del backoffice: identidad de sección y salida al sitio, además de las
	// pestañas. El guard de staff vive en el layout raíz.
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { nombreUsuario } from '$lib/admin.js';
	import { session } from '$lib/session.svelte.js';

	let { children } = $props();

	const PESTANAS = [
		{ href: '/admin/usuarios', texto: 'Usuarios' },
		{ href: '/admin/mayoristas', texto: 'Mayoristas' },
		{ href: '/admin/categorias', texto: 'Categorías' }
	];
</script>

<div class="admin-marco">
	<div class="admin-barra">
		<p class="admin-barra__titulo">Administración</p>
		{#if session.user}
			<p class="admin-barra__sesion">{nombreUsuario(session.user)}</p>
		{/if}
		<a class="admin-barra__volver" href={resolve('/')}>← Volver al sitio</a>
	</div>
	<nav class="pestanas" aria-label="Secciones del backoffice">
		{#each PESTANAS as pestana (pestana.href)}
			{@const activa = page.url.pathname.startsWith(pestana.href)}
			<a
				class="pestanas__enlace"
				class:activo={activa}
				href={resolve(pestana.href)}
				aria-current={activa ? 'page' : undefined}
			>
				{pestana.texto}
			</a>
		{/each}
	</nav>
</div>

{@render children()}

<style>
	.admin-marco {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-3);
		margin-bottom: var(--e-5);
		padding-bottom: var(--e-3);
		border-bottom: 1px solid var(--linea);
	}

	.admin-barra {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--e-2) var(--e-4);
	}

	.admin-barra__titulo {
		margin: 0;
		font-family: var(--fuente-display);
		font-size: var(--texto-md);
		font-weight: 800;
		color: var(--tinta);
	}

	.admin-barra__sesion {
		margin: 0;
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
	}

	.admin-barra__volver {
		font-size: var(--texto-sm);
		font-weight: 600;
	}
</style>
