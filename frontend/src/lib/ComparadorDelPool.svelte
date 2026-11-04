<script>
	// Pestaña "Comparador" del pool: el creador compara proveedores y los integrantes
	// ven por qué se eligió esa compra ("elegimos el más barato").
	import { api, fieldErrors } from '$lib/api.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import PanelComparador from '$lib/PanelComparador.svelte';
	import Boton from '$lib/ui/Boton.svelte';

	let { pool, esCreador } = $props();

	let comparacion = $state(null);
	let estado = $state('cargando'); // cargando | lista | vacia | error

	$effect(() => {
		const id = pool.id;
		estado = 'cargando';
		api(`/comparaciones/de-pool/${id}/`)
			.then((r) => {
				comparacion = r;
				estado = 'lista';
			})
			.catch((e) => (estado = e?.status === 404 ? 'vacia' : 'error'));
	});

	let creando = $state(false);
	let error = $state('');

	async function crear() {
		if (creando) return;
		creando = true;
		error = '';
		try {
			comparacion = await api('/comparaciones/', {
				method: 'POST',
				body: {
					titulo: `Proveedores para ${pool.titulo}`.slice(0, 200),
					producto: pool.nombre_producto,
					cantidad: pool.cantidad_total,
					pool: pool.id
				}
			});
			estado = 'lista';
		} catch (e) {
			const errores = fieldErrors(e.data);
			error = errores.pool || errores.detail || 'No se pudo crear la comparación.';
		} finally {
			creando = false;
		}
	}
</script>

{#if estado === 'cargando'}
	<p class="muted">Cargando el comparador…</p>
{:else if estado === 'lista'}
	<PanelComparador {comparacion} onactualizar={(nueva) => (comparacion = nueva)} />
{:else if estado === 'vacia'}
	<div class="vacio">
		<h2>Comparador de proveedores</h2>
		{#if esCreador}
			<p>
				Cargá las ofertas que evaluaste (precio, envío, impuestos, importación) y mostrales a los
				integrantes por qué este proveedor es el más conveniente.
			</p>
			<Boton variante="primario" disabled={creando} onclick={crear}>
				{creando ? 'Creando…' : 'Armar la comparación'}
			</Boton>
			{#if error}<Aviso variante="error">{error}</Aviso>{/if}
		{:else}
			<p>El organizador todavía no cargó la comparación de proveedores.</p>
		{/if}
	</div>
{:else}
	<p class="muted">No se pudo cargar el comparador.</p>
{/if}

<style>
	.vacio {
		display: grid;
		gap: var(--e-3);
		justify-items: start;
	}

	.vacio h2,
	.vacio p {
		margin: 0;
	}

	.vacio p,
	.muted {
		color: var(--tinta-suave);
	}
</style>
