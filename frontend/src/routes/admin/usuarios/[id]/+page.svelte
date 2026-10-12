<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { alPerderAcceso } from '$lib/admin.svelte.js';
	import { esStaff, fusionarUsuario, nombreUsuario, puedeToggle } from '$lib/admin.js';
	import { api, fieldErrors } from '$lib/api.js';
	import { session } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Avatar from '$lib/ui/Avatar.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

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
		<Boton variante="ghost" href={resolve('/admin/usuarios')}>Volver al listado</Boton>
	</div>
</div>

{#if !session.user}
	{#if session.loading}
		<div class="cargando" role="status"><span class="spinner"></span> Cargando tu sesión…</div>
	{:else}
		<Aviso variante="error">
			No se pudieron cargar tus datos. Recargá la página para volver a intentar.
		</Aviso>
	{/if}
{:else if cargando}
	<div class="cargando" role="status"><span class="spinner"></span> Cargando usuario…</div>
{:else if error}
	<Aviso variante="error">{error}</Aviso>
	<p class="volver"><a href={resolve('/admin/usuarios')}>Volver al listado</a></p>
{:else if usuario}
	<div class="ficha">
		<aside class="resumen">
			<Tarjeta class="resumen__tarjeta">
				<Avatar
					class="resumen__avatar"
					nombre={nombreUsuario(usuario)}
					foto={usuario.foto}
					tamano="lg"
					aria-hidden="true"
				/>
				<h2 class="resumen__nombre">{nombreUsuario(usuario)}</h2>
				<p class="resumen__usuario">@{usuario.username}</p>

				<p class="resumen__estado">
					<Badge variante={usuario.is_active ? 'activo' : 'inactivo'}>
						{usuario.is_active ? 'Activo' : 'Inactivo'}
					</Badge>
					{#if usuario.is_staff}<Badge variante="staff">Admin</Badge>{/if}
				</p>

				{#if puede}
					<Boton
						variante="secundario"
						bloque
						tipo="button"
						disabled={toggleando}
						onclick={alternarActivo}
					>
						{toggleando
							? 'Guardando…'
							: usuario.is_active
								? 'Desactivar cuenta'
								: 'Activar cuenta'}
					</Boton>
				{:else}
					<p class="ayuda">No podés desactivar tu propia cuenta.</p>
				{/if}
				{#if errorToggle}
					<div class="resumen__aviso"><Aviso variante="error">{errorToggle}</Aviso></div>
				{/if}

				<dl class="resumen__datos">
					<dt>Email</dt>
					<dd>{usuario.email}</dd>
					<dt>DNI</dt>
					<dd>{usuario.dni}</dd>
				</dl>
				<p class="resumen__nota">El email, el usuario y el DNI no se pueden editar.</p>
			</Tarjeta>
		</aside>

		<Tarjeta class="formulario">
			<form bind:this={form} onsubmit={guardar}>
				<fieldset class="bloque">
					<legend>Datos personales</legend>
					<div class="grilla-campos">
						<Campo id="first_name" etiqueta="Nombre" error={errors.first_name}>
							{#snippet children(props)}
								<input
									id="first_name"
									name="first_name"
									type="text"
									value={usuario.first_name}
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
									value={usuario.last_name}
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
									value={usuario.telefono}
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
					</div>
				</fieldset>

				<fieldset class="bloque">
					<legend>Domicilio</legend>
					<div class="grilla-campos">
						<Campo id="direccion" etiqueta="Dirección" error={errors.direccion}>
							{#snippet children(props)}
								<input
									id="direccion"
									name="direccion"
									type="text"
									value={usuario.direccion}
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
									value={usuario.ciudad}
									{...props}
								/>
							{/snippet}
						</Campo>
					</div>
				</fieldset>

				<fieldset class="bloque">
					<legend>Foto de perfil</legend>
					<Campo
						id="foto"
						etiqueta="Reemplazar foto"
						ayuda="JPG, PNG u otro formato de imagen."
						error={errors.foto}
					>
						{#snippet children(props)}
							<div class="archivo">
								<input
									id="foto"
									class="archivo__input"
									name="foto"
									type="file"
									accept="image/*"
									onchange={alElegirFoto}
									{...props}
								/>
								<label class="archivo__boton btn btn--secundario" for="foto">Elegir archivo</label>
								<span class="archivo__nombre">{nombreFoto || 'Sin archivo'}</span>
							</div>
						{/snippet}
					</Campo>
				</fieldset>

				{#if exito}
					<Aviso variante="exito">{exito}</Aviso>
				{/if}
				{#if errors.detail}
					<Aviso variante="error">{errors.detail}</Aviso>
				{/if}
				{#if errors.non_field_errors}
					<Aviso variante="error">{errors.non_field_errors}</Aviso>
				{/if}

				<Boton variante="primario" tipo="submit" disabled={guardando}>
					{#if guardando}<span class="spinner spinner--chico"></span> Guardando…{:else}Guardar
						cambios{/if}
				</Boton>
			</form>
		</Tarjeta>
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
	}

	/* Las clases viajan a las primitivas (sin el scope de la página): el selector
	   :global va completo, como en las fases 3-5. */
	:global(.resumen__tarjeta.ui-tarjeta) {
		padding: var(--e-6);
		text-align: center;
	}

	:global(.resumen__avatar.ui-avatar) {
		width: 6rem;
		height: 6rem;
		margin: 0 auto var(--e-4);
		border: 1px solid var(--linea);
		font-size: 2rem;
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

	.resumen__aviso {
		margin-bottom: var(--e-4);
		text-align: left;
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

	@media (max-width: 820px) {
		.ficha {
			grid-template-columns: 1fr;
		}

		.resumen {
			position: static;
		}
	}
</style>
