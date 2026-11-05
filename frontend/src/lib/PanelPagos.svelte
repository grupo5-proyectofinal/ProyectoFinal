<script>
	// Pagos con comprobante y confirmación de recepción.
	// - Participante: sube el comprobante de su parte y confirma que recibió el producto.
	// - Administrador (creador): revisa cada comprobante (confirma o rechaza con motivo)
	//   y ve quién ya recibió el producto.
	// Las reglas y textos viven en `pagos.js`; acá solo se coordina la UI.
	import { tick } from 'svelte';
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
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let { pool, usuarioId, onactualizar } = $props();

	let archivo = $state(null);
	let inputArchivo = $state();
	let campoMotivo = $state();
	let vistaPrevia = $state('');
	let arrastrando = $state(false);
	let error = $state('');
	let ocupado = $state(false);
	let rechazando = $state(null); // id de la membresía cuyo rechazo se está escribiendo
	let motivo = $state('');

	const esCreador = $derived(pool.creador?.id === usuarioId);
	const mia = $derived(pool.miembros.find((m) => m.usuario.id === usuarioId) ?? null);
	const pagos = $derived(resumenPagos(pool));
	const recepcion = $derived(resumenRecepcion(pool));
	const mostrarRecepcion = $derived(pool.estado === 'en_curso' || pool.estado === 'finalizado');
	const pagosCompletos = $derived(pagos.total > 0 && pagos.confirmados === pagos.total);
	const recepcionCompleta = $derived(recepcion.total > 0 && recepcion.recibieron === recepcion.total);

	// La vista previa del comprobante elegido se libera al cambiarlo o desmontar.
	$effect(() => {
		const url = vistaPrevia;
		return () => {
			if (url) URL.revokeObjectURL(url);
		};
	});

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

	function recibirArchivo(nuevo) {
		if (!nuevo) return;
		const invalido = validarComprobante(nuevo);
		error = invalido;
		if (invalido) return;
		archivo = nuevo;
		if (vistaPrevia) URL.revokeObjectURL(vistaPrevia);
		vistaPrevia = nuevo.type.startsWith('image/') ? URL.createObjectURL(nuevo) : '';
	}

	function elegirArchivo(evento) {
		recibirArchivo(evento.currentTarget.files?.[0] ?? null);
	}

	function quitarArchivo() {
		archivo = null;
		vistaPrevia = '';
		if (inputArchivo) inputArchivo.value = '';
	}

	function soltar(evento) {
		evento.preventDefault();
		arrastrando = false;
		recibirArchivo(evento.dataTransfer?.files?.[0] ?? null);
	}

	function peso(bytes) {
		if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
			quitarArchivo();
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

	async function abrirRechazo(miembro) {
		rechazando = miembro.id;
		motivo = '';
		error = '';
		await tick();
		campoMotivo?.focus();
	}

	function rechazarPago(miembro) {
		if (!motivo.trim()) {
			error = 'Indicá el motivo del rechazo.';
			campoMotivo?.focus();
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

	const ayudaCreador = $derived(
		pool.estado === 'listo'
			? pagosCompletos
				? 'Todos los pagos están confirmados. Confirmá el pedido desde el panel lateral.'
				: 'Revisá cada comprobante. Con todos los pagos confirmados vas a poder confirmar el pedido.'
			: pool.estado === 'en_curso'
				? recepcionCompleta
					? 'Todos confirmaron la entrega. Ya podés finalizar el pool desde el panel lateral.'
					: 'Marcá quién ya recibió el producto. Con todas las entregas confirmadas vas a poder finalizar el pool.'
				: 'Registro de pagos y entregas del pool.'
	);
</script>

<section class="pagos" aria-labelledby="pagos-titulo" aria-busy={ocupado}>
	<header class="pagos__cabecera">
		<div class="pagos__intro">
			<h2 id="pagos-titulo">Pagos y entrega</h2>
			{#if esCreador || mia}
				<p class="pagos__ayuda">{esCreador ? ayudaCreador : 'Tu parte del pool y la confirmación de entrega.'}</p>
			{/if}
		</div>

		{#if esCreador}
			<div class="fases" role="group" aria-label="Progreso de pagos y entregas">
				<div class="fase" class:completa={pagosCompletos}>
					<span class="fase__rotulo">Pagos</span>
					<span class="fase__valor">
						{pagos.confirmados}<span class="fase__total">de {pagos.total}</span>
					</span>
					<progress
						class="fase__barra"
						aria-label="Pagos confirmados"
						value={pagos.confirmados}
						max={Math.max(pagos.total, 1)}
					></progress>
					{#if pagos.enviados}
						<span class="fase__nota">{pagos.enviados} por revisar</span>
					{/if}
				</div>
				{#if mostrarRecepcion}
					<div class="fase" class:completa={recepcionCompleta}>
						<span class="fase__rotulo">Entregas</span>
						<span class="fase__valor">
							{recepcion.recibieron}<span class="fase__total">de {recepcion.total}</span>
						</span>
						<progress
							class="fase__barra"
							aria-label="Entregas confirmadas"
							value={recepcion.recibieron}
							max={Math.max(recepcion.total, 1)}
						></progress>
					</div>
				{/if}
			</div>
		{/if}
	</header>

	{#if error}
		<div class="pagos__aviso">
			<Aviso variante="error">{error}</Aviso>
		</div>
	{/if}

	{#if esCreador}
		{#if pool.miembros.length}
			<ul class="cuentas">
				{#each pool.miembros as miembro (miembro.id)}
					{@const estadoPago = etiquetaEstadoPago(miembro.pago_estado)}
					<li class="cuenta" class:cuenta--rechazada={miembro.pago_estado === 'rechazado'}>
						<div class="cuenta__fila">
							<Avatar
								nombre={miembro.usuario.username}
								foto={miembro.usuario.foto}
								tamano="sm"
								aria-hidden="true"
							/>
							<div class="cuenta__quien">
								<span class="cuenta__nombre">{miembro.usuario.username}</span>
								<span class="cuenta__detalle">
									{miembro.cantidad} u.
									{#if miembro.tiene_comprobante}
										· comprobante adjunto
									{:else}
										· sin comprobante
									{/if}
								</span>
							</div>
							<span class="cuenta__monto">{moneda(monto(pool, miembro))}</span>
							<span class="cuenta__estado">
								<Badge variante={estadoPago.variante}>{estadoPago.texto}</Badge>
							</span>
						</div>

						{#if miembro.pago_estado === 'rechazado' && miembro.pago_motivo_rechazo}
							<p class="cuenta__motivo">Motivo del rechazo: {miembro.pago_motivo_rechazo}</p>
						{/if}

						{#if mostrarRecepcion}
							<p class="cuenta__entrega" class:cuenta__entrega--ok={miembro.recepcion_confirmada}>
								<svg
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
									aria-hidden="true"
								>
									{#if miembro.recepcion_confirmada}
										<path d="M20 6 9 17l-5-5" />
									{:else}
										<circle cx="12" cy="12" r="9" />
										<path d="M12 7v5l3 2" />
									{/if}
								</svg>
								{#if miembro.recepcion_confirmada}
									Recibió el producto · {fechaHora(miembro.recepcion_confirmada)}
								{:else}
									Todavía no confirmó la entrega
								{/if}
							</p>
						{/if}

						<div class="cuenta__acciones">
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
							<div class="rechazo">
								<label class="rechazo__etiqueta" for="motivo-{miembro.id}">
									Motivo del rechazo
								</label>
								<input
									id="motivo-{miembro.id}"
									bind:this={campoMotivo}
									type="text"
									maxlength="255"
									placeholder="Ej.: el monto no coincide"
									bind:value={motivo}
								/>
								<div class="rechazo__acciones">
									<Boton
										variante="peligro-suave"
										tamano="sm"
										disabled={ocupado}
										onclick={() => rechazarPago(miembro)}
									>
										Rechazar pago
									</Boton>
									<Boton
										variante="ghost"
										tamano="sm"
										onclick={() => {
											rechazando = null;
											error = '';
										}}
									>
										Cancelar
									</Boton>
								</div>
							</div>
						{/if}
					</li>
				{/each}
			</ul>
		{:else}
			<p class="pagos__vacio">No hay otros participantes: no hay pagos para revisar.</p>
		{/if}
	{:else if mia}
		{@const estadoPago = etiquetaEstadoPago(mia.pago_estado)}
		<Tarjeta>
			<div class="mia__resumen">
				<div class="mia__cuenta">
					<p class="mia__rotulo">Tu parte</p>
					<p class="mia__monto">{moneda(monto(pool, mia))}</p>
					<p class="mia__detalle">
						{mia.cantidad}
						{mia.cantidad === 1 ? 'unidad' : 'unidades'} de {moneda(pool.precio_unitario)}
					</p>
				</div>
				<Badge variante={estadoPago.variante}>{estadoPago.texto}</Badge>
			</div>

			<div class="mia__cuerpo">
				{#if mia.pago_estado === 'rechazado'}
					<Aviso variante="error">
						El administrador rechazó tu comprobante. Subí uno nuevo.
						{#if mia.pago_motivo_rechazo}<br />Motivo: {mia.pago_motivo_rechazo}{/if}
					</Aviso>
				{:else if mia.pago_estado === 'enviado'}
					<p class="mia__estado">
						<svg
							width="18"
							height="18"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<circle cx="12" cy="12" r="9" />
							<path d="M12 7v5l3 2" />
						</svg>
						Esperando que el administrador revise tu comprobante.
					</p>
				{:else if mia.pago_estado === 'confirmado'}
					<p class="mia__estado mia__estado--ok">
						<svg
							width="18"
							height="18"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
						>
							<path d="M20 6 9 17l-5-5" />
						</svg>
						El administrador confirmó que recibió tu pago.
					</p>
				{:else if pool.estado === 'listo'}
					<p class="mia__estado">Transferí tu parte al administrador del pool y subí el comprobante.</p>
				{/if}

				{#if mia.tiene_comprobante}
					<div class="mia__comprobante">
						<span class="mia__archivo">Comprobante enviado</span>
						<Boton variante="ghost" tamano="sm" onclick={() => verComprobante(mia)}>
							Ver mi comprobante
						</Boton>
					</div>
				{/if}

				{#if puedeSubirComprobante(pool, mia)}
					<div class="subida">
						<p class="subida__titulo">
							{mia.tiene_comprobante ? 'Reemplazar comprobante' : 'Comprobante de transferencia'}
						</p>

						<div
							class="comprobante"
							class:comprobante--arrastrando={arrastrando}
							role="group"
							aria-label="Comprobante de transferencia"
							ondragover={(e) => {
								e.preventDefault();
								arrastrando = true;
							}}
							ondragleave={() => (arrastrando = false)}
							ondrop={soltar}
						>
							<label class="comprobante__zona" for="comprobante">
								<input
									id="comprobante"
									class="comprobante__input"
									type="file"
									accept="image/jpeg,image/png,application/pdf"
									bind:this={inputArchivo}
									onchange={elegirArchivo}
								/>
								{#if vistaPrevia}
									<img class="comprobante__vista" src={vistaPrevia} alt="" decoding="async" />
								{:else}
									<span class="comprobante__icono" aria-hidden="true">
										<svg
											width="22"
											height="22"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.8"
											stroke-linecap="round"
											stroke-linejoin="round"
										>
											<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
											<path d="M14 2v6h6M8 13h8M8 17h5" />
										</svg>
									</span>
								{/if}
								<span class="comprobante__texto">
									<span class="comprobante__nombre">
										{archivo ? archivo.name : 'Arrastrá el comprobante o elegí un archivo'}
									</span>
									<span class="comprobante__meta">
										{archivo
											? `${peso(archivo.size)} · ${archivo.type === 'application/pdf' ? 'PDF' : 'Imagen'}`
											: 'JPEG, PNG o PDF · hasta 5 MB'}
									</span>
								</span>
								<span class="comprobante__accion">{archivo ? 'Cambiar' : 'Elegir archivo'}</span>
							</label>

							{#if archivo}
								<Boton variante="ghost" tamano="sm" onclick={quitarArchivo}>Quitar</Boton>
							{/if}
						</div>

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
			</div>
		</Tarjeta>

		{#if mostrarRecepcion}
			<div class="entrega" class:entrega--ok={mia.recepcion_confirmada}>
				<span class="entrega__icono" aria-hidden="true">
					<svg
						width="22"
						height="22"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.8"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						{#if mia.recepcion_confirmada}
							<path d="M20 6 9 17l-5-5" />
						{:else}
							<path d="m21 8-9-5-9 5v8l9 5 9-5Z" />
							<path d="m3 8 9 5 9-5M12 13v8" />
						{/if}
					</svg>
				</span>
				<div class="entrega__texto">
					<p class="entrega__titulo">Entrega</p>
					{#if mia.recepcion_confirmada}
						<p class="entrega__detalle">
							Confirmaste que recibiste el producto · {fechaHora(mia.recepcion_confirmada)}
						</p>
					{:else if puedeConfirmarRecepcion(pool, mia)}
						<p class="entrega__detalle">
							Cuando tengas el producto en mano, confirmalo. El pool se cierra cuando todos lo
							confirman.
						</p>
					{:else}
						<p class="entrega__detalle">La entrega se confirma cuando el pool está en curso.</p>
					{/if}
				</div>
				{#if !mia.recepcion_confirmada && puedeConfirmarRecepcion(pool, mia)}
					<Boton variante="primario" onclick={confirmarRecepcion} disabled={ocupado}>
						Confirmar que recibí el producto
					</Boton>
				{/if}
			</div>
		{/if}
	{/if}
</section>

<style>
	/* Remito: una sola superficie con renglones, en vez de una tarjeta por pago. */
	.pagos {
		margin-top: var(--e-7);
		padding-top: var(--e-5);
		border-top: 1px solid var(--linea);
	}

	.pagos__cabecera {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--e-4);
		margin-bottom: var(--e-5);
	}

	.pagos__intro {
		min-width: 0;
		max-width: 52ch;
	}

	.pagos h2 {
		margin: 0;
		font-size: var(--texto-lg);
	}

	.pagos__ayuda {
		margin: var(--e-2) 0 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	/* ---------- Fases (secuencia pago → entrega) ---------- */

	.fases {
		display: flex;
		align-items: stretch;
		gap: var(--e-5);
	}

	.fase {
		display: flex;
		flex-direction: column;
		gap: var(--e-1);
		min-width: 7.5rem;
		padding-left: var(--e-4);
		border-left: 2px solid var(--linea);
	}

	.fase.completa {
		border-left-color: var(--exito);
	}

	.fase__rotulo {
		font-size: var(--texto-xs);
		font-weight: 600;
		color: var(--tinta-suave);
	}

	.fase__valor {
		font-family: var(--fuente-display);
		font-size: var(--texto-md);
		font-weight: 800;
		font-variant-numeric: tabular-nums;
		letter-spacing: -0.01em;
		color: var(--tinta);
	}

	.fase__total {
		margin-left: 0.25em;
		font-size: var(--texto-sm);
		font-weight: 500;
		color: var(--tinta-suave);
		letter-spacing: 0;
	}

	.fase__barra {
		appearance: none;
		-webkit-appearance: none;
		width: 100%;
		height: 4px;
		margin-top: var(--e-1);
		border: 0;
		border-radius: var(--radio-full);
		background: var(--melocoton-fuerte);
		overflow: hidden;
	}

	.fase__barra::-webkit-progress-bar {
		background: var(--melocoton-fuerte);
	}

	.fase__barra::-webkit-progress-value {
		background: var(--alerta);
		border-radius: var(--radio-full);
		transition: width 300ms cubic-bezier(0.2, 0.6, 0.3, 1);
	}

	.fase__barra::-moz-progress-bar {
		background: var(--alerta);
		border-radius: var(--radio-full);
	}

	.fase.completa .fase__barra::-webkit-progress-value {
		background: var(--exito);
	}

	.fase.completa .fase__barra::-moz-progress-bar {
		background: var(--exito);
	}

	.fase__nota {
		font-size: var(--texto-xs);
		color: var(--alerta);
	}

	.pagos__aviso {
		margin-bottom: var(--e-4);
	}

	/* ---------- Libro de cuentas (administrador) ---------- */

	.cuentas {
		margin: 0;
		padding: 0;
		list-style: none;
		border-top: 1px solid var(--linea);
	}

	.cuenta {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		padding: var(--e-4) 0;
		border-bottom: 1px solid var(--linea);
	}

	.cuenta__fila {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2) var(--e-3);
		min-width: 0;
	}

	.cuenta__quien {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
		min-width: 0;
	}

	.cuenta__nombre {
		font-weight: 600;
		overflow-wrap: anywhere;
	}

	.cuenta__detalle {
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.cuenta__monto {
		margin-left: auto;
		font-size: var(--texto-md);
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}

	.cuenta--rechazada .cuenta__monto {
		color: var(--tinta-suave);
	}

	.cuenta__estado {
		display: flex;
	}

	.cuenta__motivo {
		margin: 0;
		padding-left: calc(1.75rem + var(--e-3));
		font-size: var(--texto-sm);
		color: var(--texto-peligro);
	}

	.cuenta__entrega {
		display: flex;
		align-items: center;
		gap: var(--e-2);
		margin: 0;
		padding-left: calc(1.75rem + var(--e-3));
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.cuenta__entrega svg {
		flex: none;
		color: var(--tinta-tenue);
	}

	.cuenta__entrega--ok {
		color: var(--texto-exito);
	}

	.cuenta__entrega--ok svg {
		color: var(--exito);
	}

	.cuenta__acciones {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
		padding-left: calc(1.75rem + var(--e-3));
	}

	.cuenta__acciones:empty {
		display: none;
	}

	.rechazo {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		margin-left: calc(1.75rem + var(--e-3));
		padding: var(--e-3) var(--e-4);
		border-left: 2px solid var(--borde-peligro-fuerte);
		background: var(--peligro-suave);
		border-radius: 0 var(--radio-sm) var(--radio-sm) 0;
	}

	.rechazo__etiqueta {
		font-size: var(--texto-xs);
		font-weight: 600;
		color: var(--texto-peligro);
	}

	.rechazo input {
		background: var(--superficie);
	}

	.rechazo__acciones {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
	}

	.pagos__vacio {
		margin: 0;
		padding: var(--e-5) 0;
		color: var(--tinta-suave);
	}

	/* ---------- Tu parte (participante) ---------- */

	.mia__resumen {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--e-3);
		padding: var(--e-5);
		border-bottom: 1px solid var(--linea);
		border-radius: calc(var(--radio) - 1px) calc(var(--radio) - 1px) 0 0;
		background: var(--crema);
	}

	.mia__cuenta {
		display: flex;
		flex-direction: column;
		gap: var(--e-1);
		min-width: 0;
	}

	.mia__rotulo {
		margin: 0;
		font-size: var(--texto-sm);
		font-weight: 600;
		color: var(--tinta-suave);
	}

	.mia__monto {
		margin: 0;
		font-family: var(--fuente-display);
		font-size: clamp(1.9rem, 3vw, 2.4rem);
		font-weight: 800;
		line-height: 1.05;
		letter-spacing: -0.03em;
		font-variant-numeric: tabular-nums;
	}

	.mia__detalle {
		margin: 0 0 var(--e-2);
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
	}

	.mia__cuerpo {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
		min-width: 0;
		padding: var(--e-5);
	}

	.mia__estado {
		display: flex;
		align-items: flex-start;
		gap: var(--e-2);
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.mia__estado svg {
		flex: none;
		margin-top: 0.1em;
		color: var(--alerta);
	}

	.mia__estado--ok {
		color: var(--texto-exito);
	}

	.mia__estado--ok svg {
		color: var(--exito);
	}

	.mia__comprobante {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-2);
		padding: var(--e-2) 0;
		border-top: 1px solid var(--linea);
		border-bottom: 1px solid var(--linea);
	}

	.mia__archivo {
		font-size: var(--texto-sm);
		font-weight: 600;
		color: var(--tinta-suave);
	}

	/* ---------- Subida del comprobante ---------- */

	.subida {
		display: flex;
		flex-direction: column;
		gap: var(--e-3);
	}

	.subida__titulo {
		margin: 0;
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.comprobante {
		display: flex;
		align-items: center;
		gap: var(--e-2);
		border: 1.5px dashed var(--linea-control);
		border-radius: var(--radio-sm);
		background: var(--superficie);
		transition:
			border-color var(--transicion),
			background-color var(--transicion);
	}

	.comprobante:hover,
	.comprobante--arrastrando {
		border-color: var(--marca);
		background: var(--crema);
	}

	.comprobante__zona {
		display: flex;
		flex: 1;
		align-items: center;
		gap: var(--e-3);
		min-width: 0;
		padding: var(--e-3);
		cursor: pointer;
	}

	.comprobante__zona:focus-within {
		outline: 2px solid var(--acento);
		outline-offset: 2px;
		border-radius: var(--radio-sm);
	}

	.comprobante__input {
		position: absolute;
		width: 1px;
		height: 1px;
		min-height: 0;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0 0 0 0);
		white-space: nowrap;
		border: 0;
	}

	.comprobante__icono {
		display: grid;
		place-items: center;
		flex: none;
		width: 2.5rem;
		height: 2.5rem;
		border-radius: var(--radio-sm);
		background: var(--melocoton);
		color: var(--naranja-fuerte);
	}

	.comprobante__vista {
		flex: none;
		width: 2.5rem;
		height: 2.5rem;
		border-radius: var(--radio-sm);
		object-fit: cover;
	}

	.comprobante__texto {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
		min-width: 0;
	}

	.comprobante__nombre {
		font-size: var(--texto-sm);
		font-weight: 600;
		color: var(--tinta);
		overflow-wrap: anywhere;
	}

	.comprobante__meta {
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.comprobante__accion {
		flex: none;
		margin-left: auto;
		font-size: var(--texto-xs);
		font-weight: 700;
		color: var(--marca-fuerte);
		text-decoration: underline;
		text-underline-offset: 0.2em;
	}

	.comprobante > :global(.ui-boton) {
		margin-right: var(--e-2);
	}

	/* ---------- Entrega (participante) ---------- */

	.entrega {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3);
		margin-top: var(--e-4);
		padding: var(--e-4) var(--e-5);
		border: 1px solid var(--linea);
		border-left: 3px solid var(--alerta);
		border-radius: var(--radio-sm);
		background: var(--superficie);
	}

	.entrega--ok {
		border-left-color: var(--exito);
		background: var(--exito-suave);
	}

	.entrega__icono {
		display: grid;
		place-items: center;
		flex: none;
		width: 2.5rem;
		height: 2.5rem;
		border-radius: 50%;
		background: var(--alerta-suave);
		color: var(--alerta);
	}

	.entrega--ok .entrega__icono {
		background: var(--superficie);
		color: var(--exito);
	}

	.entrega__texto {
		flex: 1;
		min-width: 12rem;
	}

	.entrega__titulo {
		margin: 0;
		font-family: var(--fuente-display);
		font-size: var(--texto-base);
		font-weight: 700;
	}

	.entrega__detalle {
		margin: 0.1rem 0 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.entrega--ok .entrega__detalle {
		color: var(--texto-exito);
	}

	/* ---------- Adaptación a pantallas chicas ---------- */

	@media (max-width: 700px) {
		.pagos__cabecera {
			align-items: flex-start;
		}

		.fases {
			gap: var(--e-4);
			width: 100%;
		}

		.fase {
			flex: 1;
			min-width: 0;
		}

		.cuenta__fila {
			display: grid;
			grid-template-columns: auto minmax(0, 1fr) auto;
			column-gap: var(--e-3);
			row-gap: var(--e-1);
		}

		.cuenta__quien {
			grid-column: 2;
		}

		.cuenta__monto {
			grid-column: 3;
			margin-left: 0;
			font-size: var(--texto-base);
		}

		.cuenta__estado {
			grid-column: 2;
			justify-self: start;
		}

		.mia__resumen {
			padding: var(--e-4);
		}

		.mia__cuerpo {
			padding: var(--e-4);
		}

		.cuenta__acciones,
		.cuenta__entrega,
		.cuenta__motivo {
			padding-left: 0;
		}

		.rechazo {
			margin-left: 0;
		}

		.comprobante__accion {
			display: none;
		}
	}

	@media (max-width: 480px) {
		.entrega {
			align-items: flex-start;
		}

		.entrega :global(.ui-boton) {
			width: 100%;
		}
	}
</style>
