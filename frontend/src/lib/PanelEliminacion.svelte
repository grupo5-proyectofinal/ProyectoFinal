<script>
	import { tonoNombre } from '$lib/estados.js';
	import { miVotoEliminacion, puedeVotarEliminacion } from '$lib/eliminacion.js';
	import { iniciales } from '$lib/formato.js';

	let { pool, solicitud, usuarioId, ocupado = false, onvotar } = $props();

	const miVoto = $derived(miVotoEliminacion(solicitud, usuarioId));
	const puedoVotar = $derived(puedeVotarEliminacion(pool, solicitud, usuarioId));
	const total = $derived(solicitud?.total ?? 0);
	const votaron = $derived(solicitud?.votos?.length ?? 0);
	const aceptaron = $derived(solicitud?.aceptaron ?? 0);
	const faltan = $derived(Math.max(total - votaron, 0));
</script>

{#if solicitud?.estado === 'pendiente'}
	<div class="panel-eliminacion">
		<div class="panel-eliminacion__cabecera">
			<p class="panel-eliminacion__titulo">Eliminación con aprobación</p>
			<span class="chip chip--color panel-eliminacion__avance">{aceptaron}/{total}</span>
		</div>
		<p class="ayuda">
			Aceptaron {aceptaron} de {total}.
			{#if faltan > 0}
				Falta{faltan === 1 ? '' : 'n'} {faltan} voto{faltan === 1 ? '' : 's'} para eliminarlo.
			{/if}
		</p>
		<progress
			class="progreso progreso--color"
			value={votaron}
			max={total || 1}
			aria-label="Integrantes que ya votaron"
		></progress>

		{#if solicitud.votos.length}
			<ul class="panel-eliminacion__votos">
				{#each solicitud.votos as voto (voto.usuario.id)}
					<li class="panel-eliminacion__voto tono-{tonoNombre(voto.usuario.username)}">
						<span class="avatar avatar--sm" aria-hidden="true">
							{#if voto.usuario.foto}
								<img src={voto.usuario.foto} alt="" width="28" height="28" loading="lazy" />
							{:else}
								{iniciales(voto.usuario.username)}
							{/if}
						</span>
						<span class="panel-eliminacion__nombre">
							{voto.usuario.username}{#if voto.usuario.id === usuarioId} (vos){/if}
						</span>
						<span
							class="chip chip--color panel-eliminacion__resultado"
							class:tono-verde={voto.acepta}
							class:tono-coral={!voto.acepta}
						>
							{voto.acepta ? 'Aceptó' : 'Rechazó'}
						</span>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="ayuda">Todavía no votó nadie.</p>
		{/if}

		{#if miVoto}
			<p class="panel-eliminacion__mio">
				Ya votaste: {miVoto.acepta ? 'aceptaste' : 'rechazaste'} la eliminación. No se puede cambiar.
			</p>
		{:else if puedoVotar}
			<div class="panel-eliminacion__acciones">
				<button
					class="btn btn--primario btn--bloque"
					type="button"
					disabled={ocupado}
					onclick={() => onvotar(true)}
				>
					Aceptar eliminación
				</button>
				<button
					class="btn btn--peligro-suave btn--bloque"
					type="button"
					disabled={ocupado}
					onclick={() => onvotar(false)}
				>
					Rechazar
				</button>
			</div>
		{/if}
	</div>
{:else if solicitud?.estado === 'rechazada'}
	<div class="alerta alerta--aviso panel-eliminacion__aviso" role="alert">
		La eliminación fue rechazada por un integrante. El pool sigue en pie.
	</div>
{/if}

<style>
	.panel-eliminacion {
		display: flex;
		flex-direction: column;
		gap: var(--e-3);
		padding: var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--superficie-alt);
	}

	.panel-eliminacion__cabecera {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-3);
	}

	.panel-eliminacion__titulo {
		margin: 0;
		font-size: var(--texto-sm);
		font-weight: 600;
		color: var(--tinta);
	}

	.panel-eliminacion__avance {
		background: var(--superficie);
		font-variant-numeric: tabular-nums;
	}

	.panel-eliminacion__votos {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.panel-eliminacion__voto {
		display: flex;
		align-items: center;
		gap: var(--e-2);
		min-width: 0;
	}

	.panel-eliminacion__nombre {
		min-width: 0;
		font-size: var(--texto-sm);
		overflow-wrap: anywhere;
	}

	.panel-eliminacion__resultado {
		margin-left: auto;
		background: var(--superficie);
	}

	.panel-eliminacion__mio {
		margin: 0;
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
	}

	.panel-eliminacion__aviso {
		margin: 0;
		font-size: var(--texto-sm);
	}
</style>
