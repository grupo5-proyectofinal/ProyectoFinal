<script>
	// "Calificar participantes": al finalizar el pool, cada participante puntúa
	// (1 a 5 + comentario opcional) al administrador y a los demás integrantes.
	import { resolve } from '$app/paths';
	import { api, fieldErrors } from '$lib/api.js';
	import { mensajeError } from '$lib/eliminacion.js';
	import Estrellas from '$lib/Estrellas.svelte';
	import { etiquetaRol, payloadResena, pendientesDeCalificar } from '$lib/resenas.js';
	import { notificar } from '$lib/toast.svelte.js';
	import Avatar from '$lib/ui/Avatar.svelte';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';

	let { pool, usuarioId } = $props();

	let propias = $state([]);
	let cargando = $state(true);
	let error = $state('');
	let borradores = $state({});
	let errores = $state({});
	let enviando = $state(null);

	const poolId = $derived(pool.id);
	const pendientes = $derived(pendientesDeCalificar(pool, usuarioId, propias));

	$effect(() => {
		cargar(poolId);
	});

	async function cargar(id) {
		cargando = true;
		error = '';
		try {
			propias = (await api(`/pools/${id}/resenas/`)).results;
			// Un borrador por participante, creado fuera del render (no se muta estado al pintar).
			for (const persona of pendientesDeCalificar(pool, usuarioId)) {
				borradores[persona.id] ??= { puntaje: 0, comentario: '' };
			}
		} catch (e) {
			error = mensajeError(e);
		} finally {
			cargando = false;
		}
	}

	async function enviar(persona) {
		const datos = borradores[persona.id];
		if (!datos?.puntaje) {
			errores[persona.id] = { puntaje: 'Elegí de 1 a 5 estrellas.' };
			return;
		}
		errores[persona.id] = {};
		enviando = persona.id;
		try {
			const creada = await api(`/pools/${pool.id}/resenas/`, {
				method: 'POST',
				body: payloadResena(persona.id, datos.puntaje, datos.comentario)
			});
			propias = [...propias, creada];
			notificar(`Calificaste a ${persona.username}.`);
		} catch (e) {
			errores[persona.id] = fieldErrors(e.data);
			if (!Object.keys(errores[persona.id]).length) {
				errores[persona.id] = { detail: mensajeError(e) };
			}
		} finally {
			enviando = null;
		}
	}
</script>

<section class="bloque calificar" aria-labelledby="titulo-calificar">
	<h2 id="titulo-calificar">Calificar participantes</h2>
	<p class="muted">
		El pool finalizó. Contá cómo fue la experiencia: tu reseña aparece en el perfil de cada
		persona.
	</p>

	{#if cargando}
		<p class="muted" role="status">Cargando…</p>
	{:else if error}
		<Aviso variante="error">{error}</Aviso>
	{:else}
		{#if pendientes.length}
			<ul class="calificar__lista">
				{#each pendientes.filter((p) => borradores[p.id]) as persona (persona.id)}
					{@const datos = borradores[persona.id]}
					{@const err = errores[persona.id] ?? {}}
					<li class="calificar__item">
						<div class="calificar__persona">
							<Avatar nombre={persona.username} foto={persona.foto} tamano="sm" aria-hidden="true" />
							<a href={resolve(`/usuarios/${persona.id}`)}>{persona.username}</a>
							<span class="calificar__rol">{etiquetaRol(persona.rol)}</span>
						</div>
						<fieldset class="estrellas-input">
							<legend class="sr-only">Puntaje para {persona.username}</legend>
							{#each [1, 2, 3, 4, 5] as valor (valor)}
								<label class="estrellas-input__opcion" class:llena={valor <= datos.puntaje}>
									<input
										class="sr-only"
										type="radio"
										name="puntaje-{persona.id}"
										value={valor}
										bind:group={datos.puntaje}
									/>
									<svg viewBox="0 0 24 24" aria-hidden="true">
										<path
											d="M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4l-5.9 3.1 1.2-6.5L2.5 9.4l6.6-.9z"
										/>
									</svg>
									<span class="sr-only">{valor} {valor === 1 ? 'estrella' : 'estrellas'}</span>
								</label>
							{/each}
						</fieldset>
						{#if err.puntaje}<p class="error" role="alert">{err.puntaje}</p>{/if}
						<label class="sr-only" for="comentario-{persona.id}">Comentario para {persona.username}</label>
						<textarea
							id="comentario-{persona.id}"
							class="calificar__comentario"
							rows="2"
							maxlength="500"
							placeholder="Comentario (opcional)"
							bind:value={datos.comentario}
						></textarea>
						{#if err.comentario}<p class="error" role="alert">{err.comentario}</p>{/if}
						{#if err.destinatario || err.detail}
							<p class="error" role="alert">{err.destinatario || err.detail}</p>
						{/if}
						<Boton
							variante="primario"
							tamano="sm"
							disabled={enviando === persona.id}
							onclick={() => enviar(persona)}
						>
							{enviando === persona.id ? 'Enviando…' : 'Enviar reseña'}
						</Boton>
					</li>
				{/each}
			</ul>
		{:else}
			<Aviso variante="exito">Ya calificaste a todos los participantes. ¡Gracias!</Aviso>
		{/if}

		{#if propias.length}
			<h3 class="calificar__subtitulo">Tus reseñas en este pool</h3>
			<ul class="calificar__hechas">
				{#each propias as resena (resena.id)}
					{@const persona = [pool.creador, ...pool.miembros.map((m) => m.usuario)].find(
						(p) => p.id === resena.destinatario
					)}
					<li>
						<b>{persona?.username ?? 'Participante'}</b>
						<Estrellas puntaje={resena.puntaje} />
						{#if resena.comentario}<span class="muted">“{resena.comentario}”</span>{/if}
					</li>
				{/each}
			</ul>
		{/if}
	{/if}
</section>

<style>
	.calificar__lista {
		display: flex;
		flex-direction: column;
		gap: var(--e-3);
		margin: var(--e-3) 0 0;
		padding: 0;
		list-style: none;
	}

	.calificar__item {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--e-2);
		padding: var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--crema);
	}

	.calificar__persona {
		display: flex;
		align-items: center;
		gap: var(--e-2);
		font-weight: 700;
	}

	.calificar__rol {
		font-size: var(--texto-xs);
		font-weight: 400;
		color: var(--tinta-tenue);
	}

	.estrellas-input {
		display: flex;
		gap: 2px;
		margin: 0;
		padding: 0;
		border: 0;
	}

	.estrellas-input__opcion {
		display: grid;
		place-items: center;
		width: 36px;
		height: 36px;
		cursor: pointer;
	}

	.estrellas-input__opcion svg {
		width: 28px;
		height: 28px;
		fill: var(--linea-fuerte);
		transition: fill var(--transicion);
	}

	.estrellas-input__opcion.llena svg,
	.estrellas-input__opcion:hover svg {
		fill: var(--acento-naranja);
	}

	.estrellas-input__opcion:focus-within {
		outline: 2px solid var(--marca);
		outline-offset: 1px;
		border-radius: var(--radio-xs);
	}

	.calificar__comentario {
		width: 100%;
		padding: var(--e-2) var(--e-3);
		border: 1px solid var(--linea-control);
		border-radius: var(--radio-sm);
		background: var(--superficie);
		font: inherit;
		resize: vertical;
	}

	.calificar__subtitulo {
		margin: var(--e-5) 0 var(--e-2);
		font-size: var(--texto-md);
	}

	.calificar__hechas {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		margin: 0;
		padding: 0;
		list-style: none;
		font-size: var(--texto-sm);
	}

	.calificar__hechas li {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2);
	}
</style>
