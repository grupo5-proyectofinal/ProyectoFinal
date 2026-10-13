<script>
	import { estadoValidacion, etiquetaClave, etiquetaNivel, tonoNivel } from '$lib/confianza.js';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let { analisis } = $props();
</script>

<section class="enlace-panel">
	<h2 class="enlace-panel__titulo">Validaciones del enlace</h2>
	<Tarjeta>
		<div class="enlace-panel__cuerpo">
			<div class="enlace-panel__cabecera">
				<span class="enlace-panel__nivel tono-{tonoNivel(analisis.nivel)}">
					{etiquetaNivel(analisis.nivel)}
				</span>
				<p class="enlace-panel__nota">
					Análisis propio de PoolShop, sin servicios externos. Es orientativo y no bloquea la
					publicación.
				</p>
			</div>
			<ul class="enlace-panel__lista">
				{#each analisis.validaciones as validacion (validacion.clave)}
					{@const estado = estadoValidacion(validacion)}
					<li class="enlace-panel__item enlace-panel__item--{estado}">
						<span class="enlace-panel__icono" aria-hidden="true">
							{#if estado === 'ok'}
								<svg
									width="18"
									height="18"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.75"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<circle cx="12" cy="12" r="9" />
									<path d="m8.5 12.5 2.5 2.5 5-5.5" />
								</svg>
							{:else if estado === 'atencion'}
								<svg
									width="18"
									height="18"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.75"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<path d="M12 3 2.5 20h19L12 3Z" />
									<path d="M12 10v4" />
									<path d="M12 17.5h.01" />
								</svg>
							{:else}
								<svg
									width="18"
									height="18"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.75"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<circle cx="12" cy="12" r="9" />
									<path d="M12 11v5" />
									<path d="M12 7.5h.01" />
								</svg>
							{/if}
						</span>
						<span class="enlace-panel__detalle-cuerpo">
							<span class="enlace-panel__clave">{etiquetaClave(validacion.clave)}</span>
							<span class="enlace-panel__detalle">{validacion.detalle}</span>
						</span>
					</li>
				{/each}
			</ul>
		</div>
	</Tarjeta>
</section>

<style>
	.enlace-panel {
		margin-top: var(--e-7);
	}

	.enlace-panel__titulo {
		margin: 0 0 var(--e-3);
		font-size: var(--texto-md);
	}

	.enlace-panel__cuerpo {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
		padding: var(--e-4);
	}

	.enlace-panel__cabecera {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2) var(--e-4);
	}

	/* El tono lo aportan las clases globales `tono-*` (--c-t / --t-t). */
	.enlace-panel__nivel {
		display: inline-flex;
		align-items: center;
		flex: none;
		padding: 0.2rem 0.7rem;
		border-radius: var(--radio-full);
		background: var(--t-t);
		color: var(--c-t);
		font-size: var(--texto-xs);
		font-weight: 700;
		letter-spacing: 0.01em;
		white-space: nowrap;
	}

	.enlace-panel__nota {
		flex: 1 1 12rem;
		margin: 0;
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
	}

	.enlace-panel__lista {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--e-3) var(--e-5);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.enlace-panel__item {
		display: flex;
		align-items: flex-start;
		gap: var(--e-2);
		min-width: 0;
	}

	.enlace-panel__icono {
		display: inline-flex;
		flex: none;
		margin-top: 0.15rem;
		color: var(--tinta-tenue);
	}

	.enlace-panel__item--ok .enlace-panel__icono {
		color: var(--c-verde);
	}

	.enlace-panel__item--atencion .enlace-panel__icono {
		color: var(--c-ambar);
	}

	.enlace-panel__detalle-cuerpo {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.enlace-panel__clave {
		font-size: var(--texto-xs);
		font-weight: 600;
		color: var(--tinta-tenue);
	}

	.enlace-panel__detalle {
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
		overflow-wrap: anywhere;
	}

	@media (max-width: 560px) {
		.enlace-panel__lista {
			grid-template-columns: 1fr;
		}
	}
</style>
