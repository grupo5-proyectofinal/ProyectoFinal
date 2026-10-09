<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { alPerderAcceso } from '$lib/admin.svelte.js';
	import { api, fieldErrors } from '$lib/api.js';
	import { session } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';

	let errors = $state({});
	let general = $state('');
	let enviando = $state(false);
	let nombreFoto = $state('');
	let form = $state();

	const generos = ['Femenino', 'Masculino', 'Otro', 'Prefiero no decir'];

	function alElegirFoto(event) {
		nombreFoto = event.target.files?.[0]?.name ?? '';
	}

	async function enviar(event) {
		event.preventDefault();
		errors = {};
		general = '';
		if (form.password.value !== form.password2.value) {
			errors = { password2: 'Las contraseñas no coinciden.' };
			return;
		}
		enviando = true;
		try {
			const data = new FormData(form);
			if (!data.get('foto')?.name) data.delete('foto');
			await api('/admin/usuarios/', { method: 'POST', body: data, form: true });
			notificar('Usuario creado.');
			goto(resolve('/admin/usuarios'));
		} catch (error) {
			if (error.status === 403) {
				alPerderAcceso();
				return;
			}
			errors = fieldErrors(error.data);
			if (!Object.keys(errors).length) general = 'No se pudo crear el usuario.';
		} finally {
			enviando = false;
		}
	}
</script>

<svelte:head>
	<title>Nuevo usuario — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Nuevo usuario</h1>
		<p>Creá una cuenta desde el panel; la persona entra con la clave que definas acá.</p>
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
{:else}
	<section class="panel formulario alta">
		<form bind:this={form} onsubmit={enviar}>
			<fieldset class="bloque">
				<legend>Cuenta</legend>
				<div class="grilla-campos">
					<div class="campo">
						<label for="email">Email <span aria-hidden="true">*</span></label>
						<input
							id="email"
							name="email"
							type="email"
							required
							autocomplete="email"
							spellcheck="false"
							aria-invalid={errors.email ? 'true' : undefined}
							aria-describedby={errors.email ? 'email-error' : undefined}
						/>
						{#if errors.email}<p class="error" id="email-error">{errors.email}</p>{/if}
					</div>
					<div class="campo">
						<label for="username">Nombre de usuario <span aria-hidden="true">*</span></label>
						<input
							id="username"
							name="username"
							type="text"
							required
							autocomplete="username"
							spellcheck="false"
							aria-invalid={errors.username ? 'true' : undefined}
							aria-describedby={errors.username ? 'username-error' : undefined}
						/>
						{#if errors.username}<p class="error" id="username-error">{errors.username}</p>{/if}
					</div>
					<div class="campo">
						<label for="password">Contraseña <span aria-hidden="true">*</span></label>
						<input
							id="password"
							name="password"
							type="password"
							required
							autocomplete="new-password"
							aria-invalid={errors.password ? 'true' : undefined}
							aria-describedby={errors.password ? 'password-error' : 'password-ayuda'}
						/>
						{#if errors.password}
							<p class="error" id="password-error">{errors.password}</p>
						{:else}
							<p class="ayuda" id="password-ayuda">Mínimo 8 caracteres, no muy común.</p>
						{/if}
					</div>
					<div class="campo">
						<label for="password2">Repetir contraseña <span aria-hidden="true">*</span></label>
						<input
							id="password2"
							name="password2"
							type="password"
							required
							autocomplete="new-password"
							aria-invalid={errors.password2 ? 'true' : undefined}
							aria-describedby={errors.password2 ? 'password2-error' : undefined}
						/>
						{#if errors.password2}
							<p class="error" id="password2-error">{errors.password2}</p>
						{/if}
					</div>
				</div>
			</fieldset>

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
							aria-invalid={errors.first_name ? 'true' : undefined}
							aria-describedby={errors.first_name ? 'first_name-error' : undefined}
						/>
						{#if errors.first_name}<p class="error" id="first_name-error">{errors.first_name}</p>{/if}
					</div>
					<div class="campo">
						<label for="last_name">Apellido</label>
						<input
							id="last_name"
							name="last_name"
							type="text"
							autocomplete="family-name"
							aria-invalid={errors.last_name ? 'true' : undefined}
							aria-describedby={errors.last_name ? 'last_name-error' : undefined}
						/>
						{#if errors.last_name}<p class="error" id="last_name-error">{errors.last_name}</p>{/if}
					</div>
					<div class="campo">
						<label for="dni">DNI <span aria-hidden="true">*</span></label>
						<input
							id="dni"
							name="dni"
							type="text"
							required
							inputmode="numeric"
							aria-invalid={errors.dni ? 'true' : undefined}
							aria-describedby={errors.dni ? 'dni-error' : undefined}
						/>
						{#if errors.dni}<p class="error" id="dni-error">{errors.dni}</p>{/if}
					</div>
					<div class="campo">
						<label for="telefono">Teléfono</label>
						<input
							id="telefono"
							name="telefono"
							type="tel"
							autocomplete="tel"
							aria-invalid={errors.telefono ? 'true' : undefined}
							aria-describedby={errors.telefono ? 'telefono-error' : undefined}
						/>
						{#if errors.telefono}<p class="error" id="telefono-error">{errors.telefono}</p>{/if}
					</div>
					<div class="campo">
						<label for="genero">Género</label>
						<select id="genero" name="genero">
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
							aria-invalid={errors.direccion ? 'true' : undefined}
							aria-describedby={errors.direccion ? 'direccion-error' : undefined}
						/>
						{#if errors.direccion}<p class="error" id="direccion-error">{errors.direccion}</p>{/if}
					</div>
					<div class="campo">
						<label for="ciudad">Ciudad</label>
						<input
							id="ciudad"
							name="ciudad"
							type="text"
							autocomplete="address-level2"
							aria-invalid={errors.ciudad ? 'true' : undefined}
							aria-describedby={errors.ciudad ? 'ciudad-error' : undefined}
						/>
						{#if errors.ciudad}<p class="error" id="ciudad-error">{errors.ciudad}</p>{/if}
					</div>
				</div>
			</fieldset>

			<fieldset class="bloque">
				<legend>Foto</legend>
				<div class="campo">
					<label for="foto">Foto de perfil (opcional)</label>
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
						<p class="ayuda" id="foto-ayuda">Se muestra en el perfil dentro de los pools.</p>
					{/if}
				</div>
			</fieldset>

			{#if errors.non_field_errors || general}
				<div class="alerta alerta--error aviso" role="alert">
					{errors.non_field_errors || general}
				</div>
			{/if}

			<button class="btn btn--primario" type="submit" disabled={enviando}>
				{#if enviando}<span class="spinner spinner--chico"></span> Creando usuario…{:else}Crear
					usuario{/if}
			</button>
		</form>
	</section>
{/if}

<style>
	.alta {
		max-width: 780px;
		margin: 0 auto;
		padding: clamp(1.25rem, 2.5vw, 1.75rem);
	}
</style>
