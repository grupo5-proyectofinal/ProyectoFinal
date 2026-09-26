<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, fieldErrors } from '$lib/api.js';
	import { etiquetaEstado } from '$lib/estados.js';
	import { session } from '$lib/session.svelte.js';

	let pool = $state(null);
	let cargando = $state(true);
	let error = $state('');
	let cantidad = $state(1);
	let accionError = $state({});
	const aviso = $derived(page.url.searchParams.get('aviso'));

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
		} catch (e) {
			accionError = fieldErrors(e.data);
		}
	}

	async function salir() {
		accionError = {};
		try {
			await api(`/pools/${pool.id}/salir/`, { method: 'DELETE' });
			await cargar(pool.id);
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
		} catch (e) {
			accionError = fieldErrors(e.data);
		}
	}

	async function cambiarEstado(accion) {
		accionError = {};
		try {
			pool = await api(`/pools/${pool.id}/${accion}/`, { method: 'POST' });
		} catch (e) {
			accionError = fieldErrors(e.data);
		}
	}

	async function eliminar() {
		if (!confirm('¿Eliminar este pool? Esta acción no se puede deshacer.')) return;
		accionError = {};
		try {
			await api(`/pools/${pool.id}/`, { method: 'DELETE' });
			goto(resolve('/mis-pools'));
		} catch (e) {
			accionError = fieldErrors(e.data);
		}
	}
</script>

{#if cargando}
	<p class="muted">Cargando…</p>
{:else if error}
	<p class="error">{error}</p>
	<a class="btn secundario" href={resolve('/pools')}>Volver</a>
{:else}
	<section class="tarjeta">
		<span class="badge badge-{pool.estado}">{etiquetaEstado(pool.estado)}</span>
		<h1>{pool.titulo}</h1>
		{#if aviso === 'imagenes'}
			<p class="error">El pool se creó, pero algunas imágenes no se pudieron subir.</p>
		{/if}
		{#if pool.imagenes.length}
			<div class="galeria">
				{#each pool.imagenes as imagen (imagen.id)}
					<img src={imagen.imagen} alt={pool.titulo} />
				{/each}
			</div>
		{/if}
		<dl class="detalle">
			<dt>Producto</dt><dd>{pool.nombre_producto}</dd>
			<dt>Categoría</dt><dd>{pool.categoria_nombre}</dd>
			<dt>Descripción</dt><dd>{pool.descripcion || '—'}</dd>
			{#if pool.enlace}
				<dt>Enlace</dt>
				<dd>
					<button class="enlace" type="button" onclick={() => window.open(pool.enlace, '_blank', 'noopener')}>
						{pool.enlace}
					</button>
				</dd>
			{/if}
			<dt>Precio unitario</dt><dd>$ {pool.precio_unitario}</dd>
			<dt>Cantidad total</dt><dd>{pool.cantidad_total}</dd>
			<dt>Del creador</dt><dd>{pool.cantidad_creador}</dd>
			<dt>Disponible</dt><dd>{pool.disponible}</dd>
			<dt>Mínimo por integrante</dt><dd>{pool.min_por_integrante}</dd>
			<dt>Caducidad</dt><dd>{pool.fecha_caducidad}</dd>
			<dt>Tipo de pago</dt><dd>{pool.tipo_pago}</dd>
			<dt>Dirección</dt><dd>{pool.direccion}</dd>
			<dt>Ciudad</dt><dd>{pool.ciudad}</dd>
			<dt>Creador</dt><dd>{pool.creador.username}</dd>
			<dt>Vistas</dt><dd>{pool.vistas}</dd>
		</dl>

		<div class="acciones">
			{#if !session.access}
				<p class="muted">Ingresá para unirte a este pool.</p>
				<a class="btn" href={resolve('/login')}>Ingresar</a>
			{:else if esCreador}
				{#if pool.estado === 'abierto'}
					<a class="btn secundario" href={resolve(`/pools/${pool.id}/editar`)}>Editar</a>
					<button class="btn peligro" type="button" onclick={eliminar}>Eliminar</button>
				{/if}
				{#if pool.estado === 'listo'}
					<button class="btn" type="button" onclick={() => cambiarEstado('confirmar')}>
						Confirmar pedido
					</button>
				{/if}
				{#if pool.estado === 'en_curso'}
					<button class="btn" type="button" onclick={() => cambiarEstado('finalizar')}>
						Finalizar
					</button>
				{/if}
				{#if pool.estado === 'abierto' || pool.estado === 'listo'}
					<button class="btn peligro" type="button" onclick={() => cambiarEstado('cancelar')}>
						Cancelar
					</button>
				{/if}
			{:else if miMembresia}
				{#if pool.estado === 'abierto' || pool.estado === 'listo'}
					<input
						type="number"
						min={pool.min_por_integrante}
						max={pool.disponible + miMembresia.cantidad}
						bind:value={cantidad}
						aria-label="Mi cantidad"
					/>
					<button class="btn" type="button" onclick={guardarCantidad}>Guardar cantidad</button>
					<button class="btn peligro" type="button" onclick={salir}>Salir</button>
				{/if}
			{:else if puedeUnirse}
				<input
					type="number"
					min={pool.min_por_integrante}
					max={pool.disponible}
					bind:value={cantidad}
					aria-label="Cantidad a unirme"
				/>
				<button class="btn" type="button" onclick={unirse}>Unirse</button>
			{/if}
		</div>
		{#if accionError.cantidad}
			<p class="error">{accionError.cantidad}</p>
		{/if}
		{#if accionError.detail || accionError.non_field_errors}
			<p class="error">{accionError.detail || accionError.non_field_errors}</p>
		{/if}
		{#if accionError.estado}
			<p class="error">{accionError.estado}</p>
		{/if}

		<h2>Miembros</h2>
		{#if pool.miembros.length}
			<ul>
				{#each pool.miembros as miembro (miembro.id)}
					<li>{miembro.usuario.username}: {miembro.cantidad}</li>
				{/each}
			</ul>
		{:else}
			<p class="muted">Nadie se unió todavía.</p>
		{/if}
	</section>
{/if}
