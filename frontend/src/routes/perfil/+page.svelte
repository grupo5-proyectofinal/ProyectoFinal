<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { fieldErrors } from '$lib/api.js';
	import { iniciales } from '$lib/formato.js';
	import { session, logout, updateMe } from '$lib/session.svelte.js';
	import Avatar from '$lib/ui/Avatar.svelte';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let errors = $state({});
	let exito = $state('');
	let guardando = $state(false);
	let nombreFoto = $state('');
	let form = $state();

	const generos = ['Femenino', 'Masculino', 'Otro', 'Prefiero no decir'];

	function alElegirFoto(event) {
		nombreFoto = event.target.files?.[0]?.name ?? '';
	}

	async function enviar(event) {
		event.preventDefault();
		errors = {};
		exito = '';
		guardando = true;
		try {
			const data = new FormData(form);
			if (!data.get('foto')?.name) data.delete('foto');
			await updateMe(data, true);
			exito = 'Datos actualizados.';
		} catch (error) {
			if (error.status === 401) {
				logout();
				goto(resolve('/login'));
				return;
			}
			errors = fieldErrors(error.data);
			if (!Object.keys(errors).length) errors = { detail: 'No se pudo actualizar el perfil.' };
		} finally {
			guardando = false;
		}
	}

	const nombreVisible = $derived(
		[session.user?.first_name, session.user?.last_name].filter(Boolean).join(' ') ||
			session.user?.username ||
			''
	);

	const generoSeleccionado = $derived(
		generos.find(
			(g) => g.toLowerCase() === (session.user?.genero ?? '').toLowerCase()
		) ?? ''
	);

	// Descartar: vuelve los controles a los datos de la sesión (sin llamada API).
	function descartar() {
		for (const [clave, valor] of Object.entries({
			first_name: session.user?.first_name ?? '',
			last_name: session.user?.last_name ?? '',
			telefono: session.user?.telefono ?? '',
			genero: generoSeleccionado,
			direccion: session.user?.direccion ?? '',
			ciudad: session.user?.ciudad ?? ''
		})) {
			if (form?.elements[clave]) form.elements[clave].value = valor;
		}
		nombreFoto = '';
		exito = '';
		errors = {};
	}
</script>

<svelte:head>
	<title>Mi perfil — PoolShop</title>
</svelte:head>

{#if session.user}
	<div class="perfil">
		<aside class="perfil__resumen">
			<div class="perfil__tarjeta">
				<Avatar
					class="perfil__avatar"
					nombre={nombreVisible}
					foto={session.user.foto}
					tamano="lg"
					aria-hidden="true"
				/>
				<h1 class="perfil__nombre">{nombreVisible}</h1>
				<p class="perfil__meta">
					@{session.user.username}{#if session.user.ciudad}&nbsp;· {session.user.ciudad}{/if}
				</p>
			</div>
		</aside>

		<Tarjeta>
			<form class="perfil__form" bind:this={form} onsubmit={enviar}>
				<div class="perfil__cabecera">
					<h2 class="perfil__titulo">Datos de la cuenta</h2>
					<Campo
						id="foto"
						etiqueta="Foto de perfil"
						ayuda={nombreFoto || 'JPG, PNG u otro formato de imagen.'}
						error={errors.foto}
					>
						{#snippet children(props)}
							<div class="perfil__foto">
								<input
									id="foto"
									class="archivo__input"
									name="foto"
									type="file"
									accept="image/*"
									onchange={alElegirFoto}
									{...props}
								/>
								<label class="perfil__foto-boton" for="foto">
									<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.5" /></svg>
									Cambiar foto
								</label>
							</div>
						{/snippet}
					</Campo>
				</div>

				<div class="perfil__grilla">
					<Campo id="first_name" etiqueta="Nombre" error={errors.first_name}>
						{#snippet children(props)}
							<input
								id="first_name"
								name="first_name"
								type="text"
								autocomplete="given-name"
								value={session.user.first_name}
								{...props}
							/>
						{/snippet}
					</Campo>

					<Campo id="last_name" etiqueta="Apellido" error={errors.last_name}>
						{#snippet children(props)}
							<input
								id="last_name"
								name="last_name"
								type="text"
								autocomplete="family-name"
								value={session.user.last_name}
								{...props}
							/>
						{/snippet}
					</Campo>

					<Campo id="telefono" etiqueta="Teléfono" error={errors.telefono}>
						{#snippet children(props)}
							<input
								id="telefono"
								name="telefono"
								type="tel"
								autocomplete="tel"
								value={session.user.telefono}
								{...props}
							/>
						{/snippet}
					</Campo>

					<Campo id="genero" etiqueta="Género" error={errors.genero}>
						{#snippet children(props)}
							<select id="genero" name="genero" value={generoSeleccionado} {...props}>
								<option value="">Sin especificar</option>
								{#each generos as genero (genero)}
									<option value={genero}>{genero}</option>
								{/each}
							</select>
						{/snippet}
					</Campo>

					<Campo id="direccion" etiqueta="Dirección" error={errors.direccion}>
						{#snippet children(props)}
							<input
								id="direccion"
								name="direccion"
								type="text"
								autocomplete="street-address"
								value={session.user.direccion}
								{...props}
							/>
						{/snippet}
					</Campo>

					<Campo id="ciudad" etiqueta="Ciudad" error={errors.ciudad}>
						{#snippet children(props)}
							<input
								id="ciudad"
								name="ciudad"
								type="text"
								autocomplete="address-level2"
								value={session.user.ciudad}
								{...props}
							/>
						{/snippet}
					</Campo>

					<Campo id="email" etiqueta="Email" ayuda="No se puede cambiar desde acá.">
						{#snippet children(props)}
							<input id="email" type="email" value={session.user.email} disabled {...props} />
						{/snippet}
					</Campo>

					<Campo id="dni" etiqueta="DNI" ayuda="No se puede cambiar desde acá.">
						{#snippet children(props)}
							<input id="dni" type="text" value={session.user.dni} disabled {...props} />
						{/snippet}
					</Campo>
				</div>

				{#if exito}
					<Aviso variante="exito">{exito}</Aviso>
				{/if}
				{#if errors.detail}
					<Aviso variante="error">{errors.detail}</Aviso>
				{/if}
				{#if errors.non_field_errors}
					<Aviso variante="error">{errors.non_field_errors}</Aviso>
				{/if}

				<div class="perfil__acciones">
					<Boton variante="secundario" onclick={descartar}>Descartar</Boton>
					<Boton variante="primario" tipo="submit" disabled={guardando}>
						{#if guardando}<span class="spinner spinner--chico"></span> Guardando…{:else}Guardar
							cambios{/if}
					</Boton>
				</div>
			</form>
		</Tarjeta>
	</div>
{:else if session.loading}
	<div class="cargando" role="status"><span class="spinner"></span> Cargando tu perfil…</div>
{:else if session.access}
	<div class="cargando" role="alert">
		<Aviso variante="error">No se pudieron cargar los datos del perfil.</Aviso>
	</div>
{/if}

<style>
	.perfil {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-6);
		align-items: flex-start;
	}

	.perfil__resumen {
		flex: 1 1 320px;
		min-width: 0;
	}

	.perfil__tarjeta {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--e-3);
		padding: var(--e-6);
		border-radius: var(--radio-lg);
		background: var(--melocoton);
		text-align: center;
	}

	/* La primitiva Avatar solo tiene sm/md/lg; el mockup pide 108px con anillo
	   blanco de 4px. El selector va entero dentro de :global porque el scope de
	   Svelte no cruza a las primitivas (regla de fases 2-4). */
	:global(.perfil__avatar.ui-avatar) {
		width: 6.75rem;
		height: 6.75rem;
		border: 4px solid var(--superficie);
		font-size: 2.4rem;
	}

	.perfil__nombre {
		margin: var(--e-1) 0 0;
		font-family: var(--fuente-display);
		font-size: var(--texto-xl);
	}

	.perfil__meta {
		margin: 0;
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
	}

	/* La card de la primitiva no lleva el scope de la página: :global completo. */
	:global(.perfil > .ui-tarjeta) {
		flex: 999 1 560px;
		min-width: 0;
	}

	.perfil__form {
		display: flex;
		flex-direction: column;
		gap: var(--e-5);
		padding: var(--e-6);
	}

	.perfil__cabecera {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		align-items: center;
		gap: var(--e-4);
	}

	.perfil__cabecera :global(.ui-campo) {
		margin-bottom: 0;
	}

	/* El control de foto se autoexplica con el botón + la ayuda: la etiqueta
	   "Foto de perfil" del Campo no aporta y desalinea la cabecera del mockup. */
	.perfil__cabecera :global(.ui-campo__etiqueta) {
		display: none;
	}

	.perfil__titulo {
		margin: 0;
		font-family: var(--fuente-display);
		font-size: var(--texto-lg);
	}

	.perfil__foto {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3);
	}

	/* Botón "Cambiar foto" del mockup: es un label del input file oculto
	   (la primitiva Boton es button/a y no dispara el file picker). */
	.perfil__foto-boton {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5em;
		height: 40px;
		padding: 0 0.9rem;
		border: 1px solid var(--linea-fuerte);
		border-radius: var(--radio-xs);
		background: var(--superficie);
		color: var(--tinta);
		font-size: var(--texto-sm);
		font-weight: 700;
		cursor: pointer;
		transition:
			border-color var(--transicion),
			color var(--transicion),
			background-color var(--transicion);
	}

	.perfil__foto-boton:hover {
		border-color: var(--marca);
		background: var(--melocoton);
		color: var(--marca-fuerte);
	}

	.perfil__foto-boton:focus-within {
		outline: 2px solid var(--acento);
		outline-offset: 1px;
	}

	.perfil__grilla {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
		gap: var(--e-4);
	}

	.perfil__grilla :global(.ui-campo) {
		margin-bottom: 0;
	}

	.perfil__acciones {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		gap: var(--e-3);
	}

	@media (min-width: 901px) {
		.perfil__resumen {
			position: sticky;
			top: calc(var(--alto-cabecera) + var(--e-5));
		}
	}

	@media (max-width: 900px) {
		.perfil__resumen {
			max-width: 26rem;
		}
	}
</style>
