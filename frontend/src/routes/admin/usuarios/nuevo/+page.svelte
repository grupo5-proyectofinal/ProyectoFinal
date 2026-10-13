<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { alPerderAcceso } from '$lib/admin.svelte.js';
	import { api, fieldErrors } from '$lib/api.js';
	import { session } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

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
{:else}
	<Tarjeta class="formulario alta">
		<form bind:this={form} onsubmit={enviar}>
			<fieldset class="bloque">
				<legend>Cuenta</legend>
				<div class="grilla-campos">
					<Campo id="email" etiqueta="Email" requerido error={errors.email}>
						{#snippet children(props)}
							<input
								id="email"
								name="email"
								type="email"
								required
								autocomplete="email"
								spellcheck="false"
								{...props}
							/>
						{/snippet}
					</Campo>
					<Campo id="username" etiqueta="Nombre de usuario" requerido error={errors.username}>
						{#snippet children(props)}
							<input
								id="username"
								name="username"
								type="text"
								required
								autocomplete="username"
								spellcheck="false"
								{...props}
							/>
						{/snippet}
					</Campo>
					<Campo
						id="password"
						etiqueta="Contraseña"
						requerido
						ayuda="Mínimo 8 caracteres, no muy común."
						error={errors.password}
					>
						{#snippet children(props)}
							<input
								id="password"
								name="password"
								type="password"
								required
								autocomplete="new-password"
								{...props}
							/>
						{/snippet}
					</Campo>
					<Campo id="password2" etiqueta="Repetir contraseña" requerido error={errors.password2}>
						{#snippet children(props)}
							<input
								id="password2"
								name="password2"
								type="password"
								required
								autocomplete="new-password"
								{...props}
							/>
						{/snippet}
					</Campo>
				</div>
			</fieldset>

			<fieldset class="bloque">
				<legend>Datos personales</legend>
				<div class="grilla-campos">
					<Campo id="first_name" etiqueta="Nombre" error={errors.first_name}>
						{#snippet children(props)}
							<input
								id="first_name"
								name="first_name"
								type="text"
								autocomplete="given-name"
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
								{...props}
							/>
						{/snippet}
					</Campo>
					<Campo id="dni" etiqueta="DNI" requerido error={errors.dni}>
						{#snippet children(props)}
							<input id="dni" name="dni" type="text" required inputmode="numeric" {...props} />
						{/snippet}
					</Campo>
					<Campo id="telefono" etiqueta="Teléfono" error={errors.telefono}>
						{#snippet children(props)}
							<input
								id="telefono"
								name="telefono"
								type="tel"
								autocomplete="tel"
								{...props}
							/>
						{/snippet}
					</Campo>
					<Campo id="genero" etiqueta="Género" error={errors.genero}>
						{#snippet children(props)}
							<select id="genero" name="genero" {...props}>
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
								autocomplete="street-address"
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
								{...props}
							/>
						{/snippet}
					</Campo>
				</div>
			</fieldset>

			<fieldset class="bloque">
				<legend>Foto</legend>
				<Campo
					id="foto"
					etiqueta="Foto de perfil (opcional)"
					ayuda="Se muestra en el perfil dentro de los pools."
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

			{#if errors.non_field_errors || general}
				<Aviso variante="error">{errors.non_field_errors || general}</Aviso>
			{/if}

			<Boton variante="primario" tipo="submit" disabled={enviando}>
				{#if enviando}<span class="spinner spinner--chico"></span> Creando usuario…{:else}Crear
					usuario{/if}
			</Boton>
		</form>
	</Tarjeta>
{/if}

<style>
	/* La clase viaja a la primitiva Tarjeta (sin el scope de la página): el
	   selector :global va completo, como en las fases 3-5. */
	:global(.alta.ui-tarjeta) {
		max-width: 780px;
		margin-inline: auto;
	}
</style>
