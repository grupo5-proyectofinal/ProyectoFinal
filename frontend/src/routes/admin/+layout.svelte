<script>
	// Pestañas del backoffice (el guard de staff vive en el layout raíz).
	import { resolve } from '$app/paths';
	import { page } from '$app/state';

	let { children } = $props();

	const PESTANAS = [
		{ href: '/admin/usuarios', texto: 'Usuarios' },
		{ href: '/admin/categorias', texto: 'Categorías' }
	];
</script>

<nav class="admin-tabs" aria-label="Secciones del backoffice">
	{#each PESTANAS as pestana (pestana.href)}
		{@const activa = page.url.pathname.startsWith(pestana.href)}
		<a class="admin-tabs__enlace" class:activa href={resolve(pestana.href)} aria-current={activa ? 'page' : undefined}>
			{pestana.texto}
		</a>
	{/each}
</nav>

{@render children()}

<style>
	.admin-tabs {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
		margin-bottom: var(--e-5);
	}

	.admin-tabs__enlace {
		padding: 0.45rem 0.9rem;
		border-radius: 999px;
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.admin-tabs__enlace:hover {
		text-decoration: none;
		background: var(--crema);
	}

	.admin-tabs__enlace.activa {
		background: var(--melocoton);
		color: var(--marca-fuerte);
	}
</style>
