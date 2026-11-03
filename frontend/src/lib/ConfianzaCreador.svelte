<script>
	// Datos de confianza del organizador para quien está por unirse (Iteración 1:
	// "que el creador dé información de confianza"). Reusa el perfil público.
	import { api } from '$lib/api.js';
	import { fecha } from '$lib/formato.js';
	import { formatoPuntaje, textoResenas } from '$lib/resenas.js';

	let { usuarioId } = $props();

	let perfil = $state(null);
	let pedido = 0;

	$effect(() => {
		const actual = ++pedido;
		api(`/usuarios/${usuarioId}/`, { auth: false })
			.then((datos) => {
				if (actual === pedido) perfil = datos;
			})
			.catch(() => {
				// Es información de apoyo: si falla, el detalle del pool se ve igual.
				if (actual === pedido) perfil = null;
			});
	});
</script>

{#if perfil}
	<ul class="confianza" aria-label="Sobre el organizador">
		<li>
			{#if perfil.cantidad_resenas}
				<span class="confianza__estrella" aria-hidden="true">★</span>
				<strong>{formatoPuntaje(perfil.puntaje_promedio)}</strong>
				({textoResenas(perfil.cantidad_resenas)})
			{:else}
				Todavía sin reseñas
			{/if}
		</li>
		<li>{perfil.pools_creados} {perfil.pools_creados === 1 ? 'pool organizado' : 'pools organizados'}</li>
		<li>En PoolShop desde {fecha(perfil.antiguedad)}</li>
	</ul>
{/if}

<style>
	.confianza {
		display: grid;
		gap: var(--e-1);
		margin: var(--e-2) 0 0;
		padding: 0;
		list-style: none;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.confianza__estrella {
		color: var(--naranja-fuerte);
	}
</style>
