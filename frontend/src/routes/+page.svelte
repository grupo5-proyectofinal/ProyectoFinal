<script>
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
			cercanos = porCompletar.results.slice(0, 4);
			categorias = cats.results;
		} catch {
			destacados = [];
			cercanos = [];
			error = true;
		} finally {
			cargando = false;
		}
	}

	const enlaceCta = $derived(session.access ? '/pools/nuevo' : '/registro');
	const textoCta = $derived(session.access ? 'Crear un pool' : 'Crear una cuenta');
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
				<h3>Todavía no hay pools</h3>
				<p>Sé la primera persona en armar una compra colectiva en tu barrio.</p>
				<Boton variante="primario" href={resolve(enlaceCta)}>{textoCta}</Boton>
			</div>
		{/if}
	</section>
{/snippet}

<section class="hero">
	<div class="hero__texto">
		<h1 class="hero__titulo">Comprá en conjunto, <span>pagá menos</span></h1>
		<p class="hero__bajada">Encontrá pools de compra, sumate y conseguí mejores precios.</p>
		<Boton variante="primario" tamano="lg" href={resolve(enlaceCta)}>
			<svg
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
			Crear un pool
		</Boton>
	</div>

	<svg
		class="hero__ilustracion"
		width="420"
		height="250"
		viewBox="0 0 420 250"
		fill="none"
		aria-hidden="true"
	>
		<path
			d="M150 22l4 14M178 12l-2 16M206 24l-6 12M300 30l10 8M318 60l14-2M110 48l-12-6"
			stroke="#EA6A1F"
			stroke-width="4"
			stroke-linecap="round"
		/>
		<path d="M330 22l6 6-6 6-6-6z" fill="#DE3A3A" />
		<path d="M90 30l5 5-5 5-5-5z" fill="#F59E0B" />
		<rect x="40" y="128" width="78" height="122" rx="34" fill="#EA6A1F" />
		<circle cx="79" cy="100" r="24" fill="#E8B48F" />
		<path d="M56 96a24 24 0 0 1 46 -6c-8 -6 -30 -8 -46 6z" fill="#3B2A22" />
		<rect x="132" y="96" width="90" height="154" rx="38" fill="#DE3A3A" />
		<circle cx="177" cy="68" r="26" fill="#C98B63" />
		<path d="M151 64c2-20 22-30 40-22 8 4 12 10 12 18-12-10-32-12-52 4z" fill="#B4471D" />
		<rect x="238" y="122" width="74" height="128" rx="32" fill="#FFFFFF" />
		<circle cx="275" cy="96" r="23" fill="#F2CDB2" />
		<path d="M252 92c0-16 14-26 28-24 12 2 18 10 18 22-10-8-28-10-46 2z" fill="#2A1D17" />
		<rect x="86" y="140" width="110" height="74" rx="6" fill="#E9AE74" />
		<path d="M86 162h110M141 140v22" stroke="#C98446" stroke-width="4" />
		<path
			d="M300 150h20l14 62h70l10-44h-90"
			stroke="#2A1D17"
			stroke-width="5"
			stroke-linecap="round"
			stroke-linejoin="round"
		/>
		<rect x="336" y="160" width="20" height="40" rx="4" fill="#F59E0B" />
		<rect x="360" y="170" width="18" height="30" rx="4" fill="#DE3A3A" />
		<rect x="382" y="166" width="16" height="34" rx="4" fill="#EA6A1F" />
		<circle cx="344" cy="230" r="8" fill="#2A1D17" />
		<circle cx="394" cy="230" r="8" fill="#2A1D17" />
	</svg>
</section>

{#if error}
	<div class="aviso-inicio">
		<Aviso variante="error">
			No se pudieron cargar los pools. Recargá la página para volver a intentar.
		</Aviso>
	</div>
{/if}

{@render seccion('destacados-titulo', 'Pools destacados', destacados)}

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

{@render seccion('cercanos-titulo', 'Pools cerca de completarse', cercanos)}

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

	.hero__ilustracion {
		flex: none;
		max-width: 100%;
		height: auto;
	}

	.aviso-inicio {
		margin-top: var(--e-6);
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
