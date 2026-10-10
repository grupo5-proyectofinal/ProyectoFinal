<script>
	import { tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, fieldErrors } from '$lib/api.js';
	import { mostrarAnalisis } from '$lib/confianza.js';
	import {
		conConfirmacion,
		desenlaceEliminacion,
		mensajeError,
		puedeEliminarDirecto,
		puedeSolicitarEliminacion,
		puedeVotarEliminacion
	} from '$lib/eliminacion.js';
	import { etiquetaEstado, etiquetaPago, puedeUnirse, tonoCategoria, tonoNombre } from '$lib/estados.js';
	import { diasHasta, fecha, iniciales, moneda, vistas } from '$lib/formato.js';
	import { esIntegrante, fechaHora, textoEvento } from '$lib/historial.js';
	import MapaPool from '$lib/MapaPool.svelte';
	import MiniPerfil from '$lib/MiniPerfil.svelte';
	import PanelEliminacion from '$lib/PanelEliminacion.svelte';
	import PanelEnlace from '$lib/PanelEnlace.svelte';
	import { rutaTab } from '$lib/pestanas.js';
	import { session } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';
	import { coordsValidas } from '$lib/ubicacion.js';
	import { payloadUnion } from '$lib/union.js';

	let pool = $state(null);
	let cargando = $state(true);
	let error = $state('');
	let cantidad = $state(1);
	let telefono = $state('');
	let mensaje = $state('');
	let accionError = $state({});
	let solicitud = $state(null);
	let errorSolicitud = $state('');
	let votando = $state(false);
	let indiceImagen = $state(0);
	let copiaFallida = $state(false);
	let enlaceCopia = $state('');
	let campoEnlace = $state();
	let historial = $state([]);
	let hayMasHistorial = $state(false);
	let errorHistorial = $state('');
	let paginaHistorial = $state(1);
	let cargandoHistorial = $state(true);
	const aviso = $derived(page.url.searchParams.get('aviso'));

	const MENSAJES_ESTADO = {
		confirmar: 'Pedido confirmado.',
		finalizar: 'Pool finalizado.',
		cancelar: 'Pool cancelado.'
	};

	const PASOS_ESTADO = ['abierto', 'listo', 'en_curso', 'finalizado'];

	const CONFIRMACION_SOLICITUD =
		'Al solicitar la eliminación, el pool se borrará únicamente si todos los integrantes aceptan. ¿Querés solicitar la eliminación?';

	$effect(() => {
		cargar(page.params.id);
	});

	// Prellena el teléfono desde el perfil del usuario logueado (una sola vez).
	$effect(() => {
		if (session.user && !telefono) telefono = session.user.telefono ?? '';
	});

	async function cargar(id) {
		cargando = true;
		error = '';
		try {
			pool = await api(`/pools/${id}/`);
			const mia = pool.miembros.find((m) => m.usuario.id === session.user?.id);
			cantidad = mia ? mia.cantidad : pool.min_por_integrante;
			indiceImagen = 0;
		} catch (e) {
			if (e.status === 404) {
				notificar('Este pool ya no existe.', 'aviso');
				goto(resolve('/pools'));
				return;
			}
			error = 'No se pudo cargar el pool.';
		} finally {
			cargando = false;
		}
	}

	const esCreador = $derived(session.user?.id === pool?.creador?.id);
	const miMembresia = $derived(
		pool?.miembros?.find((m) => m.usuario.id === session.user?.id) ?? null
	);
	const puedeReservar = $derived(puedeUnirse(pool, session.user?.id));

	const esParticipante = $derived(esIntegrante(pool, session.user?.id));
	const idPool = $derived(pool?.id ?? null);
	const enEliminacion = $derived(pool?.estado === 'listo' || pool?.estado === 'en_curso');
	const claveSolicitud = $derived(
		esParticipante && enEliminacion && idPool !== null ? `${idPool}:${pool.estado}` : null
	);
	const claveHistorial = $derived(esParticipante && idPool !== null ? idPool : null);
	const solicitudPendiente = $derived(solicitud?.estado === 'pendiente');
	const panelSolicitud = $derived(solicitudPendiente || solicitud?.estado === 'rechazada');
	const puedeSolicitar = $derived(puedeSolicitarEliminacion(pool, session.user?.id, solicitud));

	$effect(() => {
		if (!claveSolicitud) {
			solicitud = null;
			errorSolicitud = '';
			return;
		}
		cargarSolicitud(idPool);
	});

	$effect(() => {
		if (claveHistorial === null) {
			historial = [];
			errorHistorial = '';
			hayMasHistorial = false;
			paginaHistorial = 1;
			return;
		}
		cargarHistorial(claveHistorial);
	});

	async function cargarHistorial(id) {
		errorHistorial = '';
		cargandoHistorial = true;
		try {
			const datos = await api(`/pools/${id}/historial/`);
			historial = datos.results;
			hayMasHistorial = Boolean(datos.next);
			paginaHistorial = 1;
		} catch (e) {
			historial = [];
			hayMasHistorial = false;
			errorHistorial = mensajeError(e);
		} finally {
			cargandoHistorial = false;
		}
	}

	async function verMasHistorial() {
		if (!pool) return;
		try {
			const datos = await api(`/pools/${pool.id}/historial/`, {
				query: { page: paginaHistorial + 1 }
			});
			historial = [...historial, ...datos.results];
			hayMasHistorial = Boolean(datos.next);
			paginaHistorial += 1;
		} catch (e) {
			errorHistorial = mensajeError(e);
		}
	}

	const tono = $derived(tonoCategoria(pool?.categoria));
	const imagenActiva = $derived(pool?.imagenes?.[indiceImagen] ?? pool?.imagenes?.[0] ?? null);
	const comprometido = $derived(pool ? pool.cantidad_total - pool.disponible : 0);
	const indiceEstado = $derived(PASOS_ESTADO.indexOf(pool?.estado ?? ''));

	const vence = $derived(pool ? diasHasta(pool.fecha_caducidad) : null);
	const venceTono = $derived(vence !== null && vence <= 2 ? 'coral' : vence !== null && vence <= 6 ? 'ambar' : 'verde');
	const venceTexto = $derived(
		vence === null
			? ''
			: vence < 0
				? 'Vencido'
				: vence === 0
					? 'Vence hoy'
					: `Vence en ${vence} ${vence === 1 ? 'día' : 'días'}`
	);

	async function unirse() {
		accionError = {};
		try {
			await api(`/pools/${pool.id}/unirse/`, {
				method: 'POST',
				body: payloadUnion(cantidad, telefono, mensaje)
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
			await cargarHistorial(pool.id);
			notificar('Cantidad actualizada.');
		} catch (e) {
			accionError = fieldErrors(e.data);
		}
	}

	async function cambiarEstado(accion) {
		accionError = {};
		try {
			pool = await api(`/pools/${pool.id}/${accion}/`, { method: 'POST' });
			await cargarHistorial(pool.id);
			notificar(MENSAJES_ESTADO[accion] ?? 'Estado actualizado.');
		} catch (e) {
			accionError = fieldErrors(e.data);
		}
	}

	async function cargarSolicitud(id) {
		errorSolicitud = '';
		try {
			solicitud = await api(`/pools/${id}/eliminacion/`);
		} catch (e) {
			solicitud = null;
			if (e.status !== 404 && e.status !== 403) errorSolicitud = mensajeError(e);
		}
	}

	function errorDeAccion(e) {
		const errores = fieldErrors(e.data);
		return Object.keys(errores).length ? errores : { detail: mensajeError(e) };
	}

	async function solicitarEliminacion() {
		if (!puedeSolicitarEliminacion(pool, session.user?.id, solicitud)) return;
		accionError = {};
		try {
			const { confirmada, resultado } = await conConfirmacion(CONFIRMACION_SOLICITUD, confirm, () =>
				api(`/pools/${pool.id}/eliminacion/`, { method: 'POST' })
			);
			if (!confirmada) return;
			await resolverEliminacion(resultado, 'Solicitud enviada. Falta que voten los integrantes.');
		} catch (e) {
			accionError = errorDeAccion(e);
		}
	}

	async function votar(acepta) {
		if (!puedeVotarEliminacion(pool, solicitud, session.user?.id)) return;
		votando = true;
		accionError = {};
		try {
			const resultado = await api(`/pools/${pool.id}/eliminacion/voto/`, {
				method: 'POST',
				body: { acepta }
			});
			await resolverEliminacion(resultado, 'Voto registrado. Falta que vote el resto.');
		} catch (e) {
			accionError = errorDeAccion(e);
		} finally {
			votando = false;
		}
	}

	async function resolverEliminacion(resultado, mensajeSeguir) {
		switch (desenlaceEliminacion(resultado?.estado)) {
			case 'borrado':
				notificar('El pool fue eliminado.');
				goto(resolve('/pools'));
				break;
			case 'rechazada':
				notificar('La eliminación fue rechazada. El pool sigue en pie.', 'aviso');
				await cargarSolicitud(pool.id);
				await cargarHistorial(pool.id);
				break;
			default:
				notificar(mensajeSeguir, 'info');
				await cargarSolicitud(pool.id);
				await cargarHistorial(pool.id);
		}
	}

	async function eliminar() {
		accionError = {};
		try {
			const { confirmada } = await conConfirmacion(
				'¿Eliminar este pool? Esta acción no se puede deshacer.',
				confirm,
				() => api(`/pools/${pool.id}/`, { method: 'DELETE' })
			);
			if (!confirmada) return;
			notificar('Pool eliminado.');
			goto(resolve(rutaTab('mios')));
		} catch (e) {
			accionError = errorDeAccion(e);
		}
	}

	async function copiarEnlace() {
		copiaFallida = false;
		try {
			await navigator.clipboard.writeText(location.href);
			notificar('Enlace copiado.');
		} catch {
			enlaceCopia = location.href;
			copiaFallida = true;
			await tick();
			campoEnlace?.select();
			notificar('No se pudo copiar automáticamente. El enlace quedó seleccionado.', 'error');
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

	<div class="detalle tono-{tono} animar">
		<div class="principal">
			<header class="encabezado">
				<div class="encabezado__chips">
					<span class="badge badge--{pool.estado}">{etiquetaEstado(pool.estado)}</span>
					<span class="chip chip--color tono-{tono}">{pool.categoria_nombre}</span>
				</div>
				<h1>{pool.titulo}</h1>
				<p class="encabezado__producto">{pool.nombre_producto}</p>
				<p class="encabezado__meta">
					<span>{pool.ciudad}</span>
					<span>{vistas(pool.vistas)}</span>
					<span>Caduca el {fecha(pool.fecha_caducidad)}</span>
				</p>
				<p class="precio">
					<span class="precio__valor">{moneda(pool.precio_unitario)}</span>
					<span class="precio__unidad">por unidad</span>
				</p>
			</header>

			{#if aviso === 'imagenes'}
				<div class="alerta alerta--aviso aviso" role="alert">
					El pool se creó, pero algunas imágenes no se pudieron subir.
				</div>
			{/if}

			<div class="galeria">
				{#if pool.imagenes.length}
					<div class="galeria__marco">
						<img
							class="galeria__activa"
							src={imagenActiva.imagen}
							alt={pool.titulo}
							width="800"
							height="600"
						/>
					</div>
					{#if pool.imagenes.length > 1}
						<div class="galeria__tiras" role="group" aria-label="Miniaturas de imágenes">
							{#each pool.imagenes as imagen, i (imagen.id)}
								<button
									class="miniatura"
									class:activa={i === indiceImagen}
									type="button"
									aria-pressed={i === indiceImagen}
									aria-label={`Ver imagen ${i + 1} de ${pool.imagenes.length}`}
									onclick={() => (indiceImagen = i)}
								>
									<img src={imagen.imagen} alt="" width="120" height="90" loading="lazy" />
								</button>
							{/each}
						</div>
					{/if}
				{:else}
					<div class="galeria__vacia">
						<svg
							width="36"
							height="36"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.5"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<rect x="3" y="3" width="18" height="18" rx="2" />
							<circle cx="9" cy="9" r="2" />
							<path d="m21 15-4.5-4.5L7 20" />
						</svg>
						<p>Este pool todavía no tiene imágenes</p>
					</div>
				{/if}
			</div>

			<section class="bloque">
				<h2>Progreso de la compra</h2>
				<div class="progreso-bloque">
					<div class="progreso-bloque__fila">
						<span>Comprometido</span>
						<strong>{comprometido} de {pool.cantidad_total} unidades</strong>
					</div>
					<progress
						class="progreso progreso--color"
						value={comprometido}
						max={pool.cantidad_total}
						aria-label="Unidades comprometidas"
					></progress>
				</div>
			</section>

			<section class="bloque">
				<h2>Estado de la compra</h2>
				<ol class="linea">
					{#each PASOS_ESTADO as paso, i (paso)}
						<li
							class="linea__paso"
							class:completado={indiceEstado > i}
							class:activo={indiceEstado === i}
							aria-current={indiceEstado === i ? 'step' : undefined}
						>
							<span class="linea__punto"></span>
							<span class="linea__nombre">{etiquetaEstado(paso)}</span>
						</li>
					{/each}
				</ol>
				{#if pool.estado === 'cancelado'}
					<p class="linea__cancelado">Este pool fue cancelado.</p>
				{/if}
			</section>

			<section class="bloque">
				<h2>Datos clave</h2>
				<div class="tiles">
					<div class="tile tono-azul">
						<span class="tile__icono" aria-hidden="true">
							<svg
								width="20"
								height="20"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.75"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<path d="M20.59 13.41 13.42 20.58a2 2 0 0 1-2.83 0L2 12V4a2 2 0 0 1 2-2h8l8.59 8.59a2 2 0 0 1 0 2.82Z" />
								<circle cx="7.5" cy="7.5" r="1.5" />
							</svg>
						</span>
						<span class="tile__etiqueta">Precio unitario</span>
						<span class="tile__valor">{moneda(pool.precio_unitario)}</span>
					</div>

					<div class="tile tono-violeta">
						<span class="tile__icono" aria-hidden="true">
							<svg
								width="20"
								height="20"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.75"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<circle cx="12" cy="8" r="3.5" />
								<path d="M5 20a7 7 0 0 1 14 0" />
							</svg>
						</span>
						<span class="tile__etiqueta">Mínimo por integrante</span>
						<span class="tile__valor">{pool.min_por_integrante} u.</span>
					</div>

					<div class="tile tono-{venceTono}">
						<span class="tile__icono" aria-hidden="true">
							<svg
								width="20"
								height="20"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.75"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<rect x="3" y="5" width="18" height="16" rx="2" />
								<path d="M8 3v4M16 3v4M3 10h18" />
							</svg>
						</span>
						<span class="tile__etiqueta">Vence</span>
						<span class="tile__valor">{fecha(pool.fecha_caducidad)}</span>
						<span class="chip chip--color tono-{venceTono} tile__chip">{venceTexto}</span>
					</div>

					<div class="tile tono-teal">
						<span class="tile__icono" aria-hidden="true">
							<svg
								width="20"
								height="20"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.75"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<rect x="2" y="5" width="20" height="14" rx="2" />
								<path d="M2 10h20" />
							</svg>
						</span>
						<span class="tile__etiqueta">Tipo de pago</span>
						<span class="tile__valor">{etiquetaPago(pool.tipo_pago)}</span>
					</div>
				</div>
			</section>

			{#if pool.descripcion}
				<section class="bloque">
					<h2>Descripción</h2>
					<p class="prosa">{pool.descripcion}</p>
				</section>
			{/if}

			<section class="bloque">
				<h2>Detalles</h2>
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
						<dt>Cantidad total</dt>
						<dd>{pool.cantidad_total}</dd>
					</div>
					<div class="ficha__item">
						<dt>Del creador</dt>
						<dd>{pool.cantidad_creador}</dd>
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

			{#if mostrarAnalisis(pool)}
				<PanelEnlace analisis={pool.analisis_enlace} />
			{/if}

			<section class="bloque">
				<h2>Ubicación</h2>
				{#if coordsValidas(pool.latitud, pool.longitud)}
					<MapaPool lat={pool.latitud} lng={pool.longitud} titulo={pool.titulo} />
					<p class="ayuda ubicacion__referencia">{pool.direccion}, {pool.ciudad}</p>
				{:else}
					<div class="ubicacion__vacia">
						<svg
							width="36"
							height="36"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.5"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z" />
							<circle cx="12" cy="10" r="3" />
						</svg>
						<p>Sin ubicación</p>
						<p class="ayuda">Todavía no hay coordenadas para este pool.</p>
					</div>
				{/if}
			</section>

			<section class="bloque">
				<h2>Quiénes participan</h2>

				<div class="creador tono-{tonoNombre(pool.creador.username)}">
					<span class="avatar avatar--lg" aria-hidden="true">
						{#if pool.creador.foto}
							<img src={pool.creador.foto} alt="" width="72" height="72" loading="lazy" />
						{:else}
							{iniciales(pool.creador.username)}
						{/if}
					</span>
					<div>
						<p class="creador__etiqueta">Creador del pool</p>
						<p class="creador__nombre">{pool.creador.username}</p>
						<p class="creador__cantidad">{pool.cantidad_creador} u. reservadas</p>
					</div>
				</div>

				{#if pool.miembros.length}
					<ul class="miembros">
						{#each pool.miembros as miembro (miembro.id)}
							<li class="miembro tono-{tonoNombre(miembro.usuario.username)}">
								<div class="miembro__fila">
									<span class="avatar avatar--sm" aria-hidden="true">
										{#if miembro.usuario.foto}
											<img src={miembro.usuario.foto} alt="" width="28" height="28" loading="lazy" />
										{:else}
											{iniciales(miembro.usuario.username)}
										{/if}
									</span>
									<span class="miembro__nombre">{miembro.usuario.username}</span>
									<span class="chip chip--color miembro__cantidad">{miembro.cantidad} u.</span>
								</div>
								{#if esCreador}
									{#if miembro.telefono}
										<p class="miembro__dato">Teléfono: {miembro.telefono}</p>
									{/if}
									{#if miembro.mensaje}
										<p class="miembro__dato">{miembro.mensaje}</p>
									{/if}
									<MiniPerfil usuarioId={miembro.usuario.id} />
								{/if}
							</li>
						{/each}
					</ul>
				{:else}
					<p class="muted">Nadie más se unió todavía.</p>
				{/if}
			</section>

			{#if esParticipante}
				<section class="bloque">
					<h2>Historial del pool</h2>
					{#if errorHistorial}
						<p class="error" role="alert">{errorHistorial}</p>
					{/if}
					{#if cargandoHistorial && !historial.length}
						<p class="muted">Cargando el historial…</p>
					{:else if historial.length}
						<ol class="historial">
							{#each historial as evento}
								<li class="historial__item">
									<span
										class="historial__punto tono-{tonoNombre(evento.actor?.username ?? 'sistema')}"
										aria-hidden="true"
									></span>
									<div class="historial__cuerpo">
										<p class="historial__texto">{textoEvento(evento)}</p>
										<p class="historial__fecha">{fechaHora(evento.creado)}</p>
									</div>
								</li>
							{/each}
						</ol>
						{#if hayMasHistorial}
							<button
								class="btn btn--secundario btn--sm historial__mas"
								type="button"
								onclick={verMasHistorial}
							>
								Ver más
							</button>
						{/if}
					{:else}
						<p class="muted">Todavía no hay movimientos en este pool.</p>
					{/if}
				</section>
			{/if}
		</div>

		<aside class="lateral panel">
			<div class="lateral__banda">
				<span class="badge badge--{pool.estado}">{etiquetaEstado(pool.estado)}</span>
				{#if pool.estado !== 'finalizado' && pool.estado !== 'cancelado'}
					<span class="chip chip--color tono-{venceTono}">{venceTexto}</span>
				{/if}
			</div>
			<p class="lateral__eyebrow">Disponible</p>
			<p class="lateral__disponible">
				{pool.disponible}<span>de {pool.cantidad_total} unidades</span>
			</p>

			<p class="lateral__caduca">Caduca el {fecha(pool.fecha_caducidad)}</p>

			<div class="lateral__acciones">
				{#if errorSolicitud}
					<p class="error" role="alert">{errorSolicitud}</p>
				{/if}
				{#if !session.access && pool.estado === 'abierto' && pool.disponible >= pool.min_por_integrante}
					<p class="muted">Ingresá para unirte a este pool.</p>
					<a class="btn btn--primario btn--bloque" href={resolve('/login')}>Ingresar</a>
				{:else if esCreador}
					{#if panelSolicitud}
						<PanelEliminacion
							{pool}
							{solicitud}
							usuarioId={session.user?.id}
							ocupado={votando}
							onvotar={votar}
						/>
					{/if}
					{#if pool.estado === 'abierto'}
						<a class="btn btn--secundario btn--bloque" href={resolve(`/pools/${pool.id}/editar`)}>
							Editar pool
						</a>
					{/if}
					{#if puedeEliminarDirecto(pool, session.user?.id)}
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
					{#if puedeSolicitar}
						<button
							class="btn btn--peligro-suave btn--bloque"
							type="button"
							onclick={solicitarEliminacion}
						>
							Solicitar eliminación
						</button>
					{/if}
				{:else if miMembresia}
					{#if panelSolicitud}
						<PanelEliminacion
							{pool}
							{solicitud}
							usuarioId={session.user?.id}
							ocupado={votando}
							onvotar={votar}
						/>
					{/if}
					{#if !solicitudPendiente && (pool.estado === 'abierto' || pool.estado === 'listo')}
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
								aria-invalid={accionError.cantidad ? 'true' : undefined}
								aria-describedby={accionError.cantidad
									? 'cantidad-ayuda cantidad-error'
									: 'cantidad-ayuda'}
							/>
							<p class="ayuda" id="cantidad-ayuda">
								Mínimo {pool.min_por_integrante} · Podés reservar hasta {pool.disponible +
									miMembresia.cantidad}.
							</p>
							{#if accionError.cantidad}
								<p class="error" id="cantidad-error" role="alert">{accionError.cantidad}</p>
							{/if}
						</div>
						<button class="btn btn--primario btn--bloque" type="button" onclick={guardarCantidad}>
							Guardar cantidad
						</button>
						<button class="btn btn--peligro-suave btn--bloque" type="button" onclick={salir}>
							Salir del pool
						</button>
					{/if}
				{:else if puedeReservar}
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
							aria-invalid={accionError.cantidad ? 'true' : undefined}
							aria-describedby={accionError.cantidad
								? 'cantidad-ayuda cantidad-error'
								: 'cantidad-ayuda'}
						/>
						<p class="ayuda" id="cantidad-ayuda">
							Mínimo {pool.min_por_integrante} · Podés reservar hasta {pool.disponible}.
						</p>
						{#if accionError.cantidad}
							<p class="error" id="cantidad-error" role="alert">{accionError.cantidad}</p>
						{/if}
					</div>
					<div class="campo">
						<label for="telefono">Tu teléfono</label>
						<input
							id="telefono"
							name="telefono"
							type="tel"
							inputmode="tel"
							bind:value={telefono}
							aria-invalid={accionError.telefono ? 'true' : undefined}
							aria-describedby={accionError.telefono ? 'telefono-error' : undefined}
						/>
						{#if accionError.telefono}
							<p class="error" id="telefono-error" role="alert">{accionError.telefono}</p>
						{/if}
					</div>
					<div class="campo">
						<label for="mensaje">Mensaje para el creador (opcional)</label>
						<textarea
							id="mensaje"
							name="mensaje"
							maxlength="500"
							rows="2"
							bind:value={mensaje}
							aria-invalid={accionError.mensaje ? 'true' : undefined}
							aria-describedby={accionError.mensaje ? 'mensaje-error' : undefined}
						></textarea>
						{#if accionError.mensaje}
							<p class="error" id="mensaje-error" role="alert">{accionError.mensaje}</p>
						{/if}
					</div>
					<button class="btn btn--primario btn--bloque" type="button" onclick={unirse}>
						Unirme al pool
					</button>
				{:else if pool.estado !== 'abierto'}
					<p class="muted">Este pool ya no acepta nuevas reservas.</p>
				{/if}

				{#if accionError.detail || accionError.non_field_errors}
					<p class="error" role="alert">{accionError.detail || accionError.non_field_errors}</p>
				{/if}
				{#if accionError.estado}
					<p class="error" role="alert">{accionError.estado}</p>
				{/if}
			</div>

			<button class="btn btn--secundario btn--bloque lateral__copiar" type="button" onclick={copiarEnlace}>
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.75"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<rect x="9" y="9" width="12" height="12" rx="2" />
					<path d="M5 15V5a2 2 0 0 1 2-2h10" />
				</svg>
				Copiar enlace
			</button>

			{#if copiaFallida}
				<div class="campo lateral__copia">
					<label for="enlace-copia">Enlace del pool</label>
					<input
						id="enlace-copia"
						type="text"
						readonly
						value={enlaceCopia}
						bind:this={campoEnlace}
					/>
					<p class="ayuda">Copialo con Ctrl+C (o Cmd+C).</p>
				</div>
			{/if}

			<div class="lateral__meta">
				<p>Organiza <strong>{pool.creador.username}</strong></p>
				<p>{vistas(pool.vistas)}</p>
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

	.principal {
		min-width: 0;
	}

	.encabezado__chips {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2);
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

	.encabezado__meta {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-1) var(--e-4);
		margin-top: var(--e-3);
		font-size: var(--texto-sm);
		color: var(--tinta-tenue);
	}

	.precio {
		display: flex;
		align-items: baseline;
		gap: var(--e-2);
		margin-top: var(--e-4);
	}

	.precio__valor {
		font-family: var(--fuente-display);
		font-size: var(--texto-2xl);
		font-weight: 600;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
	}

	.precio__unidad {
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.aviso {
		margin-top: var(--e-5);
	}

	.galeria {
		margin-top: var(--e-6);
	}

	.galeria__marco {
		overflow: hidden;
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--t-t);
	}

	.galeria__activa {
		width: 100%;
		aspect-ratio: 16 / 9;
		object-fit: cover;
	}

	.galeria__tiras {
		display: flex;
		gap: var(--e-2);
		margin-top: var(--e-3);
		padding: 4px;
		overflow-x: auto;
	}

	.miniatura {
		flex: none;
		width: 5rem;
		height: 3.75rem;
		padding: 0;
		border: 2px solid transparent;
		border-radius: var(--radio-sm);
		background: var(--superficie-alt);
		overflow: hidden;
		opacity: 0.65;
		cursor: pointer;
		transition:
			opacity var(--transicion),
			border-color var(--transicion);
	}

	.miniatura img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.miniatura:hover {
		opacity: 1;
	}

	.miniatura.activa {
		border-color: var(--c-t);
		opacity: 1;
	}

	.miniatura:focus-visible {
		outline: 2px solid var(--acento);
		outline-offset: 2px;
	}

	.galeria__vacia {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--e-2);
		aspect-ratio: 16 / 9;
		border: 1px dashed var(--c-t);
		border-radius: var(--radio);
		background: var(--t-t);
		color: var(--c-t);
	}

	.galeria__vacia p {
		margin: 0;
		font-size: var(--texto-sm);
		font-weight: 500;
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

	.progreso-bloque {
		padding: var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--superficie);
	}

	.progreso-bloque__fila {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: var(--e-3);
		margin-bottom: var(--e-3);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.progreso-bloque__fila strong {
		color: var(--tinta);
	}

	.linea {
		position: relative;
		display: flex;
		justify-content: space-between;
		gap: var(--e-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.linea::before {
		content: '';
		position: absolute;
		left: 1.1rem;
		right: 1.1rem;
		top: 0.5rem;
		height: 2px;
		background: var(--linea);
	}

	.linea__paso {
		position: relative;
		z-index: 1;
		display: flex;
		flex: 1;
		flex-direction: column;
		align-items: center;
		gap: var(--e-2);
		min-width: 0;
		text-align: center;
	}

	.linea__punto {
		width: 1rem;
		height: 1rem;
		border: 2px solid var(--linea-fuerte);
		border-radius: 50%;
		background: var(--superficie);
	}

	.linea__paso.completado .linea__punto {
		background: var(--c-verde);
		border-color: var(--c-verde);
	}

	.linea__paso.activo .linea__punto {
		background: var(--c-t);
		border-color: var(--c-t);
		box-shadow: 0 0 0 4px var(--t-t);
	}

	.linea__nombre {
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.linea__paso.activo .linea__nombre {
		color: var(--tinta);
		font-weight: 600;
	}

	.linea__paso.completado .linea__nombre {
		color: var(--tinta-suave);
	}

	.linea__cancelado {
		margin-top: var(--e-4);
		padding: var(--e-3);
		border-radius: var(--radio-sm);
		background: var(--peligro-suave);
		color: var(--peligro);
		font-size: var(--texto-sm);
		font-weight: 500;
	}

	.tiles {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--e-3);
	}

	.tile {
		display: flex;
		flex-direction: column;
		gap: var(--e-1);
		padding: var(--e-4);
		border: 1px solid var(--t-t);
		border-radius: var(--radio);
		background: var(--t-t);
	}

	.tile__icono {
		display: inline-flex;
		color: var(--c-t);
	}

	.tile__etiqueta {
		font-size: var(--texto-xs);
		font-weight: 600;
		color: var(--c-t);
	}

	.tile__valor {
		font-size: var(--texto-md);
		font-weight: 600;
		color: var(--tinta);
		overflow-wrap: anywhere;
		font-variant-numeric: tabular-nums;
	}

	.tile__chip {
		align-self: flex-start;
		margin-top: var(--e-1);
		background: var(--superficie);
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

	.ubicacion__referencia {
		margin-top: var(--e-3);
	}

	.ubicacion__vacia {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--e-2);
		padding: var(--e-6) var(--e-4);
		border: 1px dashed var(--c-t);
		border-radius: var(--radio);
		background: var(--t-t);
		color: var(--c-t);
		text-align: center;
	}

	.ubicacion__vacia p {
		margin: 0;
		font-size: var(--texto-sm);
		font-weight: 500;
	}

	.ubicacion__vacia .ayuda {
		color: var(--tinta-suave);
		font-weight: 400;
	}

	.creador {
		display: flex;
		align-items: center;
		gap: var(--e-4);
		padding: var(--e-4);
		border: 1px solid var(--t-t);
		border-radius: var(--radio);
		background: var(--t-t);
	}

	.creador__etiqueta {
		margin: 0;
		font-size: var(--texto-xs);
		font-weight: 600;
		color: var(--c-t);
	}

	.creador__nombre {
		margin: var(--e-1) 0 0;
		font-size: var(--texto-md);
		font-weight: 600;
		color: var(--tinta);
		overflow-wrap: anywhere;
	}

	.creador__cantidad {
		margin: var(--e-1) 0 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.miembros {
		display: flex;
		flex-direction: column;
		gap: var(--e-3);
		margin: var(--e-4) 0 0;
		padding: 0;
		list-style: none;
	}

	.miembro {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		padding: var(--e-3) var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
		background: var(--superficie);
	}

	.miembro__fila {
		display: flex;
		align-items: center;
		gap: var(--e-3);
	}

	.miembro__nombre {
		font-size: var(--texto-sm);
		font-weight: 500;
		min-width: 0;
		overflow-wrap: anywhere;
	}

	.miembro__cantidad {
		margin-left: auto;
	}

	.miembro__dato {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
		overflow-wrap: anywhere;
	}

	.historial {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.historial__item {
		display: flex;
		align-items: flex-start;
		gap: var(--e-3);
	}

	.historial__punto {
		flex: none;
		width: 0.6rem;
		height: 0.6rem;
		margin-top: 0.4rem;
		border-radius: 50%;
		background: var(--c-t);
	}

	.historial__cuerpo {
		min-width: 0;
	}

	.historial__texto {
		margin: 0;
		font-size: var(--texto-sm);
		overflow-wrap: anywhere;
	}

	.historial__fecha {
		margin: var(--e-1) 0 0;
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.historial__mas {
		margin-top: var(--e-4);
	}

	.lateral {
		position: sticky;
		top: calc(var(--alto-cabecera) + var(--e-5));
		padding: var(--e-6);
	}

	.lateral__banda {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2);
		margin: calc(-1 * var(--e-6)) calc(-1 * var(--e-6)) var(--e-5);
		padding: var(--e-4) var(--e-6);
		border-radius: var(--radio) var(--radio) 0 0;
		background: var(--t-t);
	}

	.lateral__eyebrow {
		margin: 0;
		font-size: var(--texto-xs);
		font-weight: 600;
		color: var(--tinta-tenue);
	}

	.lateral__disponible {
		display: flex;
		align-items: baseline;
		gap: var(--e-2);
		margin: var(--e-1) 0 0;
		font-family: var(--fuente-display);
		font-size: var(--texto-2xl);
		font-weight: 600;
		letter-spacing: -0.02em;
		color: var(--tinta);
		font-variant-numeric: tabular-nums;
	}

	.lateral__disponible span {
		font-family: var(--fuente-texto);
		font-size: var(--texto-sm);
		font-weight: 400;
		color: var(--tinta-suave);
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

	.lateral__copiar {
		margin-top: var(--e-3);
	}

	.lateral__copia {
		margin: var(--e-3) 0 0;
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
		.ficha {
			grid-template-columns: 1fr;
		}

		.tiles {
			grid-template-columns: 1fr;
		}

		.linea__paso {
			gap: var(--e-1);
		}

		.linea__nombre {
			font-size: 0.68rem;
		}
	}
</style>
