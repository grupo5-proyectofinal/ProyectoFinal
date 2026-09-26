<script>
	import { resolve } from '$app/paths';
	import { etiquetaEstado } from '$lib/estados.js';
	import { fecha, iniciales, moneda } from '$lib/formato.js';

	let { pool } = $props();

	const portada = $derived(pool.imagenes?.[0]?.imagen ?? null);
</script>

<article class="pool">
	<div class="pool__media" class:pool__media--vacia={!portada}>
		{#if portada}
			<img class="pool__imagen" src={portada} alt={pool.titulo} width="400" height="300" loading="lazy" />
		{:else}
			<span class="pool__monograma" aria-hidden="true">{iniciales(pool.titulo)}</span>
		{/if}
		<span class="badge badge--{pool.estado} pool__estado">{etiquetaEstado(pool.estado)}</span>
	</div>

	<div class="pool__cuerpo">
		<p class="pool__categoria">{pool.categoria_nombre}</p>
		<h3 class="pool__titulo">{pool.titulo}</h3>
		<p class="pool__producto">{pool.nombre_producto}</p>

		<div class="pool__datos">
			<span class="pool__precio">{moneda(pool.precio_unitario)}</span>
			<span class="pool__disponible">Quedan {pool.disponible} de {pool.cantidad_total}</span>
		</div>

		<p class="pool__meta">
			Organiza {pool.creador.username} · caduca el {fecha(pool.fecha_caducidad)}
		</p>
		<span class="pool__accion">Ver pool</span>
	</div>

	<a class="pool__enlace" href={resolve(`/pools/${pool.id}`)}>
		<span class="sr-only">{pool.titulo}</span>
	</a>
</article>

<style>
	.pool {
		position: relative;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--superficie);
		transition:
			transform var(--transicion),
			box-shadow var(--transicion),
			border-color var(--transicion);
	}

	.pool:hover {
		transform: translateY(-2px);
		border-color: var(--linea-fuerte);
		box-shadow: var(--sombra-md);
	}

	.pool__media {
		position: relative;
		aspect-ratio: 4 / 3;
		background: var(--superficie-alt);
		overflow: hidden;
	}

	.pool__media--vacia {
		display: grid;
		place-items: center;
	}

	.pool__imagen {
		width: 100%;
		height: 100%;
		object-fit: cover;
		transition: transform 400ms cubic-bezier(0.2, 0.6, 0.3, 1);
	}

	.pool:hover .pool__imagen {
		transform: scale(1.03);
	}

	.pool__monograma {
		font-family: var(--fuente-display);
		font-size: 2.5rem;
		font-weight: 500;
		color: var(--linea-fuerte);
	}

	.pool__estado {
		position: absolute;
		top: var(--e-3);
		left: var(--e-3);
		background-color: rgba(255, 255, 255, 0.92);
		backdrop-filter: blur(4px);
	}

	.pool__cuerpo {
		display: flex;
		flex: 1;
		flex-direction: column;
		gap: var(--e-2);
		padding: var(--e-4);
	}

	.pool__categoria {
		margin: 0;
		font-size: var(--texto-xs);
		font-weight: 600;
		letter-spacing: 0.02em;
		color: var(--tinta-tenue);
	}

	.pool__titulo {
		margin: 0;
		font-size: var(--texto-md);
		line-height: 1.22;
		overflow-wrap: anywhere;
	}

	.pool__producto {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
		overflow-wrap: anywhere;
	}

	.pool__datos {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--e-2);
		margin-top: var(--e-2);
		padding-top: var(--e-3);
		border-top: 1px solid var(--linea);
	}

	.pool__precio {
		font-weight: 600;
		color: var(--tinta);
		font-variant-numeric: tabular-nums;
	}

	.pool__disponible {
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
	}

	.pool__meta {
		margin: 0;
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.pool__accion {
		margin-top: auto;
		padding-top: var(--e-2);
		font-size: var(--texto-sm);
		font-weight: 600;
		color: var(--acento);
	}

	.pool__enlace {
		position: absolute;
		inset: 0;
		border-radius: var(--radio);
	}

	.pool__enlace:focus-visible {
		outline: 2px solid var(--acento);
		outline-offset: 3px;
	}

	.pool:hover .pool__titulo {
		color: var(--acento);
	}
</style>
