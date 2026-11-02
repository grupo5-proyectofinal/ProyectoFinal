<script>
	// Pagos con comprobante y confirmación de recepción.
	// - Participante: sube el comprobante de su parte y confirma que recibió el producto.
	// - Administrador (creador): revisa cada comprobante (confirma o rechaza con motivo)
	//   y ve quién ya recibió el producto.
	// Las reglas y textos viven en `pagos.js`; acá solo se coordina la UI.
	import { api, apiBlob, fieldErrors } from '$lib/api.js';
	import { mensajeError } from '$lib/eliminacion.js';
	import { fechaHora } from '$lib/historial.js';
	import { moneda } from '$lib/formato.js';
	import {
		etiquetaEstadoPago,
		monto,
		puedeConfirmarRecepcion,
		puedeSubirComprobante,
		resumenPagos,
		resumenRecepcion,
		validarComprobante
	} from '$lib/pagos.js';
	import { notificar } from '$lib/toast.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Avatar from '$lib/ui/Avatar.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';

	let { pool, usuarioId, onactualizar } = $props();

	let archivo = $state(null);
	let inputArchivo = $state();
	let error = $state('');
	let ocupado = $state(false);
	let rechazando = $state(null); // id de la membresía cuyo rechazo se está escribiendo
	let motivo = $state('');

	const esCreador = $derived(pool.creador?.id === usuarioId);
	const mia = $derived(pool.miembros.find((m) => m.usuario.id === usuarioId) ?? null);
	const pagos = $derived(resumenPagos(pool));
	const recepcion = $derived(resumenRecepcion(pool));
	const mostrarRecepcion = $derived(pool.estado === 'en_curso' || pool.estado === 'finalizado');

	async function ejecutar(accion, exito) {
		error = '';
		ocupado = true;
		try {
			await accion();
			notificar(exito);
			await onactualizar?.();
		} catch (e) {
			const errores = fieldErrors(e.data);
			error = errores.comprobante || errores.motivo || errores.accion || mensajeError(e);
		} finally {
			ocupado = false;
		}
	}

	function elegirArchivo(evento) {
		archivo = evento.currentTarget.files?.[0] ?? null;
		error = archivo ? validarComprobante(archivo) : '';
	}

	function enviarComprobante() {
		const invalido = validarComprobante(archivo);
		if (invalido) {
			error = invalido;
			return;
		}
		const datos = new FormData();
		datos.append('comprobante', archivo);
		return ejecutar(async () => {
			await api(`/pools/${pool.id}/comprobante/`, { method: 'POST', form: true, body: datos });
			archivo = null;
			if (inputArchivo) inputArchivo.value = '';
		}, 'Comprobante enviado. El administrador lo va a revisar.');
	}

	function confirmarRecepcion() {
		return ejecutar(
			() => api(`/pools/${pool.id}/recepcion/`, { method: 'POST' }),
			'Confirmaste que recibiste el producto.'
		);
	}

	function confirmarPago(miembro) {
		return ejecutar(
			() =>
				api(`/pools/${pool.id}/miembros/${miembro.id}/pago/`, {
					method: 'POST',
					body: { accion: 'confirmar' }
				}),
			`Pago de ${miembro.usuario.username} confirmado.`
		);
	}

	function abrirRechazo(miembro) {
		rechazando = miembro.id;
		motivo = '';
		error = '';
	}

	function rechazarPago(miembro) {
		if (!motivo.trim()) {
			error = 'Indicá el motivo del rechazo.';
			return;
		}
		return ejecutar(async () => {
			await api(`/pools/${pool.id}/miembros/${miembro.id}/pago/`, {
				method: 'POST',
				body: { accion: 'rechazar', motivo: motivo.trim() }
			});
			rechazando = null;
			motivo = '';
		}, `Pago de ${miembro.usuario.username} rechazado.`);
	}

	async function verComprobante(miembro) {
		error = '';
		// La pestaña se abre antes del fetch para que el navegador no la bloquee.
		const ventana = window.open('', '_blank');
		try {
			const blob = await apiBlob(`/pools/${pool.id}/miembros/${miembro.id}/comprobante/`);
			const url = URL.createObjectURL(blob);
			if (ventana) ventana.location.href = url;
			else window.location.href = url;
			setTimeout(() => URL.revokeObjectURL(url), 60_000);
		} catch (e) {
			ventana?.close();
			error = mensajeError(e);
		}
	}
</script>

<section class="pagos" aria-labelledby="pagos-titulo">
	<div class="pagos__cabecera">
		<h2 id="pagos-titulo">Pagos y entrega</h2>
		<div class="pagos__progreso">
			<Badge variante={pagos.confirmados === pagos.total ? 'abierto' : 'neutro'}>
				{pagos.confirmados}/{pagos.total} pagos confirmados
			</Badge>
			{#if mostrarRecepcion}
				<Badge variante={recepcion.recibieron === recepcion.total ? 'abierto' : 'neutro'}>
					{recepcion.recibieron}/{recepcion.total} recibieron
				</Badge>
			{/if}
		</div>
	</div>

	{#if error}
		<Aviso variante="error">{error}</Aviso>
	{/if}

	{#if esCreador}
		{#if pool.estado === 'listo'}
			<p class="ayuda">
				Cada participante transfiere su parte y sube el comprobante. Revisá cada uno: cuando todos
				estén confirmados vas a poder confirmar el pedido.
			</p>
		{:else if pool.estado === 'en_curso'}
			<p class="ayuda">
				Cuando cada participante reciba el producto lo confirma acá. Con todas las recepciones
				confirmadas vas a poder finalizar el pool.
			</p>
		{/if}

		{#if pool.miembros.length}
			<ul class="pagos__lista">
				{#each pool.miembros as miembro (miembro.id)}
					{@const estadoPago = etiquetaEstadoPago(miembro.pago_estado)}
					<li class="pago">
						<div class="pago__fila">
							<Avatar
								nombre={miembro.usuario.username}
								foto={miembro.usuario.foto}
								tamano="sm"
								aria-hidden="true"
							/>
							<span class="pago__nombre">{miembro.usuario.username}</span>
							<span class="pago__monto">{moneda(monto(pool, miembro))}</span>
							<Badge variante={estadoPago.variante}>{estadoPago.texto}</Badge>
						</div>

						{#if miembro.pago_estado === 'rechazado' && miembro.pago_motivo_rechazo}
							<p class="pago__dato">Motivo del rechazo: {miembro.pago_motivo_rechazo}</p>
						{/if}

						{#if mostrarRecepcion}
							<p class="pago__dato">
								{miembro.recepcion_confirmada
									? `Recibió el producto · ${fechaHora(miembro.recepcion_confirmada)}`
									: 'Todavía no confirmó la recepción.'}
							</p>
						{/if}

						<div class="pago__acciones">
							{#if miembro.tiene_comprobante}
								<Boton variante="secundario" tamano="sm" onclick={() => verComprobante(miembro)}>
									Ver comprobante
								</Boton>
							{/if}
							{#if pool.estado === 'listo' && miembro.pago_estado === 'enviado'}
								<Boton
									variante="primario"
									tamano="sm"
									disabled={ocupado}
									onclick={() => confirmarPago(miembro)}
								>
									Confirmar pago
								</Boton>
								{#if rechazando !== miembro.id}
									<Boton
										variante="peligro-suave"
										tamano="sm"
										disabled={ocupado}
										onclick={() => abrirRechazo(miembro)}
									>
										Rechazar
									</Boton>
								{/if}
							{/if}
						</div>

						{#if rechazando === miembro.id}
							<div class="pago__rechazo">
								<label class="ayuda" for="motivo-{miembro.id}">Motivo del rechazo</label>
								<input
									id="motivo-{miembro.id}"
									type="text"
									maxlength="255"
									placeholder="Ej.: el monto no coincide"
									bind:value={motivo}
								/>
								<div class="pago__acciones">
									<Boton
										variante="peligro-suave"
										tamano="sm"
										disabled={ocupado}
										onclick={() => rechazarPago(miembro)}
									>
										Rechazar pago
									</Boton>
									<Boton variante="secundario" tamano="sm" onclick={() => (rechazando = null)}>
										Volver
									</Boton>
								</div>
							</div>
						{/if}
					</li>
				{/each}
			</ul>
		{:else}
			<p class="muted">No hay otros participantes: no hay pagos para revisar.</p>
		{/if}
	{:else if mia}
		{@const estadoPago = etiquetaEstadoPago(mia.pago_estado)}
		<div class="pago pago--mio">
			<div class="pago__fila">
				<span class="pago__nombre">Tu parte ({mia.cantidad} u.)</span>
				<span class="pago__monto">{moneda(monto(pool, mia))}</span>
				<Badge variante={estadoPago.variante}>{estadoPago.texto}</Badge>
			</div>

			{#if mia.pago_estado === 'rechazado'}
				<Aviso variante="error">
					El administrador rechazó tu comprobante. Subí uno nuevo.
					{#if mia.pago_motivo_rechazo}<br />Motivo: {mia.pago_motivo_rechazo}{/if}
				</Aviso>
			{:else if mia.pago_estado === 'enviado'}
				<p class="ayuda">Tu comprobante está esperando la revisión del administrador.</p>
			{:else if mia.pago_estado === 'confirmado'}
				<p class="ayuda">El administrador confirmó que recibió tu pago.</p>
			{:else if pool.estado === 'listo'}
				<p class="ayuda">
					Transferí tu parte al administrador del pool y subí el comprobante (JPEG, PNG o PDF, hasta
					5 MB).
				</p>
			{/if}

			{#if mia.tiene_comprobante}
				<div class="pago__acciones">
					<Boton variante="secundario" tamano="sm" onclick={() => verComprobante(mia)}>
						Ver mi comprobante
					</Boton>
				</div>
			{/if}

			{#if puedeSubirComprobante(pool, mia)}
				<div class="pago__subida">
					<label class="ayuda" for="comprobante">
						{mia.tiene_comprobante ? 'Reemplazar comprobante' : 'Comprobante de transferencia'}
					</label>
					<input
						id="comprobante"
						type="file"
						accept="image/jpeg,image/png,application/pdf"
						bind:this={inputArchivo}
						onchange={elegirArchivo}
					/>
					<Boton
						variante="primario"
						bloque
						disabled={ocupado || !archivo}
						onclick={enviarComprobante}
					>
						Enviar comprobante
					</Boton>
				</div>
			{/if}

			{#if mostrarRecepcion}
				{#if mia.recepcion_confirmada}
					<p class="ayuda">
						Confirmaste que recibiste el producto · {fechaHora(mia.recepcion_confirmada)}
					</p>
				{:else if puedeConfirmarRecepcion(pool, mia)}
					<p class="ayuda">
						Cuando tengas el producto en mano, confirmalo. El pool se cierra cuando todos lo
						confirman.
					</p>
					<Boton variante="primario" bloque disabled={ocupado} onclick={confirmarRecepcion}>
						Confirmar que recibí el producto
					</Boton>
				{/if}
			{/if}
		</div>
	{/if}
</section>

<style>
	/* Mismo ritmo que los `.bloque` de la página del pool. */
	.pagos {
		margin-top: var(--e-7);
		padding-top: var(--e-5);
		border-top: 1px solid var(--linea);
	}

	.pagos h2 {
		font-size: var(--texto-lg);
	}

	.pagos__cabecera {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-3);
		margin-bottom: var(--e-4);
	}

	.pagos__cabecera h2 {
		margin: 0;
	}

	.pagos__progreso {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
	}

	.pagos__lista {
		display: flex;
		flex-direction: column;
		gap: var(--e-3);
		margin: var(--e-3) 0 0;
		padding: 0;
		list-style: none;
	}

	.pago {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		padding: var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--crema);
	}

	.pago__fila {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2) var(--e-3);
		min-width: 0;
	}

	.pago__nombre {
		min-width: 0;
		font-weight: 600;
		overflow-wrap: anywhere;
	}

	.pago__monto {
		margin-left: auto;
		font-variant-numeric: tabular-nums;
		font-weight: 600;
	}

	.pago__dato {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
		overflow-wrap: anywhere;
	}

	.pago__acciones {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
	}

	.pago__acciones:empty {
		display: none;
	}

	.pago__rechazo,
	.pago__subida {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
	}

	.pago__rechazo input,
	.pago__subida input {
		width: 100%;
		min-width: 0;
	}
</style>
