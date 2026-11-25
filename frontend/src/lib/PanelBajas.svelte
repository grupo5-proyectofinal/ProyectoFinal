<script>
	import { api, fieldErrors } from '$lib/api.js';
	import { accionesBaja, etiquetaBaja, hayBajas, puedePedirBaja } from '$lib/bajas.js';
	import { confirmar } from '$lib/confirmacion.svelte.js';
	import { moneda } from '$lib/formato.js';
	import { fechaHora } from '$lib/historial.js';
	import { notificar } from '$lib/toast.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';

	// Baja con devolución: el integrante que ya pagó pide salir, el administrador
	// la resuelve y la devolución se coordina fuera de la app (acá se registra).
	let { pool, usuarioId, miembro = null, onactualizar } = $props();

	let solicitudes = $state([]);
	let motivo = $state('');
	let motivoRechazo = $state({});
	let formularioAbierto = $state(false);
	let rechazando = $state(null);
	let ocupado = $state('');
	let errores = $state({});
	let pedido = 0;

	const esCreador = $derived(pool.creador?.id === usuarioId);
	const puedePedir = $derived(puedePedirBaja(pool, miembro, solicitudes));

	// Se recarga al cambiar de pool, de estado o de integrantes.
	$effect(() => {
		pool.id;
		pool.estado;
		pool.miembros?.length;
		cargar();
	});

	async function cargar() {
		const actual = ++pedido;
		try {
			const r = await api(`/pools/${pool.id}/bajas/`);
			if (actual === pedido) solicitudes = r.results ?? [];
		} catch {
			if (actual === pedido) solicitudes = [];
		}
	}

	async function ejecutar(clave, ruta, body, mensaje) {
		if (ocupado) return;
		ocupado = clave;
		errores = {};
		try {
			await api(`/pools/${pool.id}/${ruta}`, { method: 'POST', ...(body ? { body } : {}) });
			notificar(mensaje);
			await cargar();
			await onactualizar?.();
			return true;
		} catch (e) {
			errores = fieldErrors(e.data);
			return false;
		} finally {
			ocupado = '';
		}
	}

	async function pedir() {
		const ok = await ejecutar('pedir', 'bajas/', { motivo }, 'Pedido de baja enviado.');
		if (ok) {
			motivo = '';
			formularioAbierto = false;
		}
	}

	async function aprobar(solicitud) {
		const aceptada = await confirmar({
			titulo: '¿Aprobar la baja?',
			descripcion: `${solicitud.usuario.username} sale del pool y vos tenés que devolverle ${moneda(solicitud.monto)} por fuera de la app. Después marcá la devolución como hecha.`,
			confirmar: 'Aprobar la baja'
		});
		if (aceptada) {
			await ejecutar(
				`resolver-${solicitud.id}`,
				`bajas/${solicitud.id}/resolver/`,
				{ accion: 'aprobar' },
				'Baja aprobada.'
			);
		}
	}

	async function rechazar(solicitud) {
		const ok = await ejecutar(
			`resolver-${solicitud.id}`,
			`bajas/${solicitud.id}/resolver/`,
			{ accion: 'rechazar', motivo: motivoRechazo[solicitud.id] ?? '' },
			'Baja rechazada.'
		);
		if (ok) rechazando = null;
	}

	const devolver = (s) =>
		ejecutar(`devolucion-${s.id}`, `bajas/${s.id}/devolucion/`, null, 'Devolución marcada como hecha.');
	const recibir = (s) =>
		ejecutar(`devolucion-${s.id}`, `bajas/${s.id}/devolucion/`, null, 'Devolución confirmada.');
</script>

{#if puedePedir || hayBajas(solicitudes)}
	<section class="bajas" aria-labelledby="bajas-titulo">
		<h3 id="bajas-titulo">{esCreador ? 'Pedidos de baja' : 'Baja con devolución'}</h3>

		{#if errores.detail}
			<Aviso variante="error">{errores.detail}</Aviso>
		{/if}

		{#each solicitudes as solicitud (solicitud.id)}
			{@const acciones = accionesBaja(solicitud, usuarioId, pool.creador?.id)}
			{@const estado = etiquetaBaja(solicitud.estado)}
			<article class="bajas__item">
				<div class="bajas__cabecera">
					<strong>{esCreador ? solicitud.usuario.username : `${solicitud.cantidad} u.`}</strong>
					<Badge variante={estado.variante}>{estado.texto}</Badge>
				</div>
				<p class="ayuda">
					{solicitud.cantidad}
					{solicitud.cantidad === 1 ? 'unidad' : 'unidades'} · {moneda(solicitud.monto)} ·
					{fechaHora(solicitud.creado)}
				</p>
				<p class="ayuda">Motivo: {solicitud.motivo}</p>
				{#if solicitud.estado === 'rechazada' && solicitud.motivo_rechazo}
					<p class="ayuda">Motivo del rechazo: {solicitud.motivo_rechazo}</p>
				{/if}
				{#if solicitud.estado === 'aprobada' && !esCreador}
					<p class="ayuda">
						Saliste del pool. El administrador te va a devolver {moneda(solicitud.monto)}.
					</p>
				{/if}

				{#if acciones.resolver}
					{#if rechazando === solicitud.id}
						<Campo
							id={`rechazo-${solicitud.id}`}
							etiqueta="Motivo del rechazo"
							error={errores.motivo}
						>
							{#snippet children(props)}
								<input
									id={`rechazo-${solicitud.id}`}
									maxlength="255"
									bind:value={motivoRechazo[solicitud.id]}
									{...props}
								/>
							{/snippet}
						</Campo>
						<div class="bajas__acciones">
							<Boton
								variante="peligro-suave"
								disabled={!!ocupado}
								onclick={() => rechazar(solicitud)}
							>
								Confirmar rechazo
							</Boton>
							<Boton variante="secundario" onclick={() => (rechazando = null)}>Volver</Boton>
						</div>
					{:else}
						<div class="bajas__acciones">
							<Boton variante="primario" disabled={!!ocupado} onclick={() => aprobar(solicitud)}>
								Aprobar
							</Boton>
							<Boton variante="secundario" onclick={() => (rechazando = solicitud.id)}>
								Rechazar
							</Boton>
						</div>
					{/if}
				{/if}
				{#if acciones.marcarDevuelta}
					<Boton variante="primario" bloque disabled={!!ocupado} onclick={() => devolver(solicitud)}>
						Ya devolví el dinero
					</Boton>
				{/if}
				{#if acciones.confirmarRecibida}
					<p class="ayuda">El administrador dice que ya te devolvió el dinero.</p>
					<Boton variante="primario" bloque disabled={!!ocupado} onclick={() => recibir(solicitud)}>
						Confirmar que lo recibí
					</Boton>
				{/if}
			</article>
		{/each}

		{#if puedePedir}
			{#if formularioAbierto}
				<Campo id="motivo-baja" etiqueta="¿Por qué querés salir?" error={errores.motivo}>
					{#snippet children(props)}
						<input id="motivo-baja" maxlength="255" bind:value={motivo} {...props} />
					{/snippet}
				</Campo>
				<p class="ayuda">
					Si el administrador la aprueba, salís del pool y te devuelve el dinero fuera de la app.
				</p>
				<div class="bajas__acciones">
					<Boton
						variante="primario"
						disabled={!!ocupado || !motivo.trim()}
						onclick={pedir}
					>
						{ocupado === 'pedir' ? 'Enviando…' : 'Pedir la baja'}
					</Boton>
					<Boton variante="secundario" onclick={() => (formularioAbierto = false)}>Volver</Boton>
				</div>
			{:else}
				<Boton variante="peligro-suave" bloque onclick={() => (formularioAbierto = true)}>
					Pedir baja y devolución
				</Boton>
			{/if}
		{/if}
	</section>
{/if}

<style>
	.bajas {
		display: grid;
		gap: var(--e-3);
		padding: var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio-m, 12px);
		background: var(--crema);
	}

	.bajas h3 {
		margin: 0;
		font-size: 1rem;
	}

	.bajas__item {
		display: grid;
		gap: var(--e-2);
		padding-bottom: var(--e-3);
		border-bottom: 1px solid var(--linea);
	}

	.bajas__cabecera {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-2);
	}

	.bajas__acciones {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
	}

	.ayuda {
		margin: 0;
		color: var(--tinta-suave);
	}
</style>
