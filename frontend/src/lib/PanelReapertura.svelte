<script>
	import { rangoReapertura } from '$lib/caducidad.js';
	import { puedeDuplicar, puedeReabrir } from '$lib/estados.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';

	// Pool cancelado o finalizado: el creador lo reabre (si nadie había reservado) o lo
	// duplica como borrador. Solo avisa: el padre llama a la API.
	let { pool, usuarioId, ocupado = false, error = {}, onreabrir, onduplicar } = $props();

	const rango = rangoReapertura();
	let nuevaFecha = $state('');

	const reabrible = $derived(puedeReabrir(pool, usuarioId));
	const duplicable = $derived(puedeDuplicar(pool, usuarioId));
</script>

{#if reabrible || duplicable}
	<section class="reapertura" aria-labelledby="reapertura-titulo">
		<h3 id="reapertura-titulo">
			{pool.estado === 'cancelado' ? '¿Querés volver a intentarlo?' : '¿Querés repetir esta compra?'}
		</h3>
		{#if error.detail}
			<Aviso variante="error">{error.detail}</Aviso>
		{/if}
		{#if reabrible}
			<p class="ayuda">
				Como nadie había reservado, podés reabrirlo con una nueva fecha de caducidad.
			</p>
			<Campo
				id="fecha_reapertura"
				etiqueta="Nueva fecha de caducidad"
				ayuda="Hasta 30 días desde hoy."
				error={error.fecha_caducidad}
			>
				{#snippet children(props)}
					<input
						id="fecha_reapertura"
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
				onclick={() => onreabrir(nuevaFecha)}
			>
				{ocupado === 'reabrir' ? 'Reabriendo…' : 'Reabrir pool'}
			</Boton>
		{:else if pool.estado === 'cancelado'}
			<p class="ayuda">
				Este pool ya tuvo integrantes, así que no se reabre. Duplicalo para empezar de nuevo con
				los mismos datos.
			</p>
		{/if}
		{#if duplicable}
			<Boton variante="secundario" bloque disabled={!!ocupado} onclick={onduplicar}>
				{ocupado === 'duplicar' ? 'Duplicando…' : 'Duplicar como borrador'}
			</Boton>
			<p class="ayuda">
				Se crea un borrador con los mismos datos y sin integrantes: lo revisás y lo publicás.
			</p>
		{/if}
	</section>
{/if}

<style>
	.reapertura {
		display: grid;
		gap: var(--e-3);
		padding: var(--e-4);
		border: 1px solid var(--borde);
		border-radius: var(--radio-m, 12px);
		background: var(--superficie-2, var(--superficie));
	}

	.reapertura h3 {
		margin: 0;
		font-size: 1rem;
	}

	.ayuda {
		margin: 0;
		color: var(--tinta-suave);
	}
</style>
