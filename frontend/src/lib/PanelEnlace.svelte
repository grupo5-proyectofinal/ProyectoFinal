<script>
	import { estadoValidacion, etiquetaClave, etiquetaNivel, tonoNivel } from '$lib/confianza.js';

	let { analisis } = $props();
</script>

<section class="bloque">
	<h2>Validaciones del enlace</h2>
	<div class="enlace-analisis">
		<div class="enlace-analisis__cabecera">
			<span class="chip chip--color tono-{tonoNivel(analisis.nivel)}">
				{etiquetaNivel(analisis.nivel)}
			</span>
			<p class="ayuda enlace-analisis__nota">
				Análisis propio de PoolShop, sin servicios externos. Es orientativo y no bloquea la
				publicación.
			</p>
		</div>
		<ul class="enlace-analisis__lista">
			{#each analisis.validaciones as validacion (validacion.clave)}
				{@const estado = estadoValidacion(validacion)}
				<li class="enlace-analisis__item enlace-analisis__item--{estado}">
					<span class="enlace-analisis__icono" aria-hidden="true">
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
					<span class="enlace-analisis__cuerpo">
						<span class="enlace-analisis__clave">{etiquetaClave(validacion.clave)}</span>
						<span class="enlace-analisis__detalle">{validacion.detalle}</span>
					</span>
				</li>
			{/each}
		</ul>
	</div>
</section>

<style>
	.enlace-analisis {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
		padding: var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--superficie);
	}

	.enlace-analisis__cabecera {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2) var(--e-4);
	}

	.enlace-analisis__nota {
		flex: 1 1 12rem;
		margin: 0;
	}

	.enlace-analisis__lista {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--e-3) var(--e-5);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.enlace-analisis__item {
		display: flex;
		align-items: flex-start;
		gap: var(--e-2);
		min-width: 0;
	}

	.enlace-analisis__icono {
		display: inline-flex;
		flex: none;
		margin-top: 0.15rem;
		color: var(--tinta-tenue);
	}

	.enlace-analisis__item--ok .enlace-analisis__icono {
		color: var(--c-verde);
	}

	.enlace-analisis__item--atencion .enlace-analisis__icono {
		color: var(--c-ambar);
	}

	.enlace-analisis__cuerpo {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.enlace-analisis__clave {
		font-size: var(--texto-xs);
		font-weight: 600;
		color: var(--tinta-tenue);
	}

	.enlace-analisis__detalle {
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
		overflow-wrap: anywhere;
	}

	@media (max-width: 560px) {
		.enlace-analisis__lista {
			grid-template-columns: 1fr;
		}
	}
</style>
