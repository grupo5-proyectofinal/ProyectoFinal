<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { alPerderAcceso } from '$lib/admin.svelte.js';
	import { esStaff, fusionarUsuario, nombreUsuario, puedeToggle } from '$lib/admin.js';
	import { api, fieldErrors } from '$lib/api.js';
	import { tonoNombre } from '$lib/estados.js';
	import { iniciales } from '$lib/formato.js';
	import { session } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';

	let usuario = $state(null);
	let cargando = $state(true);
	let error = $state('');
	let errors = $state({});
	let errorToggle = $state('');
	let exito = $state('');
	let guardando = $state(false);
	let toggleando = $state(false);
	let nombreFoto = $state('');
	let form = $state();

	const generos = ['Femenino', 'Masculino', 'Otro', 'Prefiero no decir'];

	$effect(() => {
		if (esStaff(session.user)) cargar(page.params.id);
	});

	async function cargar(id) {
		cargando = true;
		error = '';
		try {
			usuario = await api(`/admin/usuarios/${id}/`);
		} catch (e) {
			if (e.status === 403) {
				alPerderAcceso();
				return;
			}
			if (e.status === 404) {
				notificar('Ese usuario no existe.', 'aviso');
				goto(resolve('/admin/usuarios'));
				return;
			}
			error = 'No se pudo cargar el usuario.';
		} finally {
			cargando = false;
		}
	}

	const puede = $derived(puedeToggle(usuario, session.user));
	const generoSeleccionado = $derived(
		generos.find((g) => g.toLowerCase() === (usuario?.genero ?? '').toLowerCase()) ?? ''
	);

	function alElegirFoto(event) {
		nombreFoto = event.target.files?.[0]?.name ?? '';
	}

	async function guardar(event) {
		event.preventDefault();
		errors = {};
		exito = '';
		guardando = true;
		try {
			const data = new FormData(form);
			if (!data.get('foto')?.name) data.delete('foto');
			const r = await api(`/admin/usuarios/${usuario.id}/`, {
				method: 'PATCH',
				body: data,
				form: true
			});
			usuario = fusionarUsuario(usuario, r);
			exito = 'Datos actualizados.';
		} catch (e) {
			if (e.status === 403) {
				alPerderAcceso();
				return;
			}
			errors = fieldErrors(e.data);
			if (!Object.keys(errors).length) errors = { detail: 'No se pudieron guardar los cambios.' };
		} finally {
			guardando = false;
		}
	}

	async function alternarActivo() {
		errorToggle = '';
		toggleando = true;
		try {
			const r = await api(`/admin/usuarios/${usuario.id}/`, {
				method: 'PATCH',
				body: { is_active: !usuario.is_active }
			});
			usuario = fusionarUsuario(usuario, r);
			notificar(r.is_active ? 'Usuario activado.' : 'Usuario desactivado.');
		} catch (e) {
			if (e.status === 403) {
				alPerderAcceso();
				return;
			}
			const errs = fieldErrors(e.data);
			errorToggle = errs.is_active || errs.detail || 'No se pudo cambiar el estado.';
		} finally {
			toggleando = false;
		}
	}
</script>

<svelte:head>
	<title>{usuario ? nombreUsuario(usuario) : 'Usuario'} — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Ficha de usuario</h1>
		<p>Editá el perfil y gestioná el acceso de la cuenta.</p>
	</div>
	<div class="cabecera-pagina__acciones">
		<a class="btn btn--ghost" href={resolve('/admin/usuarios')}>Volver al listado</a>
	</div>
</div>

{#if !session.user}
	{#if session.loading}
		<div class="cargando" role="status"><span class="spinner"></span> Cargando tu sesión…</div>
	{:else}
		<div class="alerta alerta--error" role="alert">
			No se pudieron cargar tus datos. Recargá la página para volver a intentar.
		</div>
	{/if}
{:else if cargando}
	<div class="cargando" role="status"><span class="spinner"></span> Cargando usuario…</div>
{:else if error}
	<div class="alerta alerta--error" role="alert">{error}</div>
	<p class="volver"><a href={resolve('/admin/usuarios')}>Volver al listado</a></p>
{:else if usuario}
	<div class="ficha">
		<aside class="resumen panel">
			{#if usuario.foto}
				<img class="resumen__foto" src={usuario.foto} alt="Foto de perfil" width="96" height="96" />
			{:else}
				<span
					class="resumen__monograma tono-{tonoNombre(usuario.username)}"
					aria-hidden="true">{iniciales(nombreUsuario(usuario))}</span
				>
			{/if}
			<h2 class="resumen__nombre">{nombreUsuario(usuario)}</h2>
			<p class="resumen__usuario">@{usuario.username}</p>

			<p class="resumen__estado">
				<span class="badge {usuario.is_active ? 'badge--activo' : 'badge--inactivo'}">
					{usuario.is_active ? 'Activo' : 'Inactivo'}
				</span>
				{#if usuario.is_staff}<span class="badge badge--staff">Admin</span>{/if}
			</p>

			{#if puede}
				<button
					class="btn btn--secundario btn--bloque"
					type="button"
					disabled={toggleando}
					onclick={alternarActivo}
				>
					{toggleando
						? 'Guardando…'
						: usuario.is_active
							? 'Desactivar cuenta'
							: 'Activar cuenta'}
				</button>
			{:else}
				<p class="ayuda">No podés desactivar tu propia cuenta.</p>
			{/if}
			{#if errorToggle}
				<p class="error" role="alert">{errorToggle}</p>
			{/if}

			<dl class="resumen__datos">
				<dt>Email</dt>
				<dd>{usuario.email}</dd>
				<dt>DNI</dt>
				<dd>{usuario.dni}</dd>
			</dl>
			<p class="resumen__nota">El email, el usuario y el DNI no se pueden editar.</p>
		</aside>

		<section class="panel formulario">
			<form bind:this={form} onsubmit={guardar}>
				<fieldset class="bloque">
					<legend>Datos personales</legend>
					<div class="grilla-campos">
						<div class="campo">
							<label for="first_name">Nombre</label>
							<input
								id="first_name"
								name="first_name"
								type="text"
								value={usuario.first_name}
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
								value={usuario.last_name}
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
								value={usuario.telefono}
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
								value={usuario.direccion}
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
								value={usuario.ciudad}
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
{/if}

<style>
	.ficha {
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
		margin: var(--e-1) 0 var(--e-4);
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
	}

	.resumen__estado {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: var(--e-2);
		margin-bottom: var(--e-4);
	}

	.resumen__datos {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--e-1) var(--e-3);
		margin: var(--e-5) 0 0;
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

	.volver {
		margin-top: var(--e-4);
	}

	.badge--activo {
		background: var(--exito-suave);
		color: var(--exito);
		border-color: var(--borde-exito);
	}

	.badge--inactivo {
		background: var(--superficie-alt);
		color: var(--tinta-suave);
		border-color: var(--linea);
	}

	.badge--staff {
		background: var(--acento-suave);
		color: var(--acento);
		border-color: var(--borde-acento);
	}

	@media (max-width: 820px) {
		.ficha {
			grid-template-columns: 1fr;
		}

		.resumen {
			position: static;
		}
	}
</style>
