<script>
	import { resolve } from '$app/paths';
	import { etiquetaCategoria, etiquetaEstado } from '$lib/estados.js';
	import { diasHasta, fecha, moneda } from '$lib/formato.js';
	import { notificar } from '$lib/toast.svelte.js';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let { pool, contexto = null } = $props();

	// Si la portada no carga (archivo borrado), se ve el ícono de "sin imagen" en vez
	// del texto alternativo encima de la etiqueta de estado.
	let portadaRota = $state(null);
	const portada = $derived(
		pool.imagenes?.[0]?.imagen && pool.imagenes[0].imagen !== portadaRota
			? pool.imagenes[0].imagen
			: null
	);
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
	const accion = 'Ver pool';
	const enlace = $derived(resolve(`/pools/${pool.id}`));

	// Tras copiar, el ícono pasa a un tilde un momento (la hoja nativa ya se ve sola).
	let copiado = $state(false);
	let temporizadorCopia;
	$effect(() => () => clearTimeout(temporizadorCopia));

	async function compartir() {
		if (typeof navigator === 'undefined') return;
		const url = new URL(`/pools/${pool.id}`, window.location.origin).href;
		try {
			if (navigator.share) {
				await navigator.share({ title: pool.titulo, url });
				return;
			}
			await navigator.clipboard.writeText(url);
			notificar('Enlace copiado.');
			copiado = true;
			clearTimeout(temporizadorCopia);
			temporizadorCopia = setTimeout(() => (copiado = false), 1600);
		} catch (error) {
			if (error?.name !== 'AbortError') notificar('No se pudo compartir el enlace.', 'error');
		}
	}

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
					decoding="async"
					onerror={() => (portadaRota = portada)}
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
			<p class="pool__categoria">{etiquetaCategoria(pool)}</p>
			<h3 class="pool__titulo"><a href={enlace}>{pool.titulo}</a></h3>
			<p class="pool__producto">{pool.nombre_producto}</p>

			<p class="pool__precio">
				<span class="pool__monto">{moneda(pool.precio_unitario)}</span>
				{#if pool.precio_original}
					<s class="pool__antiguo">{moneda(pool.precio_original)}</s>
				{/if}
				<span class="pool__unidad">por unidad</span>
			</p>

			<progress
				class="progreso pool__barra"
				value={comprometido}
				max={pool.cantidad_total}
				aria-label="Progreso del pool"
				aria-valuetext={`${comprometido} de ${pool.cantidad_total} unidades comprometidas`}
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
				<span class="pool__vence" class:pool__vence--urgente={abierto && dias <= 1}>
					{textoVence}
				</span>
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
				<div class="pool__accion-principal">
					<Boton href={enlace} bloque>{accion}</Boton>
				</div>
				{#if pool.id}
					<button
						type="button"
						class="pool__compartir"
						class:pool__compartir--hecho={copiado}
						onclick={compartir}
						aria-label={`Compartir ${pool.titulo}`}
						title="Compartir"
					>
						<svg
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							{#if copiado}
								<path class="pool__tilde" d="M5 12.5l4.5 4.5L19 7.5" />
							{:else}
								<circle cx="18" cy="5" r="3" />
								<circle cx="6" cy="12" r="3" />
								<circle cx="18" cy="19" r="3" />
								<path d="M8.6 10.6 15.4 6.4M8.6 13.4l6.8 4.2" />
							{/if}
						</svg>
					</button>
				{/if}
			</div>
		</div>
	</div>
</Tarjeta>

<style>
	:global(.pool) {
		transition:
			box-shadow var(--transicion),
			border-color var(--transicion),
			transform var(--transicion);
	}

	:global(.pool:hover) {
		border-color: var(--linea-fuerte);
		box-shadow: var(--sombra-lg);
		transform: translateY(-2px);
	}

	@media (prefers-reduced-motion: reduce) {
		:global(.pool:hover) {
			transform: none;
		}
	}

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
		text-decoration: underline;
		text-underline-offset: 3px;
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

	.pool__unidad {
		margin-left: auto;
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
		white-space: nowrap;
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

	.pool__vence--urgente {
		color: var(--marca-fuerte);
		font-weight: 700;
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
		display: flex;
		align-items: stretch;
		gap: var(--e-2);
		margin-top: auto;
		padding-top: var(--e-2);
	}

	.pool__accion-principal {
		flex: 1;
		min-width: 0;
	}

	.pool__compartir {
		display: grid;
		flex: none;
		place-items: center;
		width: var(--alto-tap);
		border: 1px solid var(--linea-fuerte);
		border-radius: var(--radio-sm);
		background: var(--superficie);
		color: var(--tinta-suave);
		cursor: pointer;
		transition:
			border-color var(--transicion),
			background-color var(--transicion),
			color var(--transicion);
	}

	.pool__compartir:hover {
		border-color: var(--marca);
		background: var(--melocoton);
		color: var(--marca-fuerte);
	}

	.pool__compartir--hecho,
	.pool__compartir--hecho:hover {
		color: var(--exito);
	}

	.pool__tilde {
		stroke-dasharray: 24;
		animation: tilde-tarjeta 400ms ease-out both;
	}

	@keyframes tilde-tarjeta {
		from {
			stroke-dashoffset: 24;
		}
		to {
			stroke-dashoffset: 0;
		}
	}

	.pool__compartir svg {
		width: 18px;
		height: 18px;
	}
</style>
