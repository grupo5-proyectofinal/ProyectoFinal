<script>
	import { beforeNavigate } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { fieldErrors } from '$lib/api.js';
	import { confirmar } from '$lib/confirmacion.svelte.js';
	import { corregirIdentidad, session, updateMe } from '$lib/session.svelte.js';
	import BajaCuenta from '$lib/BajaCuenta.svelte';
	import Avatar from '$lib/ui/Avatar.svelte';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let errors = $state({});
	let exito = $state('');
	let guardando = $state(false);
	let nombreFoto = $state('');
	let fotoPreview = $state('');
	let fotoUrl = '';
	let fotoHeic = $state(false);
	let sucio = $state(false);
	let form = $state();
	// Corrección asistida de DNI/email: formulario aparte, con contraseña.
	let passwordIdentidad = $state('');
	let dniIdentidad = $state('');
	let emailIdentidad = $state('');
	let erroresIdentidad = $state({});
	let errorIdentidad = $state('');
	let exitoIdentidad = $state('');
	let guardandoIdentidad = $state(false);

	// Aviso antes de perder cambios sin guardar (incluye "Ver mi perfil público").
	beforeNavigate(async ({ cancel }) => {
		if (!sucio) return;
		const salir = await confirmar({
			titulo: '¿Salir sin guardar?',
			descripcion: 'Tenés cambios en el perfil que todavía no guardaste.',
			confirmar: 'Salir sin guardar'
		});
		if (!salir) cancel();
	});

	// Refrescar o cerrar la pestaña no pasa por beforeNavigate.
	function alSalir(evento) {
		if (!sucio) return;
		evento.preventDefault();
		evento.returnValue = '';
	}

	const generos = ['Femenino', 'Masculino', 'Otro', 'Prefiero no decir'];

	function alElegirFoto(event) {
		const archivo = event.target.files?.[0];
		nombreFoto = archivo?.name ?? '';
		sucio = true;
		if (fotoUrl) URL.revokeObjectURL(fotoUrl);
		// HEIC es el formato por defecto del iPhone y no se decodifica en todos
		// los navegadores: se manda igual, pero no se muestra una miniatura rota.
		fotoHeic = /\.(heic|heif)$/i.test(nombreFoto);
		fotoUrl = archivo && !fotoHeic ? URL.createObjectURL(archivo) : '';
		fotoPreview = fotoUrl;
	}

	function limpiarFoto() {
		if (fotoUrl) URL.revokeObjectURL(fotoUrl);
		fotoUrl = '';
		fotoPreview = '';
		nombreFoto = '';
		fotoHeic = false;
		sucio = false;
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
			limpiarFoto();
			sucio = false;
			exito = 'Datos actualizados.';
		} catch (error) {
			// 401: api.js ya avisó "Tu sesión expiró" y el layout lleva al login.
			if (error.status === 401) return;
			errors = fieldErrors(error.data);
			if (!Object.keys(errors).length) errors = { detail: 'No se pudo actualizar el perfil.' };
		} finally {
			guardando = false;
		}
	}

	async function corregir(evento) {
		evento.preventDefault();
		if (guardandoIdentidad) return;
		erroresIdentidad = {};
		errorIdentidad = '';
		exitoIdentidad = '';
		if (!dniIdentidad.trim() && !emailIdentidad.trim()) {
			errorIdentidad = 'Ingresá un DNI nuevo, un email nuevo o los dos.';
			return;
		}
		guardandoIdentidad = true;
		try {
			const data = await corregirIdentidad({
				password: passwordIdentidad,
				...(dniIdentidad.trim() ? { dni: dniIdentidad.trim() } : {}),
				...(emailIdentidad.trim() ? { email: emailIdentidad.trim() } : {})
			});
			exitoIdentidad = data.detail;
			passwordIdentidad = '';
			dniIdentidad = '';
			emailIdentidad = '';
		} catch (error) {
			erroresIdentidad = fieldErrors(error.data);
			errorIdentidad =
				erroresIdentidad.non_field_errors ||
				erroresIdentidad.detail ||
				'No se pudo guardar la corrección.';
		} finally {
			guardandoIdentidad = false;
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
		if (form?.elements.foto) form.elements.foto.value = '';
		limpiarFoto();
		exito = '';
		errors = {};
	}
</script>

<svelte:window onbeforeunload={alSalir} />

<svelte:head>
	<title>Mi perfil — PoolShop</title>
</svelte:head>

{#if session.user}
	<div class="cabecera-pagina">
		<div>
			<h1>Mi perfil</h1>
			<p>Tus datos de cuenta. Lo que ven los demás está en tu perfil público.</p>
		</div>
		<div class="cabecera-pagina__acciones">
			<Boton variante="secundario" href={resolve(`/usuarios/${session.user.id}`)}>
				Ver mi perfil público
			</Boton>
		</div>
	</div>

	<div class="perfil">
		<aside class="perfil__resumen">
			<div class="perfil__tarjeta">
				<Avatar
					class="perfil__avatar"
					nombre={nombreVisible}
					foto={fotoPreview || session.user.foto}
					tamano="lg"
					aria-hidden="true"
				/>
				<p class="perfil__nombre">{nombreVisible}</p>
				<p class="perfil__meta">
					@{session.user.username}{#if session.user.ciudad}&nbsp;· {session.user.ciudad}{/if}
				</p>
			</div>
		</aside>

		<div class="perfil__principal">
			<Tarjeta>
				<form
					class="perfil__form"
					bind:this={form}
					onsubmit={enviar}
					oninput={() => (sucio = true)}
				>
					<div class="perfil__cabecera">
						<div class="perfil__cabecera-texto">
							<h2 class="perfil__titulo">Datos de la cuenta</h2>
							<p class="perfil__privacidad">
								Tu email, DNI, teléfono y dirección no se muestran en tu perfil público. Tu ciudad sí.
							</p>
						</div>
						<Campo
							id="foto"
							etiqueta="Foto de perfil"
							ayuda={fotoHeic
								? `${nombreFoto} se convierte al guardar.`
								: nombreFoto || 'JPG, PNG, HEIC o WEBP.'}
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

						<Campo
							id="email"
							etiqueta="Email"
							ayuda="Usá “Corregir DNI o email” abajo si tiene un error."
						>
							{#snippet children(props)}
								<input id="email" type="email" value={session.user.email} disabled {...props} />
							{/snippet}
						</Campo>

						<Campo
							id="dni"
							etiqueta="DNI"
							ayuda="Usá “Corregir DNI o email” abajo si tiene un error."
						>
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

			<Tarjeta>
				<form class="perfil__form" onsubmit={corregir}>
					<h2 class="perfil__titulo">Corregir DNI o email</h2>
					<p class="perfil__privacidad">
						Si tus datos tienen un error, corregilos acá. Te pedimos la contraseña actual. Si
						cambiás el email, te mandamos un enlace al nuevo domicilio para confirmarlo.
					</p>
					<Campo
						id="identidad-password"
						etiqueta="Contraseña actual"
						requerido
						error={erroresIdentidad.password}
					>
						{#snippet children(props)}
							<input
								id="identidad-password"
								type="password"
								autocomplete="current-password"
								bind:value={passwordIdentidad}
								required
								{...props}
							/>
						{/snippet}
					</Campo>
					<div class="grilla-campos">
						<Campo
							id="identidad-dni"
							etiqueta="DNI nuevo"
							ayuda={`Actual: ${session.user.dni}. Dejalo vacío para no cambiarlo.`}
							error={erroresIdentidad.dni}
						>
							{#snippet children(props)}
								<input
									id="identidad-dni"
									type="text"
									inputmode="numeric"
									autocomplete="off"
									placeholder={session.user.dni}
									bind:value={dniIdentidad}
									{...props}
								/>
							{/snippet}
						</Campo>
						<Campo
							id="identidad-email"
							etiqueta="Email nuevo"
							ayuda={`Actual: ${session.user.email}. Dejalo vacío para no cambiarlo.`}
							error={erroresIdentidad.email}
						>
							{#snippet children(props)}
								<input
									id="identidad-email"
									type="email"
									autocomplete="off"
									placeholder={session.user.email}
									bind:value={emailIdentidad}
									{...props}
								/>
							{/snippet}
						</Campo>
					</div>
					{#if errorIdentidad}
						<Aviso variante="error">{errorIdentidad}</Aviso>
					{/if}
					{#if exitoIdentidad}
						<Aviso variante="exito">{exitoIdentidad}</Aviso>
					{/if}
					<div class="perfil__acciones">
						<Boton variante="primario" tipo="submit" disabled={guardandoIdentidad}>
							{#if guardandoIdentidad}<span class="spinner spinner--chico"></span> Guardando…{:else}
								Guardar corrección
							{/if}
						</Boton>
					</div>
				</form>
			</Tarjeta>

			<BajaCuenta />
		</div>
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

	/* Columna principal: datos de la cuenta y, debajo, la zona de baja. */
	.perfil__principal {
		flex: 999 1 560px;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: var(--e-6);
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

	.perfil__cabecera-texto {
		display: flex;
		flex-direction: column;
		gap: var(--e-1);
		min-width: 0;
	}

	.perfil__privacidad {
		max-width: 42ch;
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-tenue);
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

	.perfil__foto:focus-within .perfil__foto-boton {
		outline: 2px solid var(--acento);
		outline-offset: 2px;
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
