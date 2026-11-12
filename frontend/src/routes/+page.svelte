<script>
	import Bolsitas from '$lib/Bolsitas.svelte';
	import { raices } from '$lib/variantes.js';
	import { resolve } from '$app/paths';
	import { api } from '$lib/api.js';
	import PoolCard from '$lib/PoolCard.svelte';
	import PoolCardSkeleton from '$lib/PoolCardSkeleton.svelte';
	import { session } from '$lib/session.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';

	// Icono por palabra clave del nombre de la categoría; sin coincidencia, cubo.
	const CUBO = ['M3 8l9-5 9 5v8l-9 5-9-5z', 'M3 8l9 5 9-5M12 13v8'];
	const ICONOS = [
		{
			claves: ['alimento', 'comida', 'almacen', 'almacén'],
			d: ['M4 7h16l-1.6 12.2a1 1 0 0 1-1 .8H6.6a1 1 0 0 1-1-.8z', 'M8 7l2-3M16 7l-2-3']
		},
		{ claves: ['bebida'], d: ['M10 2h4v4l2 3v12a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V9l2-3z', 'M8 13h8'] },
		{
			claves: ['limpieza'],
			d: ['M9 2h5v4H9z', 'M14 4h3', 'M8 6h7l2 4v11a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V10z']
		},
		{
			claves: ['higiene', 'cuidado'],
			d: ['M9 3h6a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H9a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3z', 'M6 9h12']
		},
		{ claves: ['hogar', 'casa'], d: ['M3 11l9-7 9 7', 'M5 10v10h14V10', 'M10 20v-5h4v5'] },
		{
			claves: ['ropa', 'indumentaria', 'calzado'],
			d: ['M8 3l-5 3 2 4 3-1v12h8V9l3 1 2-4-5-3', 'M8 3a4 4 0 0 0 8 0']
		},
		{
			claves: ['electro', 'tecno'],
			d: ['M9 2v5M15 2v5', 'M6 7h12v3a6 6 0 0 1-6 6 6 6 0 0 1-6-6z', 'M12 16v6']
		},
		{ claves: ['otro', 'más', 'mas'], d: ['M4.5 12h1M11.5 12h1M18.5 12h1'] }
	];

	function iconoCategoria(nombre) {
		const texto = (nombre ?? '').toLowerCase();
		return ICONOS.find((icono) => icono.claves.some((clave) => texto.includes(clave)))?.d ?? CUBO;
	}

	let destacados = $state([]);
	let cercanos = $state([]);
	let categorias = $state([]);
	let cargando = $state(true);
	let error = $state(false);

	$effect(() => {
		cargar();
	});

	async function cargar() {
		cargando = true;
		error = false;
		try {
			const [vistos, porCompletar, cats] = await Promise.all([
				api('/pools/', { query: { ordering: '-vistas', estado: 'abierto' } }),
				api('/pools/', { query: { ordering: 'restante', estado: 'abierto' } }),
				api('/categories/')
			]);
			destacados = vistos.results.slice(0, 4);
			// Un pool no se repite en las dos secciones de la misma página.
			const idsDestacados = new Set(destacados.map((pool) => pool.id));
			cercanos = porCompletar.results
				.filter((pool) => !idsDestacados.has(pool.id))
				.slice(0, 4);
			// Solo principales: filtrar por "Ropa" ya incluye Remera, Buzo, etc.
			categorias = raices(cats.results ?? cats);
		} catch {
			destacados = [];
			cercanos = [];
			error = true;
		} finally {
			cargando = false;
		}
	}

	const enlaceCta = $derived(session.access ? '/pools/nuevo' : '/registro');
	const textoCta = $derived(session.access ? 'Crear pool' : 'Crear una cuenta');
	// Si no hay pools abiertos, mostrar un único estado vacío en vez de dos seguidos.
	const sinPools = $derived(!cargando && !error && !destacados.length && !cercanos.length);
</script>

<svelte:head>
	<title>PoolShop — compras colectivas entre vecinos</title>
</svelte:head>

{#snippet seccion(id, titulo, lista)}
	<section class="seccion" aria-labelledby={id}>
		<div class="seccion__cabecera">
			<h2 class="seccion__titulo" {id}>{titulo}</h2>
			<a class="seccion__enlace" href={resolve('/pools')}>Ver todos →</a>
		</div>

		{#if cargando}
			<p class="sr-only" role="status">Cargando pools…</p>
			<div class="grilla-pools" aria-hidden="true">
				{#each [0, 1, 2, 3] as i (i)}
					<PoolCardSkeleton />
				{/each}
			</div>
		{:else if lista.length}
			<div class="grilla-pools">
				{#each lista as pool (pool.id)}
					<PoolCard {pool} />
				{/each}
			</div>
		{:else if !error}
			<div class="vacio">
				<Bolsitas variante="durmiendo" />
				<h3>Todavía no hay pools</h3>
				<p>Sé la primera persona en armar una compra colectiva en tu barrio.</p>
				<Boton variante="primario" href={resolve(enlaceCta)}>{textoCta}</Boton>
			</div>
		{/if}
	</section>
{/snippet}

<section class="hero">
	<div class="hero__texto">
		<h1 class="hero__titulo">
			Comprá en conjunto, <span
				>pagá menos<svg
					class="hero__trazo"
					viewBox="0 0 200 12"
					preserveAspectRatio="none"
					aria-hidden="true"
					><path d="M3 9C50 3 120 2 197 6" pathLength="1" /></svg
				></span
			>
		</h1>
		<p class="hero__bajada">
			Encontrá pools de compra, sumate y conseguí mejores precios. Un pool es una compra en grupo:
			entre varios juntan la cantidad y cada uno paga su parte.
		</p>
		<div class="hero__acciones">
			{#if session.access}
				<Boton variante="primario" tamano="lg" href={resolve(enlaceCta)}>
					<!-- width/height explícitos: un <svg> sin tamaño propio queda 0×0 dentro del flex del botón. -->
					<svg
						width="20"
						height="20"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						aria-hidden="true"
					>
						<circle cx="12" cy="12" r="9.5" />
						<path d="M12 8v8M8 12h8" />
					</svg>
					{textoCta}
				</Boton>
				<Boton variante="secundario" tamano="lg" href={resolve('/pools')}>Explorar pools</Boton>
			{:else}
				<Boton variante="primario" tamano="lg" href={resolve('/pools')}>Explorar pools</Boton>
				<Boton variante="secundario" tamano="lg" href={resolve('/registro')}>
					Crear una cuenta
				</Boton>
			{/if}
		</div>
		<p class="hero__nota">Gratis para crear y unirte. Sin intermediarios.</p>
	</div>

	<svg
		class="hero__ilustracion"
		width="420"
		height="250"
		viewBox="0 0 420 250"
		fill="none"
		aria-hidden="true"
	>
		<!-- Entrada (una vez) en los <g> externos; vida continua (respirar, mirar,
		     parpadear, saludar) en los internos, para que no se pisen las animaciones. -->
		<g class="escena__destellos">
			<g class="vida__titilar">
				<path
					d="M150 22l4 14M178 12l-2 16M206 24l-6 12M300 30l10 8M318 60l14-2M110 48l-12-6"
					stroke="#EA6A1F"
					stroke-width="4"
					stroke-linecap="round"
				/>
			</g>
			<path class="vida__brillo" d="M330 22l6 6-6 6-6-6z" fill="#DE3A3A" style="transform-origin: 330px 28px" />
			<path
				class="vida__brillo vida__brillo--2"
				d="M90 30l5 5-5 5-5-5z"
				fill="#F59E0B"
				style="transform-origin: 90px 35px"
			/>
		</g>

		<g class="escena__persona escena__persona--1">
			<g class="vida__respirar vida__respirar--1">
				<!-- Brazo que saluda: gira desde el hombro. -->
				<g class="vida__saludar">
					<path d="M52 150L26 112" stroke="#EA6A1F" stroke-width="15" stroke-linecap="round" />
					<circle cx="25" cy="106" r="8" fill="#E8B48F" />
				</g>
				<rect x="40" y="128" width="78" height="122" rx="34" fill="#EA6A1F" />
				<g class="vida__mirar vida__mirar--1">
					<circle cx="79" cy="100" r="24" fill="#E8B48F" />
					<path d="M56 96a24 24 0 0 1 46 -6c-8 -6 -30 -8 -46 6z" fill="#3B2A22" />
					<g class="vida__parpadear vida__parpadear--1" style="transform-origin: 79px 104px">
						<circle cx="71" cy="104" r="2.6" fill="#2A1D17" />
						<circle cx="87" cy="104" r="2.6" fill="#2A1D17" />
					</g>
					<path d="M73 112q6 5 12 0" stroke="#2A1D17" stroke-width="2" stroke-linecap="round" />
				</g>
			</g>
		</g>

		<g class="escena__persona escena__persona--2">
			<g class="vida__respirar vida__respirar--2">
				<rect x="132" y="96" width="90" height="154" rx="38" fill="#DE3A3A" />
				<g class="vida__mirar vida__mirar--2">
					<circle cx="177" cy="68" r="26" fill="#C98B63" />
					<path d="M151 64c2-20 22-30 40-22 8 4 12 10 12 18-12-10-32-12-52 4z" fill="#B4471D" />
					<g class="vida__parpadear vida__parpadear--2" style="transform-origin: 177px 73px">
						<circle cx="168" cy="73" r="2.8" fill="#2A1D17" />
						<circle cx="186" cy="73" r="2.8" fill="#2A1D17" />
					</g>
					<path d="M170 82q7 5 14 0" stroke="#2A1D17" stroke-width="2" stroke-linecap="round" />
				</g>
			</g>
		</g>

		<g class="escena__persona escena__persona--3">
			<g class="vida__respirar vida__respirar--3">
				<rect x="238" y="122" width="74" height="128" rx="32" fill="#FFFFFF" />
				<g class="vida__mirar vida__mirar--3">
					<circle cx="275" cy="96" r="23" fill="#F2CDB2" />
					<path d="M252 92c0-16 14-26 28-24 12 2 18 10 18 22-10-8-28-10-46 2z" fill="#2A1D17" />
					<g class="vida__parpadear vida__parpadear--3" style="transform-origin: 275px 100px">
						<circle cx="268" cy="100" r="2.5" fill="#2A1D17" />
						<circle cx="283" cy="100" r="2.5" fill="#2A1D17" />
					</g>
					<path d="M270 108q5 4 11 0" stroke="#2A1D17" stroke-width="2" stroke-linecap="round" />
				</g>
			</g>
		</g>

		<g class="escena__caja">
			<rect x="86" y="140" width="110" height="74" rx="6" fill="#E9AE74" />
			<path d="M86 162h110M141 140v22" stroke="#C98446" stroke-width="4" />
		</g>

		<g class="escena__carrito">
			<g class="vida__balancear">
				<path
					d="M300 150h20l14 62h70l10-44h-90"
					stroke="#2A1D17"
					stroke-width="5"
					stroke-linecap="round"
					stroke-linejoin="round"
				/>
				<rect class="escena__producto" x="336" y="160" width="20" height="40" rx="4" fill="#F59E0B" />
				<rect class="escena__producto" x="360" y="170" width="18" height="30" rx="4" fill="#DE3A3A" />
				<rect class="escena__producto" x="382" y="166" width="16" height="34" rx="4" fill="#EA6A1F" />
				<circle cx="344" cy="230" r="8" fill="#2A1D17" />
				<circle cx="394" cy="230" r="8" fill="#2A1D17" />
			</g>
		</g>
	</svg>
</section>

{#if error}
	<div class="aviso-inicio">
		<Aviso variante="error">
			No se pudieron cargar los pools. Recargá la página para volver a intentar.
		</Aviso>
	</div>
{/if}

{#if sinPools}
	<section class="seccion" aria-labelledby="vacio-titulo">
		<div class="vacio">
			<Bolsitas variante="durmiendo" />
			<h2 id="vacio-titulo">Todavía no hay pools abiertos</h2>
			<p>Sé la primera persona en armar una compra colectiva en tu barrio.</p>
			<Boton variante="primario" href={resolve(enlaceCta)}>{textoCta}</Boton>
		</div>
	</section>
{:else}
	{@render seccion('destacados-titulo', 'Pools destacados', destacados)}
{/if}

<section class="como" aria-labelledby="como-titulo">
	<h2 class="como__titulo" id="como-titulo">Cómo funciona</h2>
	<ol class="como__pasos">
		<li class="como__paso">
			<span class="como__numero" aria-hidden="true">1</span>
			<h3>Pegá el enlace de la tienda</h3>
			<p>Completamos el producto, el precio y la imagen solos. Revisás que estén bien.</p>
		</li>
		<li class="como__paso">
			<span class="como__numero" aria-hidden="true">2</span>
			<h3>Armá el pool y compartilo</h3>
			<p>Definís cantidad total, mínimo por persona y hasta cuándo se puede sumar.</p>
		</li>
		<li class="como__paso">
			<span class="como__numero" aria-hidden="true">3</span>
			<h3>Coordiná pago y entrega</h3>
			<p>Cada persona reserva su parte, sube el comprobante y confirma cuando recibe.</p>
		</li>
	</ol>
	<p class="como__nota">
		¿Importás o comprás afuera?
		<a href={resolve('/comparar')}>Compará el costo final</a> con envío, impuestos y aduana estimada.
	</p>
</section>

{#if categorias.length}
	<section class="seccion" aria-labelledby="categorias-titulo">
		<div class="seccion__cabecera">
			<h2 class="seccion__titulo" id="categorias-titulo">Categorías</h2>
		</div>
		<ul class="categorias">
			{#each categorias as categoria (categoria.id)}
				<li>
					<a class="categoria" href={resolve(`/pools?categoria=${categoria.id}`)}>
						<span class="categoria__circulo">
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.8"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
							>
								{#each iconoCategoria(categoria.nombre) as d}
									<path {d} />
								{/each}
							</svg>
						</span>
						<span class="categoria__nombre">{categoria.nombre}</span>
					</a>
				</li>
			{/each}
		</ul>
	</section>
{/if}

{#if !sinPools && cercanos.length}
	{@render seccion('cercanos-titulo', 'Pools cerca de completarse', cercanos)}
{/if}

<style>
	.hero {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-6);
		padding: clamp(1.75rem, 4vw, 2.75rem);
		border-radius: var(--radio-lg);
		background: var(--melocoton-fuerte);
		overflow: hidden;
	}

	.hero__texto {
		display: flex;
		flex: 1 1 380px;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--e-4);
	}

	/* Entrada escalonada: título, bajada, botones y nota. */
	.hero__texto > * {
		animation: aparecer 420ms var(--curva) both;
	}

	.hero__texto > :nth-child(2) {
		animation-delay: 70ms;
	}

	.hero__texto > :nth-child(3) {
		animation-delay: 140ms;
	}

	.hero__texto > :nth-child(4) {
		animation-delay: 210ms;
	}

	/* Subrayado a mano bajo "pagá menos": se dibuja cuando el título ya entró. */
	.hero__titulo span {
		position: relative;
		white-space: nowrap;
	}

	.hero__trazo {
		position: absolute;
		left: 0;
		right: 0;
		bottom: -0.08em;
		width: 100%;
		height: 0.28em;
		overflow: visible;
		pointer-events: none;
	}

	.hero__trazo path {
		fill: none;
		stroke: var(--acento-naranja);
		stroke-width: 4;
		stroke-linecap: round;
		vector-effect: non-scaling-stroke;
		stroke-dasharray: 1;
		stroke-dashoffset: 1;
		animation: dibujar-trazo 600ms var(--curva) 450ms forwards;
	}

	@keyframes dibujar-trazo {
		to {
			stroke-dashoffset: 0;
		}
	}

	/* Escena de la ilustración: entrada una sola vez (piezas externas). */
	.escena__persona,
	.escena__caja,
	.escena__carrito,
	.escena__destellos,
	.escena__producto {
		transform-box: fill-box;
		transform-origin: 50% 100%;
	}

	.escena__persona {
		animation: surgir 520ms cubic-bezier(0.22, 1, 0.36, 1) both;
	}

	.escena__persona--2 {
		animation-delay: 150ms;
	}

	.escena__persona--3 {
		animation-delay: 250ms;
	}

	.escena__caja {
		animation: caer 520ms cubic-bezier(0.22, 1, 0.36, 1) 520ms both;
	}

	.escena__carrito {
		animation: llegar 650ms var(--curva) 450ms both;
	}

	.escena__producto {
		animation: caer 420ms cubic-bezier(0.22, 1, 0.36, 1) both;
	}

	.escena__producto:nth-of-type(1) {
		animation-delay: 950ms;
	}

	.escena__producto:nth-of-type(2) {
		animation-delay: 1030ms;
	}

	.escena__producto:nth-of-type(3) {
		animation-delay: 1110ms;
	}

	.escena__destellos {
		transform-origin: 50% 50%;
		animation: destellar 500ms cubic-bezier(0.22, 1, 0.36, 1) 1200ms both;
	}

	@keyframes surgir {
		from {
			opacity: 0;
			transform: translateY(24px) scale(0.92);
		}
	}

	@keyframes caer {
		from {
			opacity: 0;
			transform: translateY(-36px);
		}
	}

	@keyframes llegar {
		from {
			opacity: 0;
			transform: translateX(60px);
		}
	}

	@keyframes destellar {
		from {
			opacity: 0;
			transform: scale(0.6);
		}
	}

	/* Vida continua (piezas internas). Duraciones distintas para que las tres
	   personas nunca se muevan sincronizadas. Con "reducir movimiento" se apaga. */
	.vida__respirar,
	.vida__mirar,
	.vida__balancear {
		transform-box: fill-box;
		transform-origin: 50% 100%;
	}

	.vida__respirar {
		animation: respirar 3.2s ease-in-out infinite;
	}

	.vida__respirar--2 {
		animation-duration: 3.8s;
		animation-delay: -1.2s;
	}

	.vida__respirar--3 {
		animation-duration: 2.9s;
		animation-delay: -0.6s;
	}

	.vida__mirar {
		animation: mirar 6s ease-in-out 1.6s infinite;
	}

	.vida__mirar--2 {
		animation-duration: 7.4s;
		animation-delay: 2.4s;
	}

	.vida__mirar--3 {
		animation-name: mirar-carrito;
		animation-duration: 5.2s;
		animation-delay: 2s;
	}

	.vida__parpadear {
		animation: parpadear 4.2s 1.8s infinite;
	}

	.vida__parpadear--2 {
		animation-duration: 5.3s;
		animation-delay: 2.6s;
	}

	.vida__parpadear--3 {
		animation-duration: 4.7s;
		animation-delay: 3.1s;
	}

	.vida__saludar {
		transform-origin: 52px 150px;
		animation: saludar 4.5s ease-in-out 1.4s infinite;
	}

	.vida__balancear {
		transform-origin: 50% 100%;
		animation: balancear 5s ease-in-out 1.8s infinite;
	}

	.vida__titilar {
		animation: titilar 2.6s ease-in-out 1.8s infinite;
	}

	.vida__brillo {
		animation: brillar 3s ease-in-out 1.8s infinite;
	}

	.vida__brillo--2 {
		animation-delay: 3.2s;
	}

	@keyframes respirar {
		0%,
		100% {
			transform: translateY(0) scaleY(1);
		}
		50% {
			transform: translateY(-3px) scaleY(1.015);
		}
	}

	@keyframes mirar {
		0%,
		60%,
		100% {
			transform: rotate(0deg);
		}
		70%,
		85% {
			transform: rotate(-6deg);
		}
	}

	@keyframes mirar-carrito {
		0%,
		55%,
		100% {
			transform: rotate(0deg);
		}
		65%,
		85% {
			transform: rotate(7deg);
		}
	}

	@keyframes parpadear {
		0%,
		92%,
		100% {
			transform: scaleY(1);
		}
		95% {
			transform: scaleY(0.1);
		}
	}

	@keyframes saludar {
		0%,
		45%,
		100% {
			transform: rotate(0deg);
		}
		52% {
			transform: rotate(-16deg);
		}
		59% {
			transform: rotate(10deg);
		}
		66% {
			transform: rotate(-16deg);
		}
		73% {
			transform: rotate(10deg);
		}
		80% {
			transform: rotate(0deg);
		}
	}

	@keyframes balancear {
		0%,
		70%,
		100% {
			transform: rotate(0deg);
		}
		78% {
			transform: rotate(-2.5deg);
		}
		86% {
			transform: rotate(1.5deg);
		}
		93% {
			transform: rotate(-0.5deg);
		}
	}

	@keyframes titilar {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.35;
		}
	}

	@keyframes brillar {
		0%,
		100% {
			transform: scale(1) rotate(0deg);
		}
		50% {
			transform: scale(1.35) rotate(45deg);
		}
	}

	.hero__titulo {
		max-width: 620px;
		font-size: var(--texto-3xl);
	}

	.hero__titulo span {
		color: var(--marca);
	}

	.hero__bajada {
		max-width: 420px;
		margin: 0;
		font-size: var(--texto-md);
		color: var(--tinta-suave);
	}

	.hero__acciones {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-3);
	}

	.hero__nota {
		margin: calc(var(--e-1) * -1) 0 0;
		font-size: var(--texto-xs);
		/* Sobre el melocotón del hero, --tinta-tenue queda en ~4.0:1. */
		color: var(--tinta-suave);
	}

	.hero__ilustracion {
		flex: none;
		max-width: 100%;
		height: auto;
	}

	.aviso-inicio {
		margin-top: var(--e-6);
	}

	.como {
		margin-top: var(--e-8);
		padding: var(--e-6);
		border-radius: var(--radio-lg);
		background: var(--crema);
	}

	.como__titulo {
		margin-bottom: var(--e-5);
		font-size: var(--texto-xl);
	}

	.como__pasos {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--e-5);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.como__paso {
		display: grid;
		gap: var(--e-2);
		align-content: start;
	}

	.como__numero {
		display: grid;
		place-items: center;
		width: 2rem;
		height: 2rem;
		border-radius: 50%;
		background: var(--marca);
		color: #fff;
		font-family: var(--fuente-display);
		font-size: var(--texto-sm);
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}

	.como__paso h3 {
		font-size: var(--texto-md);
	}

	.como__paso p {
		margin: 0;
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
	}

	.como__nota {
		margin: var(--e-5) 0 0;
		padding-top: var(--e-4);
		border-top: 1px solid var(--linea);
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
	}

	@media (max-width: 720px) {
		.como {
			padding: var(--e-5);
		}

		.como__pasos {
			grid-template-columns: 1fr;
		}
	}

	.seccion {
		margin-top: var(--e-7);
	}

	.seccion__cabecera {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--e-3);
		margin-bottom: var(--e-5);
	}

	.seccion__titulo {
		font-size: var(--texto-xl);
	}

	.seccion__enlace {
		font-size: var(--texto-sm);
		font-weight: 700;
	}

	.categorias {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
		gap: var(--e-4);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.categoria {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--e-2);
		padding: var(--e-2) 0;
		color: var(--tinta);
		font-size: var(--texto-sm);
		font-weight: 500;
	}

	.categoria:hover {
		color: var(--marca-fuerte);
		text-decoration: none;
	}

	.categoria__circulo {
		display: grid;
		place-items: center;
		width: 72px;
		height: 72px;
		border-radius: 50%;
	}

	.categoria__circulo svg {
		width: 30px;
		height: 30px;
	}

	.categorias li:nth-child(3n + 1) .categoria__circulo {
		background: var(--melocoton-fuerte);
		color: var(--naranja-fuerte);
	}

	.categorias li:nth-child(3n + 2) .categoria__circulo {
		background: var(--melocoton);
		color: var(--marca);
	}

	.categorias li:nth-child(3n + 3) .categoria__circulo {
		background: var(--crema);
		color: var(--naranja-oscuro);
	}

	.categoria__nombre {
		overflow-wrap: anywhere;
		text-align: center;
	}
</style>
