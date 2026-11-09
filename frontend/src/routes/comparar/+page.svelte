<script>
	// Comparaciones del usuario: el mismo producto en varias tiendas, por costo final.
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api, fieldErrors } from '$lib/api.js';
	import { fechaHora } from '$lib/historial.js';
	import { session } from '$lib/session.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let comparaciones = $state([]);
	let cargando = $state(true);
	let nueva = $state({ titulo: '', producto: '', cantidad: 10 });
	let errores = $state({});

	$effect(() => {
		if (!session.access) return;
		api('/comparaciones/')
			.then((r) => (comparaciones = r.results ?? r))
			.finally(() => (cargando = false));
	});

	async function crear(evento) {
		evento.preventDefault();
		errores = {};
		try {
			const creada = await api('/comparaciones/', { method: 'POST', body: nueva });
			goto(resolve(`/comparar/${creada.id}`));
		} catch (e) {
			errores = fieldErrors(e.data);
		}
	}
</script>

<svelte:head>
	<title>Comparar costos — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Comparar costo final</h1>
		<p>
			Cargá el mismo producto en varias tiendas o mayoristas y compará lo que realmente pagás:
			precio, envío, impuestos y, si importás, una estimación de la aduana.
		</p>
	</div>
</div>

{#if !session.access}
	<Aviso variante="info">
		<span><a href={resolve('/login?next=%2Fcomparar')}>Iniciá sesión</a> para armar tus comparaciones.</span>
	</Aviso>
{:else}
	<div class="columnas">
		<section>
			<h2>Mis comparaciones</h2>
			{#if cargando}
				<p class="estado">Cargando…</p>
			{:else if !comparaciones.length}
				<p class="estado">Todavía no armaste ninguna.</p>
			{:else}
				<ul class="lista">
					{#each comparaciones as comparacion (comparacion.id)}
						<li>
							<a href={resolve(`/comparar/${comparacion.id}`)}>{comparacion.titulo}</a>
							<span>
								{comparacion.cantidad_ofertas}
								{comparacion.cantidad_ofertas === 1 ? 'oferta' : 'ofertas'} · {fechaHora(comparacion.actualizado)}
							</span>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
		<Tarjeta class="relleno">
			<form class="nueva" onsubmit={crear}>
				<h2>Nueva comparación</h2>
				<label class="campo">
					<span>Título *</span>
					<input bind:value={nueva.titulo} required maxlength="200" placeholder="Ej.: Yerba para el pool del barrio" />
					{#if errores.titulo}<small class="error">{errores.titulo}</small>{/if}
				</label>
				<label class="campo">
					<span>Producto</span>
					<input bind:value={nueva.producto} maxlength="200" placeholder="Ej.: Yerba Playadito 1 kg" />
				</label>
				<label class="campo">
					<span>Cantidad que querés comprar *</span>
					<input type="number" min="1" required bind:value={nueva.cantidad} />
				</label>
				<Boton type="submit" variante="primario">Crear y cargar ofertas</Boton>
			</form>
		</Tarjeta>
	</div>
{/if}

<style>
	.columnas {
		display: grid;
		grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
		gap: var(--e-6);
		align-items: start;
	}

	h2 {
		margin: 0 0 var(--e-3);
		font-size: 1.15rem;
	}

	.lista {
		display: grid;
		gap: var(--e-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.lista li {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: var(--e-2);
		padding: var(--e-3) 0;
		border-bottom: 1px solid var(--linea);
	}

	.lista a {
		font-weight: 600;
	}

	.lista span,
	.estado {
		color: var(--tinta-tenue);
		font-size: var(--texto-sm);
	}

	.nueva {
		display: grid;
		gap: var(--e-3);
	}

	.campo {
		display: grid;
		gap: var(--e-1);
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.error {
		color: var(--texto-peligro);
		font-weight: 400;
	}

	@media (max-width: 800px) {
		.columnas {
			grid-template-columns: 1fr;
		}
	}
</style>
