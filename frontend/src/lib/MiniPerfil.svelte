<script>
	import { api } from '$lib/api.js';
	import { fecha } from '$lib/formato.js';

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

<button class="mini-perfil__boton" type="button" onclick={alternar}>
	{abierto ? 'Ocultar perfil' : 'Ver perfil'}
</button>

{#if abierto}
	{#if perfil}
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
	{:else if error}
		<p class="error" role="alert">{error}</p>
	{:else}
		<p class="muted">Cargando perfil…</p>
	{/if}
{/if}

<style>
	.mini-perfil__boton {
		margin-top: var(--e-2);
		align-self: flex-start;
		font-size: var(--texto-xs);
		font-weight: 600;
		color: var(--acento);
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
	}

	.mini-perfil {
		margin-top: var(--e-2);
		padding: var(--e-3);
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
		background: var(--superficie);
		grid-column: 1 / -1;
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
