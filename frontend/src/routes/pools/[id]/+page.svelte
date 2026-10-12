<script>
	import { tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, fieldErrors } from '$lib/api.js';
	import { estadoChat } from '$lib/chat.js';
	import { mostrarAnalisis } from '$lib/confianza.js';
	import {
		conConfirmacion,
		desenlaceEliminacion,
		mensajeError,
		puedeEliminarDirecto,
		puedeSolicitarEliminacion,
		puedeVotarEliminacion
	} from '$lib/eliminacion.js';
	import { etiquetaEstado, etiquetaPago, puedeUnirse, tonoNombre } from '$lib/estados.js';
	import { diasHasta, fecha, moneda, vistas } from '$lib/formato.js';
	import { esIntegrante, fechaHora, textoEvento } from '$lib/historial.js';
	import MapaPool from '$lib/MapaPool.svelte';
	import MiniPerfil from '$lib/MiniPerfil.svelte';
	import PanelChat from '$lib/PanelChat.svelte';
	import PanelEliminacion from '$lib/PanelEliminacion.svelte';
	import PanelEnlace from '$lib/PanelEnlace.svelte';
	import { rutaTab } from '$lib/pestanas.js';
	import { session } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';
	import { coordsValidas } from '$lib/ubicacion.js';
	import { payloadUnion } from '$lib/union.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Avatar from '$lib/ui/Avatar.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

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
	const modoChat = $derived(estadoChat(pool, session.user?.id));
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

	// Estimación de la reserva para el resumen del panel de unión (presentación).
	const totalReserva = $derived(pool ? Number(cantidad || 0) * Number(pool.precio_unitario || 0) : 0);

	/** "1 unidad" / "N unidades". */
	const unidades = (n) => `${n} ${n === 1 ? 'unidad' : 'unidades'}`;

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
		<Boton variante="secundario" href={resolve('/pools')}>Volver a pools</Boton>
	</div>
{:else}
	<a class="volver" href={resolve('/pools')}>← Volver a pools</a>

	<div class="detalle animar">
		<div class="principal">
			{#if aviso === 'imagenes'}
				<div class="detalle__aviso">
					<Aviso variante="aviso">
						El pool se creó, pero algunas imágenes no se pudieron subir.
					</Aviso>
				</div>
			{/if}

			<section class="encabezado">
				<div class="encabezado__media">
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

				<div class="encabezado__datos">
					<div class="encabezado__pills">
						<Badge variante={pool.estado}>{etiquetaEstado(pool.estado)}</Badge>
						<Badge variante="neutro">{pool.categoria_nombre}</Badge>
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
						{#if pool.precio_original}
							<s class="precio__antes">{moneda(pool.precio_original)}</s>
						{/if}
					</p>

					<div class="progreso-bloque">
						<progress
							class="progreso progreso--color"
							value={comprometido}
							max={pool.cantidad_total}
							aria-label="Unidades comprometidas"
						></progress>
						<div class="progreso__filas">
							<span><b>{comprometido} de {unidades(pool.cantidad_total)}</b></span>
							{#if pool.disponible > 0}
								<span>Faltan <b class="progreso__restante">{pool.disponible}</b></span>
							{:else}
								<span><b class="progreso__restante">Completo</b></span>
							{/if}
						</div>
						{#if pool.estado !== 'finalizado' && pool.estado !== 'cancelado'}
							<p class="progreso__tiempo">
								<svg
									width="18"
									height="18"
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
								{venceTexto} · caduca el {fecha(pool.fecha_caducidad)}
							</p>
						{/if}
					</div>
				</div>
			</section>

			<ul class="facts">
				<li class="fact">
					<svg
						width="22"
						height="22"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.8"
						stroke-linecap="round"
						stroke-linejoin="round"
						aria-hidden="true"
					>
						<path d="M6 7h12l-1 14H7z" />
						<path d="M9 7V4h6v3" />
					</svg>
					<span><b>{unidades(pool.min_por_integrante)}</b><br />por persona</span>
				</li>
				<li class="fact">
					<svg
						width="22"
						height="22"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.8"
						stroke-linecap="round"
						stroke-linejoin="round"
						aria-hidden="true"
					>
						<rect x="2" y="5" width="20" height="14" rx="2" />
						<path d="M2 10h20" />
					</svg>
					<span><b>{etiquetaPago(pool.tipo_pago)}</b><br />forma de pago</span>
				</li>
				<li class="fact">
					<svg
						width="22"
						height="22"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.8"
						stroke-linecap="round"
						stroke-linejoin="round"
						aria-hidden="true"
					>
						<rect x="3" y="5" width="18" height="16" rx="2" />
						<path d="M8 3v4M16 3v4M3 10h18" />
					</svg>
					<span
						><b class="vence vence--{venceTono}">{venceTexto}</b><br />caduca el {fecha(
							pool.fecha_caducidad
						)}</span
					>
				</li>
			</ul>

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

			{#if pool.descripcion}
				<section class="bloque">
					<h2>Descripción</h2>
					<p class="prosa">{pool.descripcion}</p>
				</section>
			{/if}

			<section class="bloque">
				<Tarjeta>
					<div class="detalles">
						<h2>Detalles del producto</h2>
						<ul class="detalles__lista">
							<li class="detalles__fila">
								<span class="detalles__icono" aria-hidden="true">
									<svg
										width="20"
										height="20"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.8"
										stroke-linecap="round"
										stroke-linejoin="round"
									>
										<path d="M3 8l9-5 9 5v8l-9 5-9-5z" />
										<path d="M3 8l9 5 9-5" />
									</svg>
								</span>
								Producto: <b>{pool.nombre_producto}</b>
							</li>
							<li class="detalles__fila">
								<span class="detalles__icono" aria-hidden="true">
									<svg
										width="20"
										height="20"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.8"
										stroke-linecap="round"
										stroke-linejoin="round"
									>
										<path d="M20.59 13.41 13.42 20.58a2 2 0 0 1-2.83 0L2 12V4a2 2 0 0 1 2-2h8l8.59 8.59a2 2 0 0 1 0 2.82Z" />
										<circle cx="7.5" cy="7.5" r="1.5" />
									</svg>
								</span>
								Categoría: <b>{pool.categoria_nombre}</b>
							</li>
							<li class="detalles__fila">
								<span class="detalles__icono" aria-hidden="true">
									<svg
										width="20"
										height="20"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.8"
										stroke-linecap="round"
										stroke-linejoin="round"
									>
										<circle cx="12" cy="12" r="9" />
										<path d="M12 7v5l3 2" />
									</svg>
								</span>
								Cantidad total: <b>{unidades(pool.cantidad_total)}</b>
							</li>
							<li class="detalles__fila">
								<span class="detalles__icono" aria-hidden="true">
									<svg
										width="20"
										height="20"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.8"
										stroke-linecap="round"
										stroke-linejoin="round"
									>
										<circle cx="12" cy="8" r="3.5" />
										<path d="M5 20a7 7 0 0 1 14 0" />
									</svg>
								</span>
								Del creador: <b>{unidades(pool.cantidad_creador)}</b>
							</li>
							<li class="detalles__fila">
								<span class="detalles__icono" aria-hidden="true">
									<svg
										width="20"
										height="20"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.8"
										stroke-linecap="round"
										aria-hidden="true"
									>
										<circle cx="12" cy="12" r="9" />
										<path d="M14.5 9a2.5 2.5 0 0 0-5 0c0 3 5 1.5 5 4.5a2.5 2.5 0 0 1-5 0M12 6v1.5M12 16.5V18" />
									</svg>
								</span>
								Precio por unidad: <b>{moneda(pool.precio_unitario)}</b>
							</li>
							{#if pool.precio_original}
								<li class="detalles__fila">
									<span class="detalles__icono" aria-hidden="true">
										<svg
											width="20"
											height="20"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.8"
											stroke-linecap="round"
											stroke-linejoin="round"
										>
											<path d="M3 12V4h8l10 10-8 8z" />
											<circle cx="7.5" cy="8.5" r="1.5" />
										</svg>
									</span>
									Precio original: <b>{moneda(pool.precio_original)}</b>
								</li>
							{/if}
							{#if pool.descuento}
								<li class="detalles__fila">
									<span class="detalles__icono" aria-hidden="true">
										<svg
											width="20"
											height="20"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.8"
											stroke-linecap="round"
										>
											<circle cx="12" cy="12" r="9" />
											<path d="M15 9l-6 6" />
											<circle cx="9" cy="9" r="0.8" />
											<circle cx="15" cy="15" r="0.8" />
										</svg>
									</span>
									Descuento: <b class="detalles__descuento">{pool.descuento}</b>
								</li>
							{/if}
							<li class="detalles__fila">
								<span class="detalles__icono" aria-hidden="true">
									<svg
										width="20"
										height="20"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.8"
										stroke-linecap="round"
										stroke-linejoin="round"
									>
										<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0Z" />
										<circle cx="12" cy="10" r="3" />
									</svg>
								</span>
								Dirección: <b>{pool.direccion}</b>
							</li>
							<li class="detalles__fila">
								<span class="detalles__icono" aria-hidden="true">
									<svg
										width="20"
										height="20"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="1.8"
										stroke-linecap="round"
										stroke-linejoin="round"
									>
										<path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-5h6v5" />
									</svg>
								</span>
								Ciudad: <b>{pool.ciudad}</b>
							</li>
						</ul>
						{#if pool.enlace}
							<div class="detalles__accion">
								<Boton
									variante="secundario"
									tamano="sm"
									onclick={() => window.open(pool.enlace, '_blank', 'noopener')}
								>
									Abrir enlace del producto
								</Boton>
							</div>
						{/if}
					</div>
				</Tarjeta>
			</section>

			{#if mostrarAnalisis(pool)}
				<PanelEnlace analisis={pool.analisis_enlace} />
			{/if}

			{#if coordsValidas(pool.latitud, pool.longitud)}
				<section class="bloque">
					<h2>Ubicación</h2>
					<MapaPool lat={pool.latitud} lng={pool.longitud} titulo={pool.titulo} />
					<p class="ayuda ubicacion__referencia">{pool.direccion}, {pool.ciudad}</p>
				</section>
			{/if}

			<section class="bloque">
				<h2>Participantes ({pool.miembros.length + 1})</h2>

				<div class="participantes">
					<Avatar
						nombre={pool.creador.username}
						foto={pool.creador.foto}
						tamano="lg"
						aria-hidden="true"
					/>
					{#each pool.miembros as miembro (miembro.id)}
						<Avatar
							nombre={miembro.usuario.username}
							foto={miembro.usuario.foto}
							aria-hidden="true"
						/>
					{/each}
				</div>

				<div class="creador">
					<Avatar
						nombre={pool.creador.username}
						foto={pool.creador.foto}
						tamano="lg"
						aria-hidden="true"
					/>
					<div class="creador__datos">
						<p class="creador__etiqueta">Administrador del pool</p>
						<p class="creador__nombre">{pool.creador.username}</p>
						<p class="creador__cantidad">{pool.cantidad_creador} u. reservadas</p>
						<p class="creador__dato">
							Pago: <b>{etiquetaPago(pool.tipo_pago)}</b>
						</p>
						<p class="creador__dato">
							Mínimo por persona: <b>{unidades(pool.min_por_integrante)}</b>
						</p>
					</div>
				</div>

				{#if pool.miembros.length}
					<ul class="miembros">
						{#each pool.miembros as miembro (miembro.id)}
							<li class="miembro">
								<div class="miembro__fila">
									<Avatar
										nombre={miembro.usuario.username}
										foto={miembro.usuario.foto}
										tamano="sm"
										aria-hidden="true"
									/>
									<span class="miembro__nombre">{miembro.usuario.username}</span>
									<span class="miembro__cantidad">
										<Badge variante="neutro">{miembro.cantidad} u.</Badge>
									</span>
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

			{#if modoChat !== 'oculto'}
				<PanelChat poolId={pool.id} estado={pool.estado} usuarioId={session.user?.id} />
			{/if}

			{#if esParticipante}
				<section class="bloque">
					<h2>Historial del pool</h2>
					{#if errorHistorial}
						<div class="historial__aviso">
							<Aviso variante="error">{errorHistorial}</Aviso>
						</div>
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
							<div class="historial__mas">
								<Boton variante="secundario" tamano="sm" onclick={verMasHistorial}>Ver más</Boton>
							</div>
						{/if}
					{:else}
						<p class="muted">Todavía no hay movimientos en este pool.</p>
					{/if}
				</section>
			{/if}

			<section class="bloque">
				<div class="compartir">
					<Boton variante="secundario" onclick={copiarEnlace}>
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
							<circle cx="18" cy="5" r="2.5" />
							<circle cx="6" cy="12" r="2.5" />
							<circle cx="18" cy="19" r="2.5" />
							<path d="M8.2 10.8l7.6-4.4M8.2 13.2l7.6 4.4" />
						</svg>
						Copiar enlace
					</Boton>
					<p class="compartir__nota">Quien tenga el enlace puede ver el pool y unirse.</p>
				</div>
				{#if copiaFallida}
					<div class="compartir__copia">
						<Campo id="enlace-copia" etiqueta="Enlace del pool" ayuda="Copialo con Ctrl+C (o Cmd+C).">
							{#snippet children(props)}
								<input
									id="enlace-copia"
									type="text"
									readonly
									value={enlaceCopia}
									bind:this={campoEnlace}
									{...props}
								/>
							{/snippet}
						</Campo>
					</div>
				{/if}
			</section>
		</div>

		<aside class="lateral">
			<Tarjeta>
				<div class="lateral__cuerpo">
					<div class="lateral__banda">
						<Badge variante={pool.estado}>{etiquetaEstado(pool.estado)}</Badge>
						{#if pool.estado !== 'finalizado' && pool.estado !== 'cancelado'}
							<span class="vence vence--{venceTono}">{venceTexto}</span>
						{/if}
					</div>
					<p class="lateral__eyebrow">Disponible</p>
					<p class="lateral__disponible">
						{pool.disponible}<span>de {unidades(pool.cantidad_total)}</span>
					</p>

					<p class="lateral__caduca">Caduca el {fecha(pool.fecha_caducidad)}</p>

					<div class="lateral__acciones">
						{#if errorSolicitud}
							<Aviso variante="error">{errorSolicitud}</Aviso>
						{/if}
						{#if !session.access && pool.estado === 'abierto' && pool.disponible >= pool.min_por_integrante}
							<p class="muted">Ingresá para unirte a este pool.</p>
							<Boton variante="primario" bloque href={resolve('/login')}>Ingresar</Boton>
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
								<Boton variante="secundario" bloque href={resolve(`/pools/${pool.id}/editar`)}>
									Editar pool
								</Boton>
							{/if}
							{#if puedeEliminarDirecto(pool, session.user?.id)}
								<Boton variante="peligro-suave" bloque onclick={eliminar}>Eliminar</Boton>
							{/if}
							{#if pool.estado === 'listo'}
								<Boton variante="primario" bloque onclick={() => cambiarEstado('confirmar')}>
									Confirmar pedido
								</Boton>
							{/if}
							{#if pool.estado === 'en_curso'}
								<Boton variante="primario" bloque onclick={() => cambiarEstado('finalizar')}>
									Finalizar
								</Boton>
							{/if}
							{#if pool.estado === 'abierto' || pool.estado === 'listo'}
								<Boton variante="peligro-suave" bloque onclick={() => cambiarEstado('cancelar')}>
									Cancelar
								</Boton>
							{/if}
							{#if puedeSolicitar}
								<Boton variante="peligro-suave" bloque onclick={solicitarEliminacion}>
									Solicitar eliminación
								</Boton>
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
								<Campo
									id="cantidad"
									etiqueta="Tu cantidad"
									ayuda={`Mínimo ${pool.min_por_integrante} · Podés reservar hasta ${pool.disponible + miMembresia.cantidad}.`}
									error={accionError.cantidad}
								>
									{#snippet children(props)}
										<input
											id="cantidad"
											name="cantidad"
											type="number"
											inputmode="numeric"
											min={pool.min_por_integrante}
											max={pool.disponible + miMembresia.cantidad}
											bind:value={cantidad}
											{...props}
										/>
									{/snippet}
								</Campo>
								<Boton variante="primario" bloque onclick={guardarCantidad}>
									Guardar cantidad
								</Boton>
								<Boton variante="peligro-suave" bloque onclick={salir}>Salir del pool</Boton>
							{/if}
						{:else if puedeReservar}
							<div class="union">
								<Campo
									id="cantidad"
									etiqueta="Cantidad a reservar"
									ayuda={`Mínimo ${pool.min_por_integrante} · Podés reservar hasta ${pool.disponible}.`}
									error={accionError.cantidad}
								>
									{#snippet children(props)}
										<input
											id="cantidad"
											name="cantidad"
											type="number"
											inputmode="numeric"
											min={pool.min_por_integrante}
											max={pool.disponible}
											bind:value={cantidad}
											{...props}
										/>
									{/snippet}
								</Campo>
								<Campo id="telefono" etiqueta="Tu teléfono" error={accionError.telefono}>
									{#snippet children(props)}
										<input
											id="telefono"
											name="telefono"
											type="tel"
											inputmode="tel"
											bind:value={telefono}
											{...props}
										/>
									{/snippet}
								</Campo>
								<Campo
									id="mensaje"
									etiqueta="Mensaje para el creador (opcional)"
									error={accionError.mensaje}
								>
									{#snippet children(props)}
										<textarea
											id="mensaje"
											name="mensaje"
											maxlength="500"
											rows="2"
											bind:value={mensaje}
											{...props}
										></textarea>
									{/snippet}
								</Campo>
								<p class="union__total">
									Tu total <b>{moneda(totalReserva)}</b>
								</p>
								<Boton variante="primario" bloque onclick={unirse}>Unirme al pool</Boton>
							</div>
						{:else if pool.estado !== 'abierto'}
							<p class="muted">Este pool ya no acepta nuevas reservas.</p>
						{/if}

						{#if accionError.detail || accionError.non_field_errors}
							<Aviso variante="error">{accionError.detail || accionError.non_field_errors}</Aviso>
						{/if}
						{#if accionError.estado}
							<Aviso variante="error">{accionError.estado}</Aviso>
						{/if}
					</div>

					<div class="lateral__meta">
						<p>Organiza <strong>{pool.creador.username}</strong></p>
						<p>{vistas(pool.vistas)}</p>
					</div>
				</div>
			</Tarjeta>
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
		color: var(--marca-fuerte);
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

	.detalle__aviso {
		margin-bottom: var(--e-5);
	}

	/* ---------- Encabezado (media + datos, como el mockup) ---------- */

	.encabezado {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr);
		gap: var(--e-7);
		align-items: start;
	}

	.encabezado__media {
		min-width: 0;
	}

	.encabezado__datos {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
		min-width: 0;
	}

	.encabezado__pills {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2);
	}

	.encabezado h1 {
		font-size: var(--texto-2xl);
	}

	.encabezado__producto {
		margin: 0;
		font-size: var(--texto-md);
		color: var(--tinta-suave);
	}

	.encabezado__meta {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-1) var(--e-4);
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-tenue);
	}

	.precio {
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: var(--e-2);
		margin: 0;
	}

	.precio__valor {
		font-family: var(--fuente-display);
		font-size: var(--texto-2xl);
		font-weight: 800;
		letter-spacing: -0.02em;
		font-variant-numeric: tabular-nums;
	}

	.precio__unidad {
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.precio__antes {
		font-size: var(--texto-md);
		color: var(--tinta-tenue);
	}

	/* ---------- Progreso ---------- */

	.progreso-bloque {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
	}

	.progreso__filas {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: var(--e-2) var(--e-3);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.progreso__filas b {
		color: var(--tinta);
		font-variant-numeric: tabular-nums;
	}

	.progreso__restante {
		color: var(--marca-fuerte);
	}

	.progreso__tiempo {
		display: flex;
		align-items: center;
		gap: var(--e-2);
		margin: 0;
		font-size: var(--texto-sm);
		font-weight: 600;
		color: var(--naranja-fuerte);
	}

	/* ---------- Facts (mockup 03) ---------- */

	.facts {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: var(--e-2);
		margin: var(--e-5) 0 0;
		padding: 0;
		list-style: none;
	}

	.fact {
		display: flex;
		align-items: center;
		gap: var(--e-2);
		padding: var(--e-3);
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
		font-size: var(--texto-xs);
		line-height: 1.35;
		color: var(--tinta-suave);
	}

	.fact svg {
		flex: none;
		color: var(--acento-naranja);
	}

	.fact b:not(.vence) {
		color: var(--tinta);
	}

	/* ---------- Chip de vencimiento ---------- */

	.vence {
		display: inline-flex;
		align-items: center;
		padding: 0.1rem 0.55rem;
		border-radius: var(--radio-full);
		font-size: var(--texto-xs);
		font-weight: 600;
		line-height: 1.6;
	}

	.vence--verde {
		background: var(--exito-suave);
		color: var(--texto-exito);
	}

	.vence--ambar {
		background: var(--alerta-suave);
		color: var(--texto-alerta);
	}

	.vence--coral {
		background: var(--peligro-suave);
		color: var(--texto-peligro);
	}

	/* ---------- Galería ---------- */

	.galeria__marco {
		overflow: hidden;
		border: 1px solid var(--linea);
		border-radius: 22px;
		background: var(--crema);
	}

	.galeria__activa {
		width: 100%;
		aspect-ratio: 16 / 10;
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
		background: var(--crema);
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
		border-color: var(--marca);
		opacity: 1;
	}

	.miniatura:focus-visible {
		outline: 2px solid var(--marca);
		outline-offset: 2px;
	}

	.galeria__vacia {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--e-2);
		aspect-ratio: 16 / 10;
		border: 1px dashed var(--borde-peligro-fuerte);
		border-radius: 22px;
		background: var(--crema);
		color: var(--naranja-fuerte);
	}

	.galeria__vacia p {
		margin: 0;
		font-size: var(--texto-sm);
		font-weight: 500;
	}

	/* ---------- Bloques ---------- */

	.bloque {
		margin-top: var(--e-7);
		padding-top: var(--e-5);
		border-top: 1px solid var(--linea);
	}

	.bloque h2 {
		margin-bottom: var(--e-4);
		font-size: var(--texto-lg);
	}

	/* ---------- Stepper de estado ---------- */

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
		background: var(--marca);
		border-color: var(--marca);
		box-shadow: 0 0 0 4px var(--melocoton);
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

	/* ---------- Descripción ---------- */

	.prosa {
		max-width: var(--ancho-lectura);
		color: var(--tinta-suave);
		white-space: pre-line;
	}

	/* ---------- Detalles del producto ---------- */

	.detalles {
		padding: var(--e-5) var(--e-6);
	}

	.detalles h2 {
		margin-bottom: var(--e-4);
		font-size: var(--texto-lg);
	}

	.detalles__lista {
		display: flex;
		flex-direction: column;
		gap: var(--e-3);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.detalles__fila {
		display: flex;
		align-items: center;
		gap: var(--e-3);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.detalles__fila b {
		color: var(--tinta);
		overflow-wrap: anywhere;
	}

	.detalles__icono {
		display: inline-flex;
		flex: none;
		color: var(--acento-naranja);
	}

	.detalles__descuento {
		color: var(--marca-fuerte);
	}

	.detalles__accion {
		margin-top: var(--e-4);
	}

	/* ---------- Ubicación ---------- */

	.ubicacion__referencia {
		margin-top: var(--e-3);
	}

	/* ---------- Participantes ---------- */

	.participantes {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2);
		margin-bottom: var(--e-4);
	}

	.creador {
		display: flex;
		align-items: center;
		gap: var(--e-4);
		padding: var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--crema);
	}

	.creador__datos {
		min-width: 0;
	}

	.creador__etiqueta {
		margin: 0;
		font-size: var(--texto-xs);
		font-weight: 600;
		color: var(--naranja-fuerte);
	}

	.creador__nombre {
		margin: var(--e-1) 0 0;
		font-size: var(--texto-md);
		font-weight: 700;
		color: var(--tinta);
		overflow-wrap: anywhere;
	}

	.creador__cantidad,
	.creador__dato {
		margin: var(--e-1) 0 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.creador__dato b {
		color: var(--tinta);
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

	/* ---------- Historial (timeline) ---------- */

	.historial {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
		margin: 0;
		padding: 0 0 0 var(--e-4);
		list-style: none;
		border-left: 2px solid var(--linea);
	}

	.historial__item {
		display: flex;
		align-items: flex-start;
		gap: var(--e-3);
	}

	.historial__punto {
		flex: none;
		width: 0.7rem;
		height: 0.7rem;
		margin: 0.35rem 0 0 calc(-1 * var(--e-4) - 0.45rem);
		border: 2px solid var(--superficie);
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

	.historial__aviso {
		margin-bottom: var(--e-4);
	}

	/* ---------- Compartir ---------- */

	.compartir {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3) var(--e-4);
		padding: var(--e-3) var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--crema);
	}

	.compartir__nota {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.compartir__copia {
		margin-top: var(--e-3);
	}

	/* ---------- Lateral ---------- */

	.lateral {
		position: sticky;
		top: calc(var(--alto-cabecera) + var(--e-5));
	}

	.lateral__cuerpo {
		display: flex;
		flex-direction: column;
		padding: var(--e-5) var(--e-5) var(--e-4);
	}

	.lateral__banda {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2);
		margin-bottom: var(--e-4);
		padding-bottom: var(--e-4);
		border-bottom: 1px solid var(--linea);
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
		font-weight: 800;
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

	.union {
		display: flex;
		flex-direction: column;
		gap: var(--e-1);
	}

	.union__total {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--e-3);
		margin: var(--e-2) 0 var(--e-3);
		padding-top: var(--e-3);
		border-top: 1px solid var(--linea);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.union__total b {
		font-family: var(--fuente-display);
		font-size: var(--texto-xl);
		font-weight: 800;
		color: var(--tinta);
		font-variant-numeric: tabular-nums;
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

	@media (max-width: 1000px) {
		.encabezado {
			grid-template-columns: 1fr;
			gap: var(--e-6);
		}
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
		.linea__paso {
			gap: var(--e-1);
		}

		.linea__nombre {
			font-size: 0.68rem;
		}
	}
</style>
