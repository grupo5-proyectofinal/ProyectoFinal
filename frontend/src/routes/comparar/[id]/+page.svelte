<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, fieldErrors } from '$lib/api.js';
	import { confirmar } from '$lib/confirmacion.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';
	import PanelComparador from '$lib/PanelComparador.svelte';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';

	let comparacion = $state(null);
	let error = $state('');
	let borrando = $state(false);

	$effect(() => {
		api(`/comparaciones/${page.params.id}/`)
			.then((r) => (comparacion = r))
			.catch((e) => (error = e?.status === 404 ? 'Esa comparación no existe o no es tuya.' : 'No se pudo cargar.'));
	});

	async function borrar() {
		if (borrando) return;
		const aceptada = await confirmar({
			titulo: '¿Borrar esta comparación?',
			descripcion: 'Se borran también sus ofertas y el historial de precios. No se puede deshacer.',
			confirmar: 'Borrar comparación'
		});
		if (!aceptada) return;
		borrando = true;
		try {
			await api(`/comparaciones/${comparacion.id}/`, { method: 'DELETE' });
			notificar('Comparación borrada.');
			goto(resolve('/comparar'));
		} catch (e) {
			notificar(fieldErrors(e.data).detail ?? 'No se pudo borrar la comparación.', 'error');
			borrando = false;
		}
	}
</script>

<svelte:head>
	<title>{comparacion?.titulo ?? 'Comparación'} — PoolShop</title>
</svelte:head>

<div class="barra">
	<a class="volver" href={resolve('/comparar')}>← Volver a mis comparaciones</a>
	{#if comparacion?.puede_editar && !comparacion.pool}
		<Boton variante="peligro-suave" tamano="sm" onclick={borrar} disabled={borrando}>
			{borrando ? 'Borrando…' : 'Borrar comparación'}
		</Boton>
	{/if}
</div>

{#if error}
	<Aviso variante="error">{error}</Aviso>
{:else if comparacion}
	<PanelComparador {comparacion} nivel={1} onactualizar={(nueva) => (comparacion = nueva)} />
{:else}
	<p role="status">Cargando…</p>
{/if}

<style>
	.barra .volver {
		margin-bottom: 0;
	}

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
