<script>
	// Comparaciones del usuario: el mismo producto en varias tiendas, por costo final.
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { api, fieldErrors } from '$lib/api.js';
	import { fechaHora } from '$lib/historial.js';
	import { urlLogin } from '$lib/sesion.js';
	import { session } from '$lib/session.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Bolsitas from '$lib/Bolsitas.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let comparaciones = $state([]);
	let cargando = $state(true);
	let errorCarga = $state(false);
	let nueva = $state({ titulo: '', producto: '', cantidad: 10 });
	let errores = $state({});
	let creando = $state(false);

	$effect(() => {
		if (!session.access) return;
		cargar();
	});

	async function cargar() {
		cargando = true;
		errorCarga = false;
		try {
			const r = await api('/comparaciones/');
			comparaciones = r.results ?? r;
		} catch {
			// Sin esto, un fallo se veía como "Todavía no armaste ninguna".
			errorCarga = true;
		} finally {
			cargando = false;
		}
	}

	async function crear(evento) {
		evento.preventDefault();
		if (creando) return;
		creando = true;
		errores = {};
		try {
			const creada = await api('/comparaciones/', { method: 'POST', body: nueva });
			goto(resolve(`/comparar/${creada.id}`));
		} catch (e) {
			const porCampo = fieldErrors(e.data);
			errores = Object.keys(porCampo).length
				? porCampo
				: { detail: 'No se pudo crear la comparación. Revisá tu conexión e intentá de nuevo.' };
			creando = false;
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
		<span><a href={urlLogin('/comparar')}>Iniciá sesión</a> para armar tus comparaciones.</span>
	</Aviso>
	<div class="ejemplo">
		<h2>Qué compara</h2>
		<p>
			El comparador no ordena por el precio publicado: suma envío, impuestos y, si importás, una
			estimación de aduana. Por ejemplo, con números inventados:
		</p>
		<p class="ejemplo__cuenta">
			$ 10.000 de precio + $ 2.000 de envío + $ 2.100 de impuestos =
			<strong>$ 14.100 por unidad</strong>
		</p>
		<p class="ayuda">
			Ese total es el que se compara entre tiendas. Las alícuotas y el tipo de cambio son valores
			de referencia que carga el equipo.
		</p>
	</div>
{:else}
	<div class="columnas">
		<section>
			<h2>Mis comparaciones</h2>
			{#if cargando}
				<p class="estado" role="status">Cargando…</p>
			{:else if errorCarga}
				<Aviso variante="error">
					<span>No se pudieron cargar tus comparaciones.</span>
					<Boton variante="secundario" tamano="sm" onclick={cargar}>Reintentar</Boton>
				</Aviso>
			{:else if !comparaciones.length}
				<div class="vacio vacio--compacto">
					<Bolsitas variante="durmiendo" />
					<p>Todavía no armaste ninguna. Creá la primera con el formulario.</p>
				</div>
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
				<Campo id="titulo" etiqueta="Título" requerido error={errores.titulo}>
					{#snippet children(props)}
						<input
							id="titulo"
							bind:value={nueva.titulo}
							required
							maxlength="200"
							placeholder="Ej.: Yerba para el pool del barrio"
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo id="producto" etiqueta="Producto" error={errores.producto}>
					{#snippet children(props)}
						<input
							id="producto"
							bind:value={nueva.producto}
							maxlength="200"
							placeholder="Ej.: Yerba Playadito 1 kg"
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo
					id="cantidad"
					etiqueta="Cantidad que querés comprar"
					requerido
					ayuda="Se usa para repartir el envío y los impuestos por unidad."
					error={errores.cantidad}
				>
					{#snippet children(props)}
						<input id="cantidad" type="number" min="1" required bind:value={nueva.cantidad} {...props} />
					{/snippet}
				</Campo>
				{#if errores.detail || errores.non_field_errors}
					<Aviso variante="error">{errores.detail || errores.non_field_errors}</Aviso>
				{/if}
				<Boton tipo="submit" variante="primario" disabled={creando}>
					{creando ? 'Creando…' : 'Crear comparación'}
				</Boton>
			</form>
		</Tarjeta>
	</div>
{/if}

<style>
	.ejemplo {
		max-width: 62ch;
		margin-top: var(--e-6);
		padding: var(--e-5);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--crema);
	}

	.ejemplo h2 {
		margin: 0 0 var(--e-2);
		font-size: var(--texto-lg);
	}

	.ejemplo__cuenta {
		margin: var(--e-3) 0;
		padding: var(--e-3) var(--e-4);
		border-radius: var(--radio-sm);
		background: var(--superficie);
		font-variant-numeric: tabular-nums;
	}

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
	}

	.nueva :global(.ui-boton) {
		margin-top: var(--e-2);
	}

	@media (max-width: 800px) {
		.columnas {
			grid-template-columns: 1fr;
		}
	}
</style>
