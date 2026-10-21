<script>
	import { resolve } from '$app/paths';
	import { etiquetaEstado } from '$lib/estados.js';
	import { diasHasta, fecha, moneda } from '$lib/formato.js';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let { pool, contexto = null } = $props();

	const portada = $derived(pool.imagenes?.[0]?.imagen ?? null);
	const abierto = $derived(pool.estado === 'abierto');
	const comprometido = $derived(pool.cantidad_total - pool.disponible);
	const miParte = $derived(pool.mi_cantidad ?? pool.cantidad_creador);
	const dias = $derived(diasHasta(pool.fecha_caducidad));
	const textoVence = $derived(
		abierto
			? dias <= 0
				? 'Vence hoy'
				: `Vence en ${dias} ${dias === 1 ? 'día' : 'días'}`
			: `Caduca el ${fecha(pool.fecha_caducidad)}`
	);
	const accion = $derived(abierto && pool.disponible > 0 ? 'Unirme' : 'Ver pool');
	const enlace = $derived(resolve(`/pools/${pool.id}`));
	// El API no expone precio de lista: la pill y el precio tachado solo
	// aparecen si el pool trae `descuento` o `precio_original` (ver fase 2).
	const descuento = $derived(
		Number(pool.descuento) ||
			(pool.precio_original
				? Math.round((1 - pool.precio_unitario / pool.precio_original) * 100)
				: 0)
	);
</script>

<Tarjeta class="pool">
	<div class="pool__contenido">
		<!-- La imagen también lleva al detalle; fuera del orden de tabulación porque el título ya es el enlace accesible. -->
		<a
			class="pool__media"
			class:pool__media--rosa={pool.id % 2 === 0}
			href={enlace}
			tabindex="-1"
			aria-hidden="true"
		>
			{#if portada}
				<img
					class="pool__imagen"
					src={portada}
					alt={pool.titulo}
					width="400"
					height="300"
					loading="lazy"
				/>
			{:else}
				<svg
					class="pool__cubo"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.4"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<path d="M3 8l9-5 9 5v8l-9 5-9-5z" />
					<path d="M3 8l9 5 9-5M12 13v8" />
				</svg>
			{/if}
			<div class="pool__estado">
				<Badge variante={pool.estado}>{etiquetaEstado(pool.estado)}</Badge>
			</div>
			{#if descuento > 0}
				<div class="pool__descuento">
					<Badge variante="descuento">-{descuento}%</Badge>
				</div>
			{/if}
		</a>

		<div class="pool__cuerpo">
			<p class="pool__categoria">{pool.categoria_nombre}</p>
			<h3 class="pool__titulo"><a href={enlace}>{pool.titulo}</a></h3>
			<p class="pool__producto">{pool.nombre_producto}</p>

			<p class="pool__precio">
				<span class="pool__monto">{moneda(pool.precio_unitario)}</span>
				{#if pool.precio_original}
					<s class="pool__antiguo">{moneda(pool.precio_original)}</s>
				{/if}
			</p>

			<progress
				class="progreso pool__barra"
				value={comprometido}
				max={pool.cantidad_total}
				aria-label="Progreso del pool"
			></progress>

			<p class="pool__meta">
				<span class="pool__comprometido">{comprometido} / {pool.cantidad_total}</span>
				{#if pool.disponible > 0}
					<span class="pool__faltan">Faltan <strong>{pool.disponible}</strong></span>
				{:else}
					<span class="pool__faltan">Completo</span>
				{/if}
			</p>

			<p class="pool__pie">
				<svg
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					aria-hidden="true"
				>
					<circle cx="12" cy="12" r="9" />
					<path d="M12 7v5l3 2" />
				</svg>
				<span>{textoVence}</span>
				<span aria-hidden="true">·</span>
				{#if pool.creador.id}
					<span class="pool__creador"
						>Organiza <a href={resolve(`/usuarios/${pool.creador.id}`)}>{pool.creador.username}</a
						></span
					>
				{:else}
					<span class="pool__creador">Organiza {pool.creador.username}</span>
				{/if}
			</p>

			{#if contexto === 'mis-pools'}
				<p class="pool__parte">Tu parte: <strong>{miParte} u.</strong></p>
			{:else if contexto === 'unidos' && pool.mi_cantidad != null}
				<p class="pool__parte">Tu reserva: <strong>{pool.mi_cantidad} u.</strong></p>
			{/if}

			<div class="pool__accion">
				<Boton href={enlace} bloque>{accion}</Boton>
			</div>
		</div>
	</div>
</Tarjeta>

<style>
	.pool__contenido {
		display: flex;
		flex-direction: column;
		height: 100%;
	}

	.pool__media {
		position: relative;
		display: grid;
		place-items: center;
		aspect-ratio: 16 / 10;
		margin: var(--e-3) var(--e-3) 0;
		border-radius: var(--radio-sm);
		background: var(--melocoton-fuerte);
		overflow: hidden;
	}

	.pool__media:hover {
		text-decoration: none;
	}

	.pool__media:hover .pool__imagen {
		transform: scale(1.03);
	}

	.pool__media--rosa {
		background: var(--melocoton);
	}

	.pool__imagen {
		width: 100%;
		height: 100%;
		object-fit: cover;
		transition: transform var(--transicion);
	}

	.pool__cubo {
		width: 60px;
		height: 60px;
		color: var(--naranja-fuerte);
	}

	.pool__media--rosa .pool__cubo {
		color: var(--marca);
	}

	.pool__estado,
	.pool__descuento {
		position: absolute;
		top: var(--e-2);
		filter: drop-shadow(0 0 2px rgba(255, 255, 255, 0.9));
	}

	.pool__estado {
		left: var(--e-2);
	}

	.pool__descuento {
		right: var(--e-2);
	}

	.pool__cuerpo {
		display: flex;
		flex: 1;
		flex-direction: column;
		gap: var(--e-2);
		padding: var(--e-3);
	}

	.pool__categoria {
		margin: 0;
		font-size: var(--texto-xs);
		font-weight: 600;
		letter-spacing: 0.02em;
		color: var(--tinta-tenue);
	}

	.pool__titulo {
		min-height: 40px;
		font-size: var(--texto-base);
		font-weight: 500;
		line-height: 1.35;
		overflow-wrap: anywhere;
	}

	.pool__titulo a {
		color: var(--tinta);
	}

	.pool__titulo a:hover {
		color: var(--marca-fuerte);
	}

	.pool__producto {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
		overflow-wrap: anywhere;
	}

	.pool__precio {
		display: flex;
		align-items: baseline;
		gap: var(--e-2);
		margin: 0;
	}

	.pool__monto {
		font-family: var(--fuente-display);
		font-size: var(--texto-xl);
		font-weight: 800;
		letter-spacing: -0.02em;
	}

	.pool__antiguo {
		font-size: var(--texto-sm);
		color: var(--tinta-tenue);
	}

	.pool__barra {
		height: 8px;
		margin: 0;
	}

	.pool__barra::-webkit-progress-value {
		background: var(--progreso);
	}

	.pool__barra::-moz-progress-bar {
		background: var(--progreso);
	}

	.pool__meta {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--e-2);
		margin: 0;
		font-size: var(--texto-sm);
	}

	.pool__comprometido {
		font-weight: 700;
	}

	.pool__faltan {
		color: var(--tinta-tenue);
	}

	.pool__faltan strong {
		color: var(--marca-fuerte);
	}

	.pool__pie {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2);
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-tenue);
	}

	.pool__pie svg {
		flex: none;
		width: 16px;
		height: 16px;
		color: var(--acento-naranja);
	}

	.pool__creador {
		overflow-wrap: anywhere;
	}

	.pool__parte {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.pool__parte strong {
		color: var(--tinta);
	}

	.pool__accion {
		margin-top: auto;
		padding-top: var(--e-2);
	}
</style>
