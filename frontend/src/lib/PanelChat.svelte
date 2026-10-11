<script>
	import { tick, untrack } from 'svelte';
	import { api } from '$lib/api.js';
	import {
		INTERVALO_CHAT,
		LIMITE_INICIAL,
		avisoEscritura,
		cursorMensajes,
		fusionarMensajes,
		puedeEnviar
	} from '$lib/chat.js';
	import { mensajeError } from '$lib/eliminacion.js';
	import { tonoNombre } from '$lib/estados.js';
	import { iniciales } from '$lib/formato.js';
	import { fechaHora } from '$lib/historial.js';

	let { poolId, estado, usuarioId } = $props();

	// Tope de lotes de la carga inicial (200 mensajes por lote).
	const MAX_LOTES = 5;

	let mensajes = $state([]);
	let borrador = $state('');
	let cargando = $state(true);
	let errorCarga = $state('');
	let errorEnvio = $state('');
	let enviando = $state(false);
	let lista = $state(null);

	// Identifica la corrida vigente del pool actual: un fetch en vuelo que
	// resuelve después de cambiar de pool (o de desmontar) no toca el estado.
	let generacion = 0;

	const bloqueado = $derived(avisoEscritura(estado));
	const avisoCarga = $derived(errorCarga ? `${errorCarga} Reintentamos en unos segundos.` : '');
	const puedeMandar = $derived(!bloqueado && !enviando && puedeEnviar(borrador));

	$effect(() => {
		const id = poolId;
		const mia = ++generacion;
		mensajes = [];
		borrador = '';
		enviando = false;
		errorCarga = '';
		errorEnvio = '';
		cargando = true;
		untrack(() => cargarInicial(id, mia));

		// Un único intervalo por vista; sin pedidos con la pestaña oculta.
		const intervalo = setInterval(() => {
			if (!document.hidden) consultar(id, mia);
		}, INTERVALO_CHAT);
		const alVolver = () => {
			if (!document.hidden) consultar(id, mia);
		};
		document.addEventListener('visibilitychange', alVolver);

		return () => {
			clearInterval(intervalo);
			document.removeEventListener('visibilitychange', alVolver);
		};
	});

	async function cargarInicial(id, mia) {
		try {
			let datos = await api(`/pools/${id}/mensajes/`, {
				query: { desde: 0, limit: LIMITE_INICIAL }
			});
			let lote = datos.results;
			// `desde` devuelve desde el principio: con `hay_mas` se avanza hasta la cola.
			for (let i = 1; datos.hay_mas && i < MAX_LOTES; i++) {
				datos = await api(`/pools/${id}/mensajes/`, {
					query: { desde: cursorMensajes(lote), limit: LIMITE_INICIAL }
				});
				lote = fusionarMensajes(lote, datos.results);
			}
			if (mia !== generacion) return;
			errorCarga = '';
			mensajes = lote;
			await desplazarAlFinal();
		} catch (e) {
			if (mia === generacion) errorCarga = mensajeError(e);
		} finally {
			if (mia === generacion) cargando = false;
		}
	}

	async function consultar(id, mia) {
		try {
			const datos = await api(`/pools/${id}/mensajes/`, {
				query: { desde: cursorMensajes(mensajes) }
			});
			if (mia !== generacion) return;
			errorCarga = '';
			if (!datos.results.length) return;
			const estabaCerca = cercaDelFondo();
			mensajes = fusionarMensajes(mensajes, datos.results);
			if (estabaCerca) await desplazarAlFinal();
		} catch (e) {
			if (mia === generacion) errorCarga = mensajeError(e);
		}
	}

	async function enviar(event) {
		event.preventDefault();
		const texto = borrador.trim();
		const mia = generacion;
		if (bloqueado || enviando || !puedeEnviar(texto)) return;
		enviando = true;
		errorEnvio = '';
		try {
			const creado = await api(`/pools/${poolId}/mensajes/`, {
				method: 'POST',
				body: { texto }
			});
			if (mia !== generacion) return;
			mensajes = fusionarMensajes(mensajes, [creado]);
			borrador = '';
			await desplazarAlFinal();
		} catch (e) {
			if (mia === generacion) errorEnvio = mensajeError(e);
		} finally {
			if (mia === generacion) enviando = false;
		}
	}

	function cercaDelFondo() {
		return !lista || lista.scrollHeight - lista.scrollTop - lista.clientHeight < 60;
	}

	async function desplazarAlFinal() {
		await tick();
		if (lista) lista.scrollTop = lista.scrollHeight;
	}
</script>

<section class="bloque">
	<h2>Chat del pool</h2>
	<div class="chat">
		{#if cargando && !mensajes.length}
			<p class="muted">Cargando los mensajes…</p>
		{:else if mensajes.length}
			<ol class="chat__lista" role="log" aria-label="Mensajes del chat" bind:this={lista}>
				{#each mensajes as mensaje (mensaje.id)}
					<li
						class="chat__item tono-{tonoNombre(mensaje.autor?.username)}"
						class:propio={mensaje.autor?.id === usuarioId}
					>
						<span class="avatar avatar--sm" aria-hidden="true">
							{#if mensaje.autor?.foto}
								<img src={mensaje.autor.foto} alt="" width="28" height="28" loading="lazy" />
							{:else}
								{iniciales(mensaje.autor?.username)}
							{/if}
						</span>
						<div class="chat__cuerpo">
							<p class="chat__meta">
								<span class="chat__autor">
									{mensaje.autor?.id === usuarioId ? 'Vos' : mensaje.autor?.username}
								</span>
								<span class="chat__fecha">{fechaHora(mensaje.creado)}</span>
							</p>
							<p class="chat__texto">{mensaje.texto}</p>
						</div>
					</li>
				{/each}
			</ol>
		{:else if avisoCarga}
			<p class="muted">{avisoCarga}</p>
		{:else}
			<p class="muted">Todavía no hay mensajes. Escribí el primero.</p>
		{/if}

		{#if avisoCarga && mensajes.length}
			<p class="chat__aviso" role="status">{avisoCarga}</p>
		{/if}

		{#if bloqueado}
			<p class="chat__aviso" role="status">{bloqueado}</p>
		{:else}
			<form class="chat__form" onsubmit={enviar}>
				<div class="campo">
					<label for="chat-texto">Tu mensaje</label>
					<textarea
						id="chat-texto"
						name="texto"
						rows="2"
						maxlength="1000"
						placeholder="Escribí un mensaje…"
						bind:value={borrador}
					></textarea>
				</div>
				<button class="btn btn--primario btn--bloque" type="submit" disabled={!puedeMandar}>
					{enviando ? 'Enviando…' : 'Enviar mensaje'}
				</button>
				{#if errorEnvio}
					<p class="error" role="alert">{errorEnvio}</p>
				{/if}
			</form>
		{/if}
	</div>
</section>

<style>
	.chat {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
	}

	.chat__lista {
		display: flex;
		flex-direction: column;
		gap: var(--e-3);
		margin: 0;
		padding: var(--e-4);
		max-height: min(24rem, 60vh);
		overflow-y: auto;
		list-style: none;
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--superficie-alt);
	}

	.chat__item {
		display: flex;
		align-items: flex-start;
		gap: var(--e-3);
	}

	.chat__cuerpo {
		min-width: 0;
		padding: var(--e-3) var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
		background: var(--superficie);
	}

	.chat__item.propio .chat__cuerpo {
		border-color: var(--t-t);
		background: var(--t-t);
	}

	.chat__meta {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-1) var(--e-3);
		margin: 0 0 var(--e-1);
		font-size: var(--texto-xs);
	}

	.chat__autor {
		font-weight: 600;
		color: var(--c-t);
	}

	.chat__fecha {
		color: var(--tinta-tenue);
	}

	.chat__texto {
		margin: 0;
		font-size: var(--texto-sm);
		overflow-wrap: anywhere;
		white-space: pre-line;
	}

	.chat__aviso {
		margin: 0;
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
	}

	.chat__form {
		display: flex;
		flex-direction: column;
		gap: var(--e-3);
	}

	.chat__form .campo {
		margin-bottom: 0;
	}
</style>
