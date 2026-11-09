<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import Boton from '$lib/ui/Boton.svelte';

	const titulo = $derived(
		page.status === 404
			? 'No encontramos esta página'
			: page.status === 403
				? 'No tenés permiso para ver esto'
				: 'Algo salió mal'
	);
	const detalle = $derived(
		page.status === 404
			? 'Puede que el enlace esté mal escrito o que el pool ya no exista.'
			: page.error?.message || 'Probá de nuevo en unos segundos.'
	);
</script>

<svelte:head>
	<title>{titulo} — PoolShop</title>
</svelte:head>

<div class="error">
	<p class="error__codigo">{page.status}</p>
	<h1>{titulo}</h1>
	<p class="error__detalle">{detalle}</p>
	<div class="error__acciones">
		<Boton variante="primario" href={resolve('/pools')}>Explorar pools</Boton>
		<Boton variante="secundario" href={resolve('/')}>Ir al inicio</Boton>
	</div>
</div>

<style>
	.error {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--e-3);
		max-width: 34rem;
		margin: 0 auto;
		padding: var(--e-8) var(--e-4);
		text-align: center;
	}

	.error__codigo {
		margin: 0;
		font-family: var(--fuente-display);
		font-size: clamp(3rem, 12vw, 6rem);
		font-weight: 800;
		line-height: 1;
		color: var(--melocoton-fuerte);
	}

	.error h1 {
		margin: 0;
		font-size: var(--texto-xl);
	}

	.error__detalle {
		margin: 0;
		color: var(--tinta-suave);
	}

	.error__acciones {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: var(--e-3);
		margin-top: var(--e-2);
	}
</style>
