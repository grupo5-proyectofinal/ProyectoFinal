<script>
	import { api } from '$lib/api.js';
	import { fecha } from '$lib/formato.js';
	import Boton from '$lib/ui/Boton.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let { usuarioId } = $props();

	let perfil = $state(null);
	let abierto = $state(false);
	let error = $state('');

	async function alternar() {
		abierto = !abierto;
		if (abierto && !perfil) {
			try {
				perfil = await api(`/usuarios/${usuarioId}/`);
			} catch {
				error = 'No se pudo cargar el perfil.';
			}
		}
	}
</script>

<div class="mini-perfil__accion">
	<Boton variante="ghost" tamano="sm" onclick={alternar}>
		{abierto ? 'Ocultar perfil' : 'Ver perfil'}
	</Boton>
</div>

{#if abierto}
	<div class="mini-perfil__panel">
		{#if perfil}
			<Tarjeta>
				<div class="mini-perfil">
					{#if perfil.ciudad}
						<p class="mini-perfil__dato">{perfil.ciudad}</p>
					{/if}
					<p class="mini-perfil__dato">Miembro desde {fecha(perfil.antiguedad)}</p>
					<p class="mini-perfil__dato">
						{perfil.pools_creados} pools creados · {perfil.pools_unidos} pools unidos
					</p>
					<p class="mini-perfil__titulo">Pools en común</p>
					{#if perfil.pools_en_comun.length}
						<ul class="mini-perfil__lista">
							{#each perfil.pools_en_comun as pool (pool.id)}
								<li>{pool.titulo}</li>
							{/each}
						</ul>
					{:else}
						<p class="mini-perfil__dato">Sin pools en común.</p>
					{/if}
				</div>
			</Tarjeta>
		{:else if error}
			<p class="error" role="alert">{error}</p>
		{:else}
			<p class="muted">Cargando perfil…</p>
		{/if}
	</div>
{/if}

<style>
	.mini-perfil__accion {
		margin-top: var(--e-2);
		align-self: flex-start;
	}

	.mini-perfil__panel {
		margin-top: var(--e-2);
	}

	.mini-perfil {
		padding: var(--e-3) var(--e-4);
		background: var(--crema);
	}

	.mini-perfil__dato {
		margin: 0 0 var(--e-1);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.mini-perfil__titulo {
		margin: var(--e-2) 0 var(--e-1);
		font-size: var(--texto-xs);
		font-weight: 600;
		color: var(--tinta-tenue);
	}

	.mini-perfil__lista {
		margin: 0;
		padding-left: var(--e-4);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}
</style>
