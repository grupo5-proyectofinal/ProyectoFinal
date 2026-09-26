<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { fieldErrors } from '$lib/api.js';
	import { tonoNombre } from '$lib/estados.js';
	import { iniciales } from '$lib/formato.js';
	import { session, logout, updateMe } from '$lib/session.svelte.js';

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
</script>

<svelte:head>
	<title>Mi perfil — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Mi perfil</h1>
		<p>Tus datos de contacto y tu foto pública dentro de los pools.</p>
	</div>
</div>

{#if session.user}
	<div class="perfil">
		<aside class="resumen panel">
			{#if session.user.foto}
				<img class="resumen__foto" src={session.user.foto} alt="Foto de perfil" width="96" height="96" />
			{:else}
				<span
					class="resumen__monograma tono-{tonoNombre(session.user.username)}"
					aria-hidden="true">{iniciales(nombreVisible)}</span
				>
			{/if}
			<h2 class="resumen__nombre">{nombreVisible}</h2>
			<p class="resumen__usuario">@{session.user.username}</p>
			<dl class="resumen__datos">
				<dt>Email</dt>
				<dd>{session.user.email}</dd>
				<dt>DNI</dt>
				<dd>{session.user.dni}</dd>
				{#if session.user.ciudad}
					<dt>Ciudad</dt>
					<dd>{session.user.ciudad}</dd>
				{/if}
			</dl>
			<p class="resumen__nota">
				El email, el usuario y el DNI no se pueden cambiar desde acá.
			</p>
		</aside>

		<section class="panel formulario">
			<form bind:this={form} onsubmit={enviar}>
				<fieldset class="bloque">
					<legend>Datos personales</legend>
					<div class="grilla-campos">
						<div class="campo">
							<label for="first_name">Nombre</label>
							<input
								id="first_name"
								name="first_name"
								type="text"
								autocomplete="given-name"
								value={session.user.first_name}
								aria-invalid={errors.first_name ? 'true' : undefined}
								aria-describedby={errors.first_name ? 'first_name-error' : undefined}
							/>
							{#if errors.first_name}
								<p class="error" id="first_name-error">{errors.first_name}</p>
							{/if}
						</div>
						<div class="campo">
							<label for="last_name">Apellido</label>
							<input
								id="last_name"
								name="last_name"
								type="text"
								autocomplete="family-name"
								value={session.user.last_name}
								aria-invalid={errors.last_name ? 'true' : undefined}
								aria-describedby={errors.last_name ? 'last_name-error' : undefined}
							/>
							{#if errors.last_name}
								<p class="error" id="last_name-error">{errors.last_name}</p>
							{/if}
						</div>
						<div class="campo">
							<label for="telefono">Teléfono</label>
							<input
								id="telefono"
								name="telefono"
								type="tel"
								autocomplete="tel"
								value={session.user.telefono}
								aria-invalid={errors.telefono ? 'true' : undefined}
								aria-describedby={errors.telefono ? 'telefono-error' : undefined}
							/>
							{#if errors.telefono}
								<p class="error" id="telefono-error">{errors.telefono}</p>
							{/if}
						</div>
						<div class="campo">
							<label for="genero">Género</label>
							<select id="genero" name="genero" value={generoSeleccionado}>
								<option value="">Sin especificar</option>
								{#each generos as genero (genero)}
									<option value={genero}>{genero}</option>
								{/each}
							</select>
							{#if errors.genero}<p class="error">{errors.genero}</p>{/if}
						</div>
					</div>
				</fieldset>

				<fieldset class="bloque">
					<legend>Domicilio</legend>
					<div class="grilla-campos">
						<div class="campo">
							<label for="direccion">Dirección</label>
							<input
								id="direccion"
								name="direccion"
								type="text"
								autocomplete="street-address"
								value={session.user.direccion}
								aria-invalid={errors.direccion ? 'true' : undefined}
								aria-describedby={errors.direccion ? 'direccion-error' : undefined}
							/>
							{#if errors.direccion}
								<p class="error" id="direccion-error">{errors.direccion}</p>
							{/if}
						</div>
						<div class="campo">
							<label for="ciudad">Ciudad</label>
							<input
								id="ciudad"
								name="ciudad"
								type="text"
								autocomplete="address-level2"
								value={session.user.ciudad}
								aria-invalid={errors.ciudad ? 'true' : undefined}
								aria-describedby={errors.ciudad ? 'ciudad-error' : undefined}
							/>
							{#if errors.ciudad}
								<p class="error" id="ciudad-error">{errors.ciudad}</p>
							{/if}
						</div>
					</div>
				</fieldset>

				<fieldset class="bloque">
					<legend>Foto de perfil</legend>
					<div class="campo">
						<label for="foto">Reemplazar foto</label>
						<div class="archivo">
							<input
								id="foto"
								class="archivo__input"
								name="foto"
								type="file"
								accept="image/*"
								onchange={alElegirFoto}
								aria-describedby={errors.foto ? 'foto-error' : 'foto-ayuda'}
							/>
							<label class="archivo__boton btn btn--secundario" for="foto">Elegir archivo</label>
							<span class="archivo__nombre">{nombreFoto || 'Sin archivo'}</span>
						</div>
						{#if errors.foto}
							<p class="error" id="foto-error">{errors.foto}</p>
						{:else}
							<p class="ayuda" id="foto-ayuda">JPG, PNG u otro formato de imagen.</p>
						{/if}
					</div>
				</fieldset>

				{#if exito}
					<div class="alerta alerta--exito aviso" role="status">{exito}</div>
				{/if}
				{#if errors.detail}
					<div class="alerta alerta--error aviso" role="alert">{errors.detail}</div>
				{/if}
				{#if errors.non_field_errors}
					<div class="alerta alerta--error aviso" role="alert">{errors.non_field_errors}</div>
				{/if}

				<button class="btn btn--primario" type="submit" disabled={guardando}>
					{#if guardando}<span class="spinner spinner--chico"></span> Guardando…{:else}Guardar
						cambios{/if}
				</button>
			</form>
		</section>
	</div>
{:else if session.loading}
	<div class="cargando" role="status"><span class="spinner"></span> Cargando tu perfil…</div>
{:else if session.access}
	<div class="alerta alerta--error" role="alert">No se pudieron cargar los datos del perfil.</div>
{/if}

<style>
	.perfil {
		display: grid;
		grid-template-columns: minmax(0, 300px) minmax(0, 1fr);
		gap: var(--e-6);
		align-items: start;
	}

	.resumen {
		position: sticky;
		top: calc(var(--alto-cabecera) + var(--e-5));
		padding: var(--e-6);
		text-align: center;
	}

	.resumen__foto {
		width: 6rem;
		height: 6rem;
		margin: 0 auto var(--e-4);
		border-radius: 50%;
		object-fit: cover;
		border: 1px solid var(--linea);
	}

	.resumen__monograma {
		display: grid;
		place-items: center;
		width: 6rem;
		height: 6rem;
		margin: 0 auto var(--e-4);
		border: 1px solid var(--t-t);
		border-radius: 50%;
		background: var(--t-t);
		font-family: var(--fuente-display);
		font-size: 2rem;
		color: var(--c-t);
	}

	.resumen__nombre {
		font-size: var(--texto-lg);
	}

	.resumen__usuario {
		margin: var(--e-1) 0 var(--e-5);
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
	}

	.resumen__datos {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--e-1) var(--e-3);
		margin: 0;
		text-align: left;
		font-size: var(--texto-sm);
	}

	.resumen__datos dt {
		color: var(--tinta-tenue);
	}

	.resumen__datos dd {
		margin: 0;
		word-break: break-word;
	}

	.resumen__nota {
		margin-top: var(--e-5);
		padding-top: var(--e-4);
		border-top: 1px solid var(--linea);
		color: var(--tinta-tenue);
		font-size: var(--texto-xs);
	}

	@media (max-width: 820px) {
		.perfil {
			grid-template-columns: 1fr;
		}

		.resumen {
			position: static;
		}
	}

</style>
