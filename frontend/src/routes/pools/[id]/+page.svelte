<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, fieldErrors } from '$lib/api.js';
	import { etiquetaEstado, etiquetaPago } from '$lib/estados.js';
	import { fecha, iniciales, moneda } from '$lib/formato.js';
	import { session } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';

	let pool = $state(null);
	let cargando = $state(true);
	let error = $state('');
	let cantidad = $state(1);
	let accionError = $state({});
	const aviso = $derived(page.url.searchParams.get('aviso'));

	const MENSAJES_ESTADO = {
		confirmar: 'Pedido confirmado.',
		finalizar: 'Pool finalizado.',
		cancelar: 'Pool cancelado.'
	};

	$effect(() => {
		cargar(page.params.id);
	});

	async function cargar(id) {
		cargando = true;
		error = '';
		try {
			pool = await api(`/pools/${id}/`);
			const mia = pool.miembros.find((m) => m.usuario.id === session.user?.id);
			cantidad = mia ? mia.cantidad : pool.min_por_integrante;
		} catch (e) {
			error = e.status === 404 ? 'El pool no existe.' : 'No se pudo cargar el pool.';
		} finally {
			cargando = false;
		}
	}

	const esCreador = $derived(session.user?.id === pool?.creador?.id);
	const miMembresia = $derived(
		pool?.miembros?.find((m) => m.usuario.id === session.user?.id) ?? null
	);
	const puedeUnirse = $derived(
		pool?.estado === 'abierto' && !esCreador && !miMembresia && pool.disponible >= pool.min_por_integrante
	);

	async function unirse() {
		accionError = {};
		try {
			await api(`/pools/${pool.id}/unirse/`, {
				method: 'POST',
				body: { cantidad: Number(cantidad) }
			});
			await cargar(pool.id);
			notificar('Te uniste al pool.');
		} catch (e) {
			accionError = fieldErrors(e.data);
		}
	}

	async function salir() {
		accionError = {};
		try {
			await api(`/pools/${pool.id}/salir/`, { method: 'DELETE' });
			await cargar(pool.id);
			notificar('Saliste del pool.');
		} catch (e) {
			accionError = fieldErrors(e.data);
		}
	}

	async function guardarCantidad() {
		accionError = {};
		try {
			pool = await api(`/pools/${pool.id}/mi-membresia/`, {
				method: 'PATCH',
				body: { cantidad: Number(cantidad) }
			});
			notificar('Cantidad actualizada.');
		} catch (e) {
			accionError = fieldErrors(e.data);
		}
	}

	async function cambiarEstado(accion) {
		accionError = {};
		try {
			pool = await api(`/pools/${pool.id}/${accion}/`, { method: 'POST' });
			notificar(MENSAJES_ESTADO[accion] ?? 'Estado actualizado.');
		} catch (e) {
			accionError = fieldErrors(e.data);
		}
	}

	async function eliminar() {
		if (!confirm('¿Eliminar este pool? Esta acción no se puede deshacer.')) return;
		accionError = {};
		try {
			await api(`/pools/${pool.id}/`, { method: 'DELETE' });
			notificar('Pool eliminado.');
			goto(resolve('/mis-pools'));
		} catch (e) {
			accionError = fieldErrors(e.data);
		}
	}
</script>

<svelte:head>
	<title>{pool?.titulo ?? 'Pool'} — PoolShop</title>
</svelte:head>

{#if cargando}
	<div class="cargando" role="status"><span class="spinner spinner--grande"></span> Cargando el pool…</div>
{:else if error}
	<div class="vacio">
		<h3>{error}</h3>
		<p>Puede que lo hayan eliminado o que el enlace ya no sea válido.</p>
		<a class="btn btn--secundario" href={resolve('/pools')}>Volver a pools</a>
	</div>
{:else}
	<a class="volver" href={resolve('/pools')}>Volver a pools</a>

	<div class="detalle">
		<div>
			<header class="encabezado">
				<span class="badge badge--{pool.estado}">{etiquetaEstado(pool.estado)}</span>
				<h1>{pool.titulo}</h1>
				<p class="encabezado__producto">{pool.nombre_producto}</p>
			</header>

			{#if aviso === 'imagenes'}
				<div class="alerta alerta--aviso aviso" role="alert">
					El pool se creó, pero algunas imágenes no se pudieron subir.
				</div>
			{/if}

			{#if pool.imagenes.length}
				<div class="galeria">
					{#each pool.imagenes as imagen (imagen.id)}
						<img
							class="galeria__img"
							src={imagen.imagen}
							alt={pool.titulo}
							width="800"
							height="600"
							loading="lazy"
						/>
					{/each}
				</div>
			{/if}

			{#if pool.descripcion}
				<section class="bloque">
					<h2>Descripción</h2>
					<p class="prosa">{pool.descripcion}</p>
				</section>
			{/if}

			<section class="bloque">
				<h2>Detalles de la compra</h2>
				<dl class="ficha">
					<div class="ficha__item">
						<dt>Producto</dt>
						<dd>{pool.nombre_producto}</dd>
					</div>
					<div class="ficha__item">
						<dt>Categoría</dt>
						<dd>{pool.categoria_nombre}</dd>
					</div>
					<div class="ficha__item">
						<dt>Precio unitario</dt>
						<dd>{moneda(pool.precio_unitario)}</dd>
					</div>
					<div class="ficha__item">
						<dt>Cantidad total</dt>
						<dd>{pool.cantidad_total}</dd>
					</div>
					<div class="ficha__item">
						<dt>Del creador</dt>
						<dd>{pool.cantidad_creador}</dd>
					</div>
					<div class="ficha__item">
						<dt>Mínimo por integrante</dt>
						<dd>{pool.min_por_integrante}</dd>
					</div>
					<div class="ficha__item">
						<dt>Caducidad</dt>
						<dd>{fecha(pool.fecha_caducidad)}</dd>
					</div>
					<div class="ficha__item">
						<dt>Tipo de pago</dt>
						<dd>{etiquetaPago(pool.tipo_pago)}</dd>
					</div>
					<div class="ficha__item">
						<dt>Dirección</dt>
						<dd>{pool.direccion}</dd>
					</div>
					<div class="ficha__item">
						<dt>Ciudad</dt>
						<dd>{pool.ciudad}</dd>
					</div>
					{#if pool.enlace}
						<div class="ficha__item ficha__item--ancho">
							<dt>Enlace</dt>
							<dd>
								<button
									class="btn btn--secundario btn--sm"
									type="button"
									onclick={() => window.open(pool.enlace, '_blank', 'noopener')}
								>
									Abrir enlace del producto
								</button>
							</dd>
						</div>
					{/if}
				</dl>
			</section>

			<section class="bloque">
				<h2>Integrantes</h2>
				{#if pool.miembros.length}
					<ul class="miembros">
						{#each pool.miembros as miembro (miembro.id)}
							<li class="miembro">
								<span class="miembro__avatar" aria-hidden="true">
									{iniciales(miembro.usuario.username)}
								</span>
								<span class="miembro__nombre">{miembro.usuario.username}</span>
								<span class="miembro__cantidad">{miembro.cantidad} u.</span>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="muted">Nadie se unió todavía.</p>
				{/if}
			</section>
		</div>

		<aside class="lateral panel">
			<div class="lateral__precio">
				<span class="lateral__precio-valor">{moneda(pool.precio_unitario)}</span>
				<span class="lateral__precio-unidad">por unidad</span>
			</div>

			<div class="lateral__disponibilidad">
				<div class="lateral__fila">
					<span>Disponible</span>
					<strong>{pool.disponible} de {pool.cantidad_total}</strong>
				</div>
				<progress
					class="progreso"
					value={pool.cantidad_total - pool.disponible}
					max={pool.cantidad_total}
					aria-label="Unidades comprometidas"
				></progress>
			</div>

			<p class="lateral__caduca">Caduca el {fecha(pool.fecha_caducidad)}</p>

			<div class="lateral__acciones">
				{#if !session.access && pool.estado === 'abierto' && pool.disponible >= pool.min_por_integrante}
					<p class="muted">Ingresá para unirte a este pool.</p>
					<a class="btn btn--primario btn--bloque" href={resolve('/login')}>Ingresar</a>
				{:else if esCreador}
					{#if pool.estado === 'abierto'}
						<a class="btn btn--secundario btn--bloque" href={resolve(`/pools/${pool.id}/editar`)}>
							Editar pool
						</a>
						<button class="btn btn--peligro-suave btn--bloque" type="button" onclick={eliminar}>
							Eliminar
						</button>
					{/if}
					{#if pool.estado === 'listo'}
						<button
							class="btn btn--primario btn--bloque"
							type="button"
							onclick={() => cambiarEstado('confirmar')}
						>
							Confirmar pedido
						</button>
					{/if}
					{#if pool.estado === 'en_curso'}
						<button
							class="btn btn--primario btn--bloque"
							type="button"
							onclick={() => cambiarEstado('finalizar')}
						>
							Finalizar
						</button>
					{/if}
					{#if pool.estado === 'abierto' || pool.estado === 'listo'}
						<button
							class="btn btn--peligro-suave btn--bloque"
							type="button"
							onclick={() => cambiarEstado('cancelar')}
						>
							Cancelar
						</button>
					{/if}
				{:else if miMembresia}
					{#if pool.estado === 'abierto' || pool.estado === 'listo'}
						<div class="campo">
							<label for="cantidad">Tu cantidad</label>
							<input
								id="cantidad"
								name="cantidad"
								type="number"
								inputmode="numeric"
								min={pool.min_por_integrante}
								max={pool.disponible + miMembresia.cantidad}
								bind:value={cantidad}
							/>
							<p class="ayuda">
								Mínimo {pool.min_por_integrante}, máximo {pool.disponible + miMembresia.cantidad}.
							</p>
						</div>
						<button class="btn btn--primario btn--bloque" type="button" onclick={guardarCantidad}>
							Guardar cantidad
						</button>
						<button class="btn btn--peligro-suave btn--bloque" type="button" onclick={salir}>
							Salir del pool
						</button>
					{/if}
				{:else if puedeUnirse}
					<div class="campo">
						<label for="cantidad">Cantidad a reservar</label>
						<input
							id="cantidad"
							name="cantidad"
							type="number"
							inputmode="numeric"
							min={pool.min_por_integrante}
							max={pool.disponible}
							bind:value={cantidad}
						/>
						<p class="ayuda">Mínimo {pool.min_por_integrante}, disponible {pool.disponible}.</p>
					</div>
					<button class="btn btn--primario btn--bloque" type="button" onclick={unirse}>
						Unirme al pool
					</button>
				{:else if pool.estado !== 'abierto'}
					<p class="muted">Este pool ya no acepta nuevas reservas.</p>
				{/if}

				{#if accionError.cantidad}
					<p class="error" role="alert">{accionError.cantidad}</p>
				{/if}
				{#if accionError.detail || accionError.non_field_errors}
					<p class="error" role="alert">{accionError.detail || accionError.non_field_errors}</p>
				{/if}
				{#if accionError.estado}
					<p class="error" role="alert">{accionError.estado}</p>
				{/if}
			</div>

			<div class="lateral__meta">
				<p>Organiza <strong>{pool.creador.username}</strong></p>
				<p>{pool.ciudad} · {pool.vistas} vistas</p>
			</div>
		</aside>
	</div>
{/if}

<style>
	.volver {
		display: inline-block;
		margin-bottom: var(--e-5);
		font-size: var(--texto-sm);
		font-weight: 600;
		color: var(--tinta-suave);
	}

	.volver:hover {
		color: var(--acento);
	}

	.detalle {
		display: grid;
		grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
		gap: var(--e-7);
		align-items: start;
	}

	.encabezado .badge {
		margin-bottom: var(--e-3);
	}

	.encabezado h1 {
		font-size: var(--texto-2xl);
	}

	.encabezado__producto {
		margin-top: var(--e-2);
		font-size: var(--texto-md);
		color: var(--tinta-suave);
	}

	.aviso {
		margin-top: var(--e-5);
	}

	.galeria {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--e-3);
		margin-top: var(--e-6);
	}

	.galeria__img {
		width: 100%;
		height: 100%;
		aspect-ratio: 4 / 3;
		object-fit: cover;
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
	}

	.galeria__img:first-child {
		grid-column: 1 / -1;
		aspect-ratio: 16 / 9;
	}

	.bloque {
		margin-top: var(--e-7);
		padding-top: var(--e-5);
		border-top: 1px solid var(--linea);
	}

	.bloque h2 {
		margin-bottom: var(--e-4);
		font-size: var(--texto-lg);
	}

	.prosa {
		max-width: var(--ancho-lectura);
		color: var(--tinta-suave);
		white-space: pre-line;
	}

	.ficha {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--e-4) var(--e-6);
		margin: 0;
	}

	.ficha__item--ancho {
		grid-column: 1 / -1;
	}

	.ficha dt {
		margin-bottom: var(--e-1);
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.ficha dd {
		margin: 0;
		font-size: var(--texto-sm);
		word-break: break-word;
	}

	.miembros {
		display: flex;
		flex-direction: column;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.miembro {
		display: flex;
		align-items: center;
		gap: var(--e-3);
		padding: var(--e-3) 0;
		border-bottom: 1px solid var(--linea);
	}

	.miembro:last-child {
		border-bottom: 0;
	}

	.miembro__avatar {
		flex: none;
		width: 2.25rem;
		height: 2.25rem;
		display: grid;
		place-items: center;
		border-radius: 50%;
		background: var(--acento-suave);
		color: var(--acento);
		font-family: var(--fuente-display);
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.miembro__nombre {
		font-size: var(--texto-sm);
		font-weight: 500;
		min-width: 0;
		overflow-wrap: anywhere;
	}

	.miembro__cantidad {
		margin-left: auto;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.lateral {
		position: sticky;
		top: calc(var(--alto-cabecera) + var(--e-5));
		padding: var(--e-6);
	}

	.lateral__precio {
		display: flex;
		align-items: baseline;
		gap: var(--e-2);
	}

	.lateral__precio-valor {
		font-family: var(--fuente-display);
		font-size: var(--texto-xl);
		font-weight: 600;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
	}

	.lateral__precio-unidad {
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.lateral__disponibilidad {
		margin-top: var(--e-5);
	}

	.lateral__fila {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--e-3);
		margin-bottom: var(--e-2);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.lateral__fila strong {
		color: var(--tinta);
	}

	.lateral__caduca {
		margin-top: var(--e-3);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.lateral__acciones {
		display: flex;
		flex-direction: column;
		gap: var(--e-3);
		margin-top: var(--e-5);
		padding-top: var(--e-5);
		border-top: 1px solid var(--linea);
	}

	.lateral__acciones .campo {
		margin-bottom: 0;
	}

	.lateral__meta {
		margin-top: var(--e-5);
		padding-top: var(--e-4);
		border-top: 1px solid var(--linea);
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.lateral__meta p {
		margin: 0 0 var(--e-1);
	}

	@media (max-width: 900px) {
		.detalle {
			grid-template-columns: 1fr;
			gap: var(--e-6);
		}

		.lateral {
			position: static;
		}
	}

	@media (max-width: 560px) {
		.galeria {
			grid-template-columns: 1fr;
		}

		.ficha {
			grid-template-columns: 1fr;
		}
	}
</style>
