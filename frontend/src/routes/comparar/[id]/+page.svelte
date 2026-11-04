<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api } from '$lib/api.js';
	import PanelComparador from '$lib/PanelComparador.svelte';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';

	let comparacion = $state(null);
	let error = $state('');

	$effect(() => {
		api(`/comparaciones/${page.params.id}/`)
			.then((r) => (comparacion = r))
			.catch((e) => (error = e?.status === 404 ? 'Esa comparación no existe o no es tuya.' : 'No se pudo cargar.'));
	});

	async function borrar() {
		if (!confirm('¿Borrar esta comparación y sus ofertas?')) return;
		await api(`/comparaciones/${comparacion.id}/`, { method: 'DELETE' });
		goto(resolve('/comparar'));
	}
</script>

<svelte:head>
	<title>{comparacion?.titulo ?? 'Comparación'} — PoolShop</title>
</svelte:head>

<div class="barra">
	<a href={resolve('/comparar')}>← Mis comparaciones</a>
	{#if comparacion?.puede_editar && !comparacion.pool}
		<Boton variante="peligro-suave" tamano="sm" onclick={borrar}>Borrar comparación</Boton>
	{/if}
</div>

{#if error}
	<Aviso variante="error">{error}</Aviso>
{:else if comparacion}
	<PanelComparador {comparacion} onactualizar={(nueva) => (comparacion = nueva)} />
{:else}
	<p>Cargando…</p>
{/if}

<style>
	.barra {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--e-3);
		margin-bottom: var(--e-5);
		font-size: var(--texto-sm);
		font-weight: 600;
	}
</style>
