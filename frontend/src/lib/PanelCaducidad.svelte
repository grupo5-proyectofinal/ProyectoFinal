<script>
	import {
		diasParaResponder,
		puedeExtender,
		rangoExtension,
		reconfirmacionPendiente,
		resumenReconfirmacion
	} from '$lib/caducidad.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';

	// Pool caducado (el creador extiende el plazo) y reconfirmación posterior
	// (cada participante sigue o sale). Solo avisa: el padre llama a la API.
	let { pool, usuarioId, ocupado = false, error = {}, onextender, onreconfirmar } = $props();

	const rango = rangoExtension();
	let nuevaFecha = $state('');

	const puedeExtenderPool = $derived(puedeExtender(pool, usuarioId));
	const pendiente = $derived(reconfirmacionPendiente(pool, usuarioId));
	const resumen = $derived(resumenReconfirmacion(pool));
	const dias = $derived(diasParaResponder(pool));
	const esCreador = $derived(pool.creador?.id === usuarioId);
</script>

{#if pool.estado === 'caducado'}
	<section class="caducidad" aria-labelledby="caducidad-titulo">
		<h3 id="caducidad-titulo">Este pool caducó</h3>
		{#if puedeExtenderPool}
			<p class="ayuda">
				Venció la fecha sin completar el cupo. Extendé el plazo: cada participante va a tener
				{dias || 3} días para confirmar si sigue.
			</p>
			<Campo
				id="nueva_fecha"
				etiqueta="Nueva fecha de caducidad"
				error={error.fecha_caducidad}
			>
				{#snippet children(props)}
					<input
						id="nueva_fecha"
						type="date"
						min={rango.min}
						max={rango.max}
						bind:value={nuevaFecha}
						{...props}
					/>
				{/snippet}
			</Campo>
			<Boton
				variante="primario"
				bloque
				disabled={!nuevaFecha || ocupado}
				onclick={() => onextender(nuevaFecha)}
			>
				{ocupado ? 'Extendiendo…' : 'Extender plazo'}
			</Boton>
		{:else}
			<p class="ayuda">
				Venció la fecha sin completar el cupo. El administrador puede extender el plazo o
				cancelar el pool. Mientras tanto no se pueden cargar comprobantes ni escribir en el chat.
			</p>
		{/if}
	</section>
{:else if pool.estado === 'reconfirmacion'}
	<section class="caducidad" aria-labelledby="caducidad-titulo">
		<h3 id="caducidad-titulo">Esperando confirmación</h3>
		<p class="ayuda">
			Se extendió el plazo. Respondieron {resumen.respondieron} de
			{resumen.respondieron + resumen.faltan} participantes
			{#if dias}· quedan {dias} {dias === 1 ? 'día' : 'días'}{/if}. Quien no responde queda
			afuera y se libera su reserva.
		</p>
		{#if error.detail}
			<Aviso variante="error">{error.detail}</Aviso>
		{/if}
		{#if pendiente}
			<div class="caducidad__acciones">
				<Boton variante="primario" disabled={ocupado} onclick={() => onreconfirmar(true)}>
					Sigo en el pool
				</Boton>
				<Boton variante="peligro-suave" disabled={ocupado} onclick={() => onreconfirmar(false)}>
					Salir
				</Boton>
			</div>
		{:else if !esCreador}
			<p class="ayuda">Ya respondiste. Te avisamos cuando el pool vuelva a abrirse.</p>
		{/if}
	</section>
{/if}

<style>
	.caducidad {
		display: grid;
		gap: var(--e-3);
		padding: var(--e-4);
		border: 1px solid var(--borde-alerta);
		border-radius: var(--radio-m, 12px);
		background: var(--alerta-suave);
	}

	.caducidad h3 {
		margin: 0;
		font-size: 1rem;
	}

	.ayuda {
		margin: 0;
		color: var(--tinta-suave);
	}

	.caducidad__acciones {
		display: grid;
		gap: var(--e-2);
	}
</style>
