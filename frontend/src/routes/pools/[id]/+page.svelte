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
	import { diasHasta, fecha, moneda } from '$lib/formato.js';
	import { esIntegrante, fechaHora, textoEvento } from '$lib/historial.js';
	import DialogoUnion from '$lib/DialogoUnion.svelte';
	import MapaPool from '$lib/MapaPool.svelte';
	import MiniPerfil from '$lib/MiniPerfil.svelte';
	import PanelCalificar from '$lib/PanelCalificar.svelte';
	import PanelChat from '$lib/PanelChat.svelte';
	import PanelEliminacion from '$lib/PanelEliminacion.svelte';
	import PanelEnlace from '$lib/PanelEnlace.svelte';
	import PanelPagos from '$lib/PanelPagos.svelte';
	import {
		faltanPagos,
		faltanRecepciones,
		monto,
		puedeConfirmarPedido,
		puedeFinalizar
	} from '$lib/pagos.js';
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
	let dialogoGaleria = $state();
	let toqueX = 0;
	let compraVisible = $state(false);
	let pieVisible = $state(false);
	let copiaFallida = $state(false);
	let enlaceCopia = $state('');
	let campoEnlace = $state();
	let historial = $state([]);
	let hayMasHistorial = $state(false);
	let errorHistorial = $state('');
	let paginaHistorial = $state(1);
	let cargandoHistorial = $state(true);
	// Popup "¡Te uniste!": guarda la reserva confirmada para el resumen.
	let unionConfirmada = $state(false);
	let ultimaUnion = $state({ cantidad: 0, total: 0 });
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
	// Con el pago enviado o confirmado la membresía queda fija (regla del backend).
	const pagoEnviado = $derived(['enviado', 'confirmado'].includes(miMembresia?.pago_estado));
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

	// Secciones del detalle: pestañas con las que se puede deep-linkear (?seccion=).
	const IDS_SECCIONES = ['resumen', 'participantes', 'pagos', 'chat', 'historial'];

	function seccionDeUrl() {
		if (typeof window === 'undefined') return 'resumen';
		const valor = new URLSearchParams(window.location.search).get('seccion');
		return IDS_SECCIONES.includes(valor) ? valor : 'resumen';
	}

	let seccionActiva = $state(seccionDeUrl());

	const tienePagos = $derived(
		esParticipante && ['listo', 'en_curso', 'finalizado'].includes(pool?.estado)
	);

	const accionPendientePagos = $derived.by(() => {
		if (!tienePagos) return false;
		if (esCreador) {
			if (pool.estado === 'listo') return pool.miembros.some((m) => m.pago_estado === 'enviado');
			if (pool.estado === 'en_curso')
				return pool.miembros.some((m) => !m.recepcion_confirmada);
			return false;
		}
		if (!miMembresia) return false;
		if (pool.estado === 'listo')
			return ['pendiente', 'rechazado'].includes(miMembresia.pago_estado);
		if (pool.estado === 'en_curso') return !miMembresia.recepcion_confirmada;
		return false;
	});

	const secciones = $derived([
		{ id: 'resumen', texto: 'Resumen' },
		{ id: 'participantes', texto: `Participantes (${(pool?.miembros.length ?? 0) + 1})` },
		{ id: 'pagos', texto: 'Pagos y entrega', pendiente: accionPendientePagos },
		{ id: 'chat', texto: 'Chat' },
		{ id: 'historial', texto: 'Historial' }
	]);

	const textoEstado = $derived.by(() => {
		if (!pool) return '';
		if (pool.estado === 'abierto') {
			return pool.disponible > 0
				? 'Abierto a nuevas reservas hasta completar el cupo.'
				: 'Cupo completo: falta confirmar los pagos.';
		}
		if (pool.estado === 'listo') {
			return puedeConfirmarPedido(pool)
				? 'Todos los pagos están confirmados.'
				: 'Se alcanzó el mínimo. Revisá los pagos para confirmar el pedido.';
		}
		if (pool.estado === 'en_curso') {
			return puedeFinalizar(pool)
				? 'Todas las entregas están confirmadas.'
				: 'El pedido está en curso. Confirmá la entrega cuando recibas el producto.';
		}
		if (pool.estado === 'finalizado') return 'El pool se completó: pagos y entregas confirmados.';
		if (pool.estado === 'cancelado') return 'Este pool fue cancelado.';
		return '';
	});

	// Acción principal para la barra fija de mobile.
	const accionFlotante = $derived.by(() => {
		if (!pool) return null;
		if (esCreador) {
			if (pool.estado === 'listo') {
				return puedeConfirmarPedido(pool)
					? { texto: 'Confirmar pedido', accion: () => cambiarEstado('confirmar') }
					: { texto: 'Revisar pagos', accion: () => cambiarSeccion('pagos', true) };
			}
			if (pool.estado === 'en_curso') {
				return puedeFinalizar(pool)
					? { texto: 'Finalizar', accion: () => cambiarEstado('finalizar') }
					: { texto: 'Revisar entregas', accion: () => cambiarSeccion('pagos', true) };
			}
			return null;
		}
		if (!session.access) {
			return pool.estado === 'abierto' && pool.disponible >= pool.min_por_integrante
				? { texto: 'Ingresar', href: resolve('/login') }
				: null;
		}
		if (miMembresia) {
			if (pool.estado === 'listo' && ['pendiente', 'rechazado'].includes(miMembresia.pago_estado)) {
				return { texto: 'Subir comprobante', accion: () => cambiarSeccion('pagos', true) };
			}
			if (pool.estado === 'en_curso' && !miMembresia.recepcion_confirmada) {
				return { texto: 'Confirmar entrega', accion: () => cambiarSeccion('pagos', true) };
			}
			if ((pool.estado === 'abierto' || pool.estado === 'listo') && !pagoEnviado) {
				return { texto: 'Editar mi cantidad', accion: irAFormulario };
			}
			return null;
		}
		if (puedeReservar) return { texto: 'Unirme al pool', accion: irAFormulario };
		return null;
	});

	const textoPagosBloqueado = $derived(
		esParticipante
			? pool?.estado === 'cancelado'
				? 'El pool se canceló antes de habilitar los pagos.'
				: 'Los pagos se habilitan cuando el pool está listo.'
			: session.access
				? 'Los pagos y la entrega se ven solo para los integrantes del pool.'
				: 'Ingresá y unite al pool para ver los pagos y la entrega.'
	);

	const textoChatBloqueado = $derived(
		session.access
			? 'El chat es solo para los integrantes del pool.'
			: 'Ingresá y unite al pool para usar el chat.'
	);

	const textoHistorialBloqueado = $derived(
		session.access
			? 'El historial es solo para los integrantes del pool.'
			: 'Ingresá y unite al pool para ver el historial.'
	);





	// En mobile la barra scrollea: deja visible la pestaña activa.
	$effect(() => {
		seccionActiva;
		const barra = document.querySelector('.pestanas-detalle');
		const activa = barra?.querySelector('.pestanas-detalle__enlace.activo');
		if (!barra || !activa || barra.scrollWidth <= barra.clientWidth) return;
		const inicio = activa.offsetLeft;
		const fin = inicio + activa.offsetWidth;
		if (inicio < barra.scrollLeft) barra.scrollLeft = inicio;
		else if (fin > barra.scrollLeft + barra.clientWidth) barra.scrollLeft = fin - barra.clientWidth;
	});

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

	// La barra fija no repite precio/CTA cuando la compra ya está a la vista.
	$effect(() => {
		if (!pool?.id) {
			compraVisible = false;
			return;
		}
		const compra = document.querySelector('.lateral');
		if (!compra || !('IntersectionObserver' in window)) return;
		const observador = new IntersectionObserver(
			([entrada]) => {
				compraVisible = entrada.isIntersecting;
			},
			{ threshold: 0.2 }
		);
		observador.observe(compra);
		return () => observador.disconnect();
	});

	$effect(() => {
		const pie = document.querySelector('.pie');
		if (!pie || !('IntersectionObserver' in window)) return;
		const observador = new IntersectionObserver(
			([entrada]) => {
				pieVisible = entrada.isIntersecting;
			},
			{ threshold: 0.05 }
		);
		observador.observe(pie);
		return () => observador.disconnect();
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

	const precioCompra = $derived.by(() => {
		if (!pool) return null;
		if (esCreador) {
			return {
				rotulo: 'Valor del pool',
				valor: Number(pool.precio_unitario) * Number(pool.cantidad_total),
				detalle: ''
			};
		}
		if (miMembresia) {
			return {
				rotulo: 'Tu parte',
				valor: monto(pool, miMembresia),
				detalle: `${miMembresia.cantidad} ${miMembresia.cantidad === 1 ? 'unidad' : 'unidades'}`
			};
		}
		return {
			rotulo: 'Precio por unidad',
			valor: Number(pool.precio_unitario),
			detalle: ''
		};
	});

	// Estimación de la reserva para el resumen del panel de unión (presentación).
	const totalReserva = $derived(pool ? Number(cantidad || 0) * Number(pool.precio_unitario || 0) : 0);

	/** "1 unidad" / "N unidades". */
	const unidades = (n) => `${n} ${n === 1 ? 'unidad' : 'unidades'}`;

	async function unirse() {
		accionError = {};
		try {
			const payload = payloadUnion(cantidad, telefono, mensaje);
			await api(`/pools/${pool.id}/unirse/`, { method: 'POST', body: payload });
			ultimaUnion = { cantidad: payload.cantidad, total: totalReserva };
			await cargar(pool.id);
			unionConfirmada = true;
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

	/** Tras una acción de pagos: refresca el pool (sin spinner) y el historial. */
	async function recargarPagos() {
		pool = await api(`/pools/${pool.id}/`);
		await cargarHistorial(pool.id);
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

	function movimiento() {
		return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
	}

	function moverGaleria(paso) {
		if (!pool?.imagenes?.length) return;
		indiceImagen = (indiceImagen + paso + pool.imagenes.length) % pool.imagenes.length;
	}

	function toqueInicio(evento) {
		toqueX = evento.changedTouches[0].clientX;
	}

	function toqueFin(evento) {
		const dx = evento.changedTouches[0].clientX - toqueX;
		if (Math.abs(dx) > 40) moverGaleria(dx > 0 ? -1 : 1);
	}

	async function irAFormulario() {
		document
			.querySelector('.lateral__acciones')
			?.scrollIntoView({ behavior: movimiento(), block: 'center' });
		await tick();
		document.getElementById('cantidad')?.focus({ preventScroll: true });
	}

	async function cambiarSeccion(id, desplazar = false) {
		if (id === seccionActiva) return;
		seccionActiva = id;
		// Cambia la URL sin navegar: la pestaña responde al instante y no recarga datos.
		const url = new URL(window.location.href);
		url.searchParams.set('seccion', id);
		history.replaceState(history.state, '', url);
		await tick();

		const barra = document.querySelector('.pestanas-detalle');
		if (desplazar) {
			barra?.scrollIntoView({ behavior: movimiento(), block: 'start' });
			return;
		}

		const cabecera =
			Number.parseFloat(
				getComputedStyle(document.documentElement).getPropertyValue('--alto-cabecera')
			) || 76;
		// Solo si el menú ya quedó pegado arriba: volver al inicio de la sección.
		if (barra && barra.getBoundingClientRect().top <= cabecera + 1) {
			document
				.querySelector('.seccion')
				?.scrollIntoView({ behavior: movimiento(), block: 'start' });
		}
	}

	function irASeccion(evento, id) {
		// Deja abrir en pestaña nueva con el enlace normal.
		if (evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.altKey || evento.button !== 0) {
			return;
		}
		evento.preventDefault();
		if (id === seccionActiva) return;
		cambiarSeccion(id);
	}

	async function copiarEnlace() {
		copiaFallida = false;
		const url = new URL(location.href);
		url.searchParams.delete('seccion');
		const enlace = url.toString();

		// En mobile, hoja de compartir nativa; en desktop, portapapeles.
		if (window.matchMedia('(pointer: coarse)').matches && navigator.share) {
			try {
				await navigator.share({ title: pool?.titulo ?? 'PoolShop', url: enlace });
				return;
			} catch (e) {
				if (e.name === 'AbortError') return;
			}
		}

		try {
			await navigator.clipboard.writeText(enlace);
			notificar('Enlace copiado.');
		} catch {
			enlaceCopia = enlace;
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

{#snippet candado()}
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
		<rect x="4" y="10" width="16" height="10" rx="2" />
		<path d="M8 10V7a4 4 0 0 1 8 0v3" />
	</svg>
{/snippet}

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

	{#if aviso === 'imagenes'}
		<div class="detalle__aviso">
			<Aviso variante="aviso">
				El pool se creó, pero algunas imágenes no se pudieron subir.
			</Aviso>
		</div>
	{/if}

	<div class="detalle animar">
		<div class="principal">
			<div class="hero">
				<section class="encabezado">
				<div class="encabezado__media">
					{#if pool.imagenes.length}
						<div class="galeria__marco">
							<button
								class="galeria__abrir"
								type="button"
								aria-label="Ampliar imagen"
								aria-haspopup="dialog"
								onclick={() => dialogoGaleria?.showModal()}
							>
								<img
									class="galeria__activa"
									src={imagenActiva.imagen}
									alt={pool.titulo}
									width="800"
									height="600"
									decoding="async"
								/>
								<span class="galeria__lupa" aria-hidden="true">
									<svg
										width="18"
										height="18"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
									>
										<circle cx="11" cy="11" r="7" />
										<path d="m20 20-3.5-3.5M8 11h6M11 8v6" />
									</svg>
								</span>
							</button>
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
					{#if pool.nombre_producto && pool.nombre_producto !== pool.titulo}
						<p class="encabezado__producto">{pool.nombre_producto}</p>
					{/if}

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
								{vence !== null && vence < 0 ? 'Venció el' : 'Vence el'}
								{fecha(pool.fecha_caducidad)}
							</p>
						{/if}
					</div>

					{#if pool.enlace}
						<div class="encabezado__enlace">
							<Boton
								variante="secundario"
								tamano="sm"
								onclick={() => window.open(pool.enlace, '_blank', 'noopener')}
							>
								Ver producto original
							</Boton>
						</div>
					{/if}
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
				{:else}
					<p class="linea__detalle">{textoEstado}</p>
				{/if}
			</section>
			</div>

			<div class="detalle__cuerpo">
				<nav class="pestanas-detalle" aria-label="Secciones del pool">
					{#each secciones as s (s.id)}
						<a
							class="pestanas-detalle__enlace"
							class:activo={seccionActiva === s.id}
							href={`/pools/${pool.id}?seccion=${s.id}`}
							aria-current={seccionActiva === s.id ? 'true' : undefined}
							onclick={(evento) => irASeccion(evento, s.id)}
						>
							{s.texto}
							{#if s.pendiente}
								<span class="pestanas-detalle__punto" aria-hidden="true"></span>
								<span class="sr-only">Acción pendiente</span>
							{/if}
						</a>
					{/each}
				</nav>

				<div class="seccion">
					{#if seccionActiva === 'resumen'}
			{#if pool.descripcion}
				<section class="bloque">
					<h2>Descripción</h2>
					<p class="prosa">{pool.descripcion}</p>
				</section>
			{/if}

			{#if coordsValidas(pool.latitud, pool.longitud)}
				<section class="bloque">
					<h2>Ubicación</h2>
					<MapaPool lat={pool.latitud} lng={pool.longitud} titulo={pool.titulo} />
					<div class="ubicacion__pie">
						<p class="ayuda ubicacion__referencia">{pool.direccion}, {pool.ciudad}</p>
						<a
							class="ubicacion__enlace"
							href={`https://www.google.com/maps/search/?api=1&query=${pool.latitud},${pool.longitud}`}
							target="_blank"
							rel="noopener"
						>
							Abrir en Maps
						</a>
					</div>
				</section>
			{/if}

			{#if mostrarAnalisis(pool)}
				<PanelEnlace analisis={pool.analisis_enlace} />
			{/if}

			{#if pool.estado === 'finalizado' && esParticipante}
				<PanelCalificar {pool} usuarioId={session.user?.id} />
			{/if}
					{:else if seccionActiva === 'participantes'}
			<section class="bloque">
				<h2>Participantes ({pool.miembros.length + 1})</h2>

				<ul class="roster">
					<li class="roster__item">
						<Avatar
							nombre={pool.creador.username}
							foto={pool.creador.foto}
							tamano="md"
							aria-hidden="true"
						/>
						<div class="roster__datos">
							<p class="roster__nombre">
								<a href={resolve(`/usuarios/${pool.creador.id}`)}>{pool.creador.username}</a>
								<span class="roster__rol">Administrador</span>
							</p>
							<p class="roster__meta">{pool.cantidad_creador} u. reservadas</p>
						</div>
					</li>

					{#each pool.miembros as miembro (miembro.id)}
						<li class="roster__item">
							<Avatar
								nombre={miembro.usuario.username}
								foto={miembro.usuario.foto}
								tamano="sm"
								aria-hidden="true"
							/>
							<div class="roster__datos">
								<p class="roster__nombre">
									<a href={resolve(`/usuarios/${miembro.usuario.id}`)}>{miembro.usuario.username}</a>
									<span class="roster__rol roster__rol--miembro">Miembro</span>
								</p>
								<p class="roster__meta">{miembro.cantidad} u. reservadas</p>
								{#if esCreador}
									{#if miembro.telefono}
										<p class="roster__dato">Teléfono: {miembro.telefono}</p>
									{/if}
									{#if miembro.mensaje}
										<p class="roster__dato">{miembro.mensaje}</p>
									{/if}
									<MiniPerfil usuarioId={miembro.usuario.id} />
								{/if}
							</div>
						</li>
					{/each}
				</ul>

				{#if !pool.miembros.length}
					<p class="muted">Nadie más se unió todavía.</p>
				{/if}
			</section>
					{:else if seccionActiva === 'pagos'}
						{#if tienePagos}
							<PanelPagos {pool} usuarioId={session.user?.id} onactualizar={recargarPagos} />
						{:else}
							<section class="bloque">
								<h2>Pagos y entrega</h2>
								<div class="bloqueo">
									<span class="bloqueo__icono" aria-hidden="true">{@render candado()}</span>
									<p>{textoPagosBloqueado}</p>
								</div>
							</section>
						{/if}
					{:else if seccionActiva === 'chat'}
						{#if modoChat !== 'oculto'}
							<PanelChat poolId={pool.id} estado={pool.estado} usuarioId={session.user?.id} />
						{:else}
							<section class="bloque">
								<h2>Chat del pool</h2>
								<div class="bloqueo">
									<span class="bloqueo__icono" aria-hidden="true">{@render candado()}</span>
									<p>{textoChatBloqueado}</p>
								</div>
							</section>
						{/if}
					{:else if seccionActiva === 'historial'}
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
						{:else}
							<section class="bloque">
								<h2>Historial del pool</h2>
								<div class="bloqueo">
									<span class="bloqueo__icono" aria-hidden="true">{@render candado()}</span>
									<p>{textoHistorialBloqueado}</p>
								</div>
							</section>
						{/if}
					{/if}
				</div>
			</div>
		</div>

		<aside class="lateral">
			<Tarjeta>
				<div class="lateral__cuerpo">
					<div class="compra">
						<div class="compra__cabecera">
							<p class="compra__rotulo">{precioCompra.rotulo}</p>
							{#if pool.descuento}
								<span class="compra__descuento">{pool.descuento}</span>
							{/if}
						</div>
						<p class="compra__precio">{moneda(precioCompra.valor)}</p>
						{#if precioCompra.detalle}
							<p class="compra__detalle">{precioCompra.detalle}</p>
						{/if}
						{#if pool.precio_original && !miMembresia && !esCreador}
							<p class="compra__antes">Antes <s>{moneda(pool.precio_original)}</s> por unidad</p>
						{/if}
						<p class="compra__condiciones">
							Mínimo {unidades(pool.min_por_integrante)} por persona. Pago por {etiquetaPago(
								pool.tipo_pago
							).toLowerCase()}.
						</p>
					</div>

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
								<Boton
									variante="primario"
									bloque
									disabled={!puedeConfirmarPedido(pool)}
									onclick={() => cambiarEstado('confirmar')}
								>
									Confirmar pedido
								</Boton>
								{#if !puedeConfirmarPedido(pool)}
									<p class="ayuda">
										{faltanPagos(pool)}
										<button type="button" class="enlace" onclick={() => cambiarSeccion('pagos', true)}>
											Revisalos en “Pagos y entrega”
										</button>.
									</p>
								{/if}
							{/if}
							{#if pool.estado === 'en_curso'}
								<Boton
									variante="primario"
									bloque
									disabled={!puedeFinalizar(pool)}
									onclick={() => cambiarEstado('finalizar')}
								>
									Finalizar
								</Boton>
								{#if !puedeFinalizar(pool)}
									<p class="ayuda">
										{faltanRecepciones(pool)}
										<button type="button" class="enlace" onclick={() => cambiarSeccion('pagos', true)}>
											Revisalas en “Pagos y entrega”
										</button>
									</p>
								{/if}
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
							{#if !solicitudPendiente && (pool.estado === 'abierto' || pool.estado === 'listo') && !pagoEnviado}
								<Campo
									id="cantidad"
									etiqueta="Tu cantidad"
									ayuda={`Podés reservar hasta ${pool.disponible + miMembresia.cantidad}.`}
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
									ayuda={`Podés reservar hasta ${pool.disponible}.`}
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
						<p>
							Organiza <a href={resolve(`/usuarios/${pool.creador.id}`)}
								><strong>{pool.creador.username}</strong></a
							>
						</p>
					</div>

					<div class="lateral__compartir">
						<Boton variante="ghost" tamano="sm" onclick={copiarEnlace}>
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
								<circle cx="18" cy="5" r="2.5" />
								<circle cx="6" cy="12" r="2.5" />
								<circle cx="18" cy="19" r="2.5" />
								<path d="M8.2 10.8l7.6-4.4M8.2 13.2l7.6 4.4" />
							</svg>
							Compartir enlace
						</Boton>
						<p class="compartir__nota">Quien tenga el enlace puede ver el pool y unirse.</p>
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
					</div>
				</div>
			</Tarjeta>
		</aside>
	</div>

	{#if pool.imagenes.length}
		<dialog
			class="lightbox"
			bind:this={dialogoGaleria}
			aria-label={`Imágenes de ${pool.titulo}`}
			onclick={(evento) => {
				if (evento.target === dialogoGaleria) dialogoGaleria.close();
			}}
			onkeydown={(evento) => {
				if (evento.key === 'ArrowLeft') {
					evento.preventDefault();
					moverGaleria(-1);
				}
				if (evento.key === 'ArrowRight') {
					evento.preventDefault();
					moverGaleria(1);
				}
			}}
			ontouchstart={toqueInicio}
			ontouchend={toqueFin}
		>
			<div class="lightbox__caja">
				<button
					class="lightbox__cerrar"
					type="button"
					aria-label="Cerrar"
					onclick={() => dialogoGaleria.close()}
				>
					<svg
						width="22"
						height="22"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
					>
						<path d="M6 6l12 12M18 6 6 18" />
					</svg>
				</button>

				<img class="lightbox__imagen" src={imagenActiva.imagen} alt={pool.titulo} decoding="async" />

				{#if pool.imagenes.length > 1}
					<button
						class="lightbox__nav lightbox__nav--prev"
						type="button"
						aria-label="Imagen anterior"
						onclick={() => moverGaleria(-1)}
					>
						<svg
							width="24"
							height="24"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="m15 18-6-6 6-6" />
						</svg>
					</button>
					<button
						class="lightbox__nav lightbox__nav--next"
						type="button"
						aria-label="Imagen siguiente"
						onclick={() => moverGaleria(1)}
					>
						<svg
							width="24"
							height="24"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path d="m9 6 6 6-6 6" />
						</svg>
					</button>
					<p class="lightbox__contador">{indiceImagen + 1} / {pool.imagenes.length}</p>
				{/if}
			</div>
		</dialog>
	{/if}

	{#if accionFlotante && !compraVisible && !pieVisible}
		<div class="barra-fija">
			<div class="barra-fija__precio">
				<span class="barra-fija__valor">{moneda(precioCompra.valor)}</span>
				<span class="barra-fija__unidad">{precioCompra.rotulo}</span>
			</div>
			<Boton
				variante="primario"
				href={accionFlotante.href}
				onclick={accionFlotante.accion}
			>
				{accionFlotante.texto}
			</Boton>
		</div>
	{/if}
{/if}

{#if pool}
	<DialogoUnion
		bind:abierto={unionConfirmada}
		titulo={pool.titulo}
		cantidad={ultimaUnion.cantidad}
		total={ultimaUnion.total}
	/>
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

	.enlace {
		padding: 0;
		border: 0;
		background: none;
		color: var(--marca-fuerte);
		font: inherit;
		text-decoration: underline;
		text-underline-offset: 0.15em;
		cursor: pointer;
	}

	.enlace:hover {
		color: var(--marca-oscuro);
	}

	.detalle {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(300px, 340px);
		grid-template-areas:
			'hero compra'
			'cuerpo cuerpo';
		gap: var(--e-6);
		align-items: start;
		padding-bottom: 5.5rem;
	}

	.principal {
		display: contents;
	}

	.hero {
		grid-area: hero;
		min-width: 0;
	}

	.detalle__cuerpo {
		grid-area: cuerpo;
		min-width: 0;
	}

	/* ---------- Pestañas de secciones ---------- */

	.pestanas-detalle {
		position: sticky;
		top: var(--alto-cabecera);
		z-index: 10;
		display: flex;
		gap: 2px;
		margin: var(--e-5) 0 var(--e-5);
		padding: 5px;
		border-radius: var(--radio);
		background: var(--melocoton-fuerte);
		overflow-x: auto;
		overscroll-behavior-x: contain;
		scrollbar-width: none;
		scroll-margin-top: var(--alto-cabecera);
	}

	.pestanas-detalle::-webkit-scrollbar {
		display: none;
	}

	.pestanas-detalle__enlace {
		display: flex;
		align-items: center;
		gap: 0.4em;
		min-height: var(--alto-tap);
		padding: 0 1rem;
		border-radius: var(--radio-sm);
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
		font-weight: 700;
		white-space: nowrap;
	}

	.pestanas-detalle__enlace:hover {
		color: var(--marca-fuerte);
		text-decoration: none;
	}

	.pestanas-detalle__enlace.activo {
		background: var(--superficie);
		color: var(--marca-fuerte);
	}

	.pestanas-detalle__punto {
		width: 0.4rem;
		height: 0.4rem;
		border-radius: 50%;
		background: var(--marca);
		flex: none;
	}

	.seccion {
		scroll-margin-top: calc(var(--alto-cabecera) + 4rem);
	}

	/* Contenido de lectura: las pestañas ocupan todo, el texto no se estira. */
	.seccion :global(.chat) {
		max-width: 48rem;
	}

	.seccion :global(.mia) {
		max-width: 60rem;
	}

	/* El primer bloque de cada pestaña ya no necesita separador propio. */
	.seccion > .bloque:first-child,
	.seccion > :global(.pagos),
	.seccion > :global(.chat-seccion) {
		margin-top: 0;
		padding-top: 0;
		border-top: 0;
	}

	.bloqueo {
		display: flex;
		align-items: flex-start;
		gap: var(--e-3);
		padding: var(--e-4) var(--e-5);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--crema);
	}

	.bloqueo__icono {
		display: grid;
		place-items: center;
		flex: none;
		width: 2.25rem;
		height: 2.25rem;
		border-radius: 50%;
		background: var(--melocoton);
		color: var(--naranja-fuerte);
	}

	.bloqueo p {
		margin: 0;
		max-width: 60ch;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
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

	.encabezado__enlace {
		margin-top: var(--e-1);
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

	/* ---------- Galería ---------- */

	.galeria__marco {
		overflow: hidden;
		border: 1px solid var(--linea);
		border-radius: 22px;
		background: var(--crema);
	}

	.galeria__abrir {
		position: relative;
		display: block;
		width: 100%;
		padding: 0;
		border: 0;
		background: none;
		cursor: zoom-in;
	}

	.galeria__lupa {
		position: absolute;
		top: var(--e-3);
		right: var(--e-3);
		display: grid;
		place-items: center;
		width: 2.25rem;
		height: 2.25rem;
		border: 1px solid var(--linea);
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.94);
		color: var(--tinta);
		pointer-events: none;
	}

	.galeria__activa {
		width: 100%;
		aspect-ratio: 16 / 10;
		object-fit: cover;
	}

	/* ---------- Lightbox ---------- */

	.lightbox {
		width: min(94vw, 1100px);
		max-width: none;
		max-height: none;
		padding: 0;
		border: 0;
		background: transparent;
		overflow: visible;
	}

	.lightbox::backdrop {
		background: rgba(31, 21, 18, 0.82);
	}

	.lightbox__caja {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 20rem;
		padding: var(--e-4);
		border-radius: var(--radio);
		background: var(--crema);
	}

	.lightbox__imagen {
		display: block;
		max-width: 100%;
		max-height: 78vh;
		width: auto;
		border-radius: var(--radio);
		object-fit: contain;
	}

	.lightbox__cerrar,
	.lightbox__nav {
		display: grid;
		place-items: center;
		border: 1px solid var(--linea);
		border-radius: 50%;
		background: var(--fondo);
		color: var(--tinta);
		cursor: pointer;
		box-shadow: var(--sombra-md);
	}

	.lightbox__cerrar {
		position: absolute;
		top: var(--e-3);
		right: var(--e-3);
		z-index: 2;
		width: 2.75rem;
		height: 2.75rem;
	}

	.lightbox__nav {
		position: absolute;
		top: 50%;
		width: 2.75rem;
		height: 2.75rem;
		translate: 0 -50%;
	}

	.lightbox__nav--prev {
		left: var(--e-3);
	}

	.lightbox__nav--next {
		right: var(--e-3);
	}

	.lightbox__contador {
		position: absolute;
		bottom: var(--e-3);
		left: 50%;
		margin: 0;
		padding: 0.2rem 0.7rem;
		border-radius: var(--radio-full);
		background: rgba(31, 21, 18, 0.62);
		color: #fff;
		font-size: var(--texto-xs);
		font-variant-numeric: tabular-nums;
		translate: -50% 0;
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

	.linea__detalle {
		margin: var(--e-3) 0 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	/* ---------- Descripción ---------- */

	.prosa {
		max-width: var(--ancho-lectura);
		color: var(--tinta-suave);
		white-space: pre-line;
	}

	/* ---------- Ubicación ---------- */

	.ubicacion__pie {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-2) var(--e-4);
		margin-top: var(--e-3);
	}

	.ubicacion__referencia {
		margin: 0;
	}

	.ubicacion__enlace {
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	/* ---------- Participantes ---------- */

	.roster {
		margin: var(--e-3) 0 0;
		padding: 0;
		list-style: none;
		border-top: 1px solid var(--linea);
	}

	.roster__item {
		display: flex;
		align-items: flex-start;
		gap: var(--e-3);
		padding: var(--e-4) 0;
		border-bottom: 1px solid var(--linea);
	}

	.roster__datos {
		display: flex;
		flex: 1;
		flex-direction: column;
		gap: var(--e-1);
		min-width: 0;
	}

	.roster__nombre {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--e-2);
		margin: 0;
		font-weight: 600;
		overflow-wrap: anywhere;
	}

	.roster__rol {
		font-size: var(--texto-xs);
		font-weight: 600;
		color: var(--marca-fuerte);
	}

	.roster__rol--miembro {
		color: var(--tinta-tenue);
		font-weight: 500;
	}

	.roster__meta {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.roster__dato {
		margin: 0;
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
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

	.lateral__compartir {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--e-2);
		margin-top: var(--e-2);
	}

	.lateral__compartir :global(.ui-boton) {
		padding-left: 0;
	}

	.compartir__nota {
		margin: 0;
		font-size: var(--texto-xs);
		line-height: 1.4;
		color: var(--tinta-tenue);
	}

	.compartir__copia {
		width: 100%;
		margin-top: var(--e-3);
	}

	/* ---------- Lateral ---------- */

	.lateral {
		grid-area: compra;
	}

	.lateral__cuerpo {
		display: flex;
		flex-direction: column;
		padding: var(--e-5) var(--e-5) var(--e-4);
	}

	.compra {
		display: flex;
		flex-direction: column;
		gap: var(--e-1);
	}

	.compra__cabecera {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-2);
	}

	.compra__rotulo {
		margin: 0;
		font-size: var(--texto-sm);
		font-weight: 600;
		color: var(--tinta-suave);
	}

	.compra__descuento {
		display: inline-flex;
		padding: 0.1rem 0.55rem;
		border-radius: var(--radio-full);
		background: var(--marca);
		color: #fff;
		font-size: var(--texto-xs);
		font-weight: 700;
	}

	.compra__precio {
		margin: 0;
		font-family: var(--fuente-display);
		font-size: clamp(2rem, 3vw, 2.5rem);
		font-weight: 800;
		line-height: 1.05;
		letter-spacing: -0.03em;
		font-variant-numeric: tabular-nums;
	}

	.compra__detalle,
	.compra__antes {
		margin: 0;
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.compra__antes s {
		color: var(--tinta-suave);
	}

	.compra__condiciones {
		margin: var(--e-3) 0 0;
		padding-top: var(--e-3);
		border-top: 1px solid var(--linea);
		font-size: var(--texto-xs);
		line-height: 1.45;
		color: var(--tinta-suave);
	}

	.lateral__acciones {
		display: flex;
		flex-direction: column;
		gap: var(--e-3);
		margin-top: var(--e-4);
	}

	.lateral__acciones:empty {
		display: none;
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

	/* ---------- Barra fija de acción ---------- */

	.barra-fija {
		position: fixed;
		bottom: var(--e-4);
		left: 50%;
		z-index: 20;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-3);
		width: min(calc(100% - 2rem), 56rem);
		padding: var(--e-3) var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--fondo);
		box-shadow: var(--sombra-md);
		translate: -50% 0;
	}

	.barra-fija__precio {
		display: flex;
		flex-direction: column;
		line-height: 1.15;
	}

	.barra-fija__valor {
		font-family: var(--fuente-display);
		font-size: var(--texto-md);
		font-weight: 800;
		font-variant-numeric: tabular-nums;
	}

	.barra-fija__unidad {
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
	}

	@media (max-width: 1150px) {
		.encabezado {
			grid-template-columns: 1fr;
			gap: var(--e-6);
		}
	}

	@media (max-width: 900px) {
		.detalle {
			grid-template-columns: 1fr;
			grid-template-areas:
				'hero'
				'compra'
				'cuerpo';
			gap: var(--e-6);
		}

		.barra-fija {
			inset: auto 0 0;
			width: auto;
			padding: var(--e-3) var(--e-4) calc(var(--e-3) + env(safe-area-inset-bottom));
			border-right: 0;
			border-bottom: 0;
			border-left: 0;
			border-radius: 0;
			box-shadow: none;
			translate: 0;
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
