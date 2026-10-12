<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { fieldErrors } from '$lib/api.js';
	import { register } from '$lib/session.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';

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
			await register(data, true);
			goto(resolve('/'));
		} catch (error) {
			errors = fieldErrors(error.data);
			if (!Object.keys(errors).length) general = 'No se pudo crear la cuenta.';
		} finally {
			enviando = false;
		}
	}
</script>

<svelte:head>
	<title>Crear cuenta — PoolShop</title>
</svelte:head>

<div class="acceso">
	<aside class="acceso__panel">
		<h1 class="acceso__titulo">Comprá en conjunto, <span>pagá menos</span></h1>
		<p class="acceso__bajada">Creá tu cuenta para sumarte a pools de tu zona o armar los tuyos.</p>
		<ul class="acceso__lista">
			<li>
				<span class="acceso__icono" aria-hidden="true">
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12z" />
						<circle cx="12" cy="9" r="2.5" />
					</svg>
				</span>
				Pools de tu ciudad, sin intermediarios
			</li>
			<li>
				<span class="acceso__icono" aria-hidden="true">
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1.1-4.4A8 8 0 1 1 21 12z" />
					</svg>
				</span>
				Chat con cada grupo para coordinar
			</li>
			<li>
				<span class="acceso__icono" aria-hidden="true">
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z" />
						<path d="M8.5 12.5l2.5 2.5 4.5-5" />
					</svg>
				</span>
				Seguí el estado de cada compra
			</li>
		</ul>
	</aside>

	<section class="acceso__card">
		<h2 class="acceso__titulo-card">Crear cuenta</h2>
		<p class="acceso__bajada">
			Los datos con <span aria-hidden="true">*</span> son obligatorios.
		</p>

		<form class="acceso__form" bind:this={form} onsubmit={enviar}>
			<div class="acceso__foto">
				<span class="acceso__foto-icono" aria-hidden="true">
					<svg
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.8"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M4 8h3l2-3h6l2 3h3v11H4z" />
						<circle cx="12" cy="13" r="3.5" />
					</svg>
				</span>
				<div>
					<input
						id="foto"
						class="archivo__input"
						name="foto"
						type="file"
						accept="image/*"
						onchange={alElegirFoto}
						aria-describedby="foto-ayuda"
					/>
					<label class="acceso__foto-boton" for="foto">Subir foto de perfil</label>
					<p class="acceso__foto-ayuda" id="foto-ayuda">
						{nombreFoto || 'Se muestra en tu perfil dentro de los pools.'}
					</p>
				</div>
			</div>

			<div class="acceso__grilla">
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

			{#if errors.non_field_errors || general}
				<Aviso variante="error">{errors.non_field_errors || general}</Aviso>
			{/if}

			<Boton
				variante="primario"
				tamano="lg"
				bloque
				tipo="submit"
				disabled={enviando}
				class="acceso__cta"
			>
				{#if enviando}<span class="spinner spinner--chico"></span> Creando cuenta…{:else}Crear
					cuenta{/if}
			</Boton>
		</form>

		<p class="acceso__pie">
			¿Ya tenés cuenta? <a href={resolve('/login')}>Ingresá</a>.
		</p>
	</section>
</div>

<style>
	.acceso {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		gap: 36px;
	}

	.acceso__panel {
		display: flex;
		flex: 1 1 380px;
		flex-direction: column;
		gap: var(--e-4);
		min-width: 0;
		padding: 40px;
		border-radius: var(--radio-lg);
		background: var(--melocoton-fuerte);
	}

	.acceso__titulo {
		font-size: clamp(1.9rem, 3vw, 2.75rem);
		letter-spacing: -0.03em;
		line-height: 1.05;
	}

	.acceso__titulo span {
		color: var(--marca);
	}

	.acceso__bajada {
		margin: 0;
		max-width: 46ch;
		font-size: 1.0625rem;
		line-height: 1.5;
		color: var(--tinta-suave);
	}

	.acceso__lista {
		display: flex;
		flex-direction: column;
		gap: 14px;
		margin: var(--e-2) 0 0;
		padding: 0;
		list-style: none;
	}

	.acceso__lista li {
		display: flex;
		align-items: center;
		gap: 12px;
		font-size: var(--texto-base);
	}

	.acceso__icono {
		display: grid;
		place-items: center;
		flex: none;
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: var(--superficie);
		color: var(--marca);
	}

	.acceso__icono svg {
		width: 18px;
		height: 18px;
	}

	.acceso__card {
		display: flex;
		flex: 999 1 520px;
		flex-direction: column;
		min-width: 0;
		padding: 32px;
		border: 1px solid var(--linea);
		border-radius: var(--radio-lg);
		background: var(--superficie);
	}

	.acceso__titulo-card {
		font-size: clamp(1.5rem, 2.1vw, 1.75rem);
	}

	.acceso__card .acceso__bajada {
		margin-top: var(--e-2);
		margin-bottom: var(--e-5);
	}

	.acceso__form {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
	}

	/* Fila de foto del mockup 14: círculo punteado + botón + nombre del archivo. */
	.acceso__foto {
		display: flex;
		align-items: center;
		gap: var(--e-4);
	}

	.acceso__foto-icono {
		display: grid;
		place-items: center;
		flex: none;
		width: 76px;
		height: 76px;
		border: 2px dashed var(--melocoton-avatar);
		border-radius: 50%;
		background: var(--crema);
		color: var(--acento-naranja);
	}

	.acceso__foto-icono svg {
		width: 28px;
		height: 28px;
	}

	.acceso__foto-boton {
		display: inline-flex;
		align-items: center;
		min-height: 40px;
		padding: 0 14px;
		border: 1px solid var(--linea-fuerte);
		border-radius: var(--radio-xs);
		background: var(--superficie);
		color: var(--tinta);
		font-size: var(--texto-sm);
		font-weight: 700;
		cursor: pointer;
		transition:
			border-color var(--transicion),
			background-color var(--transicion),
			color var(--transicion);
	}

	.acceso__foto-boton:hover {
		border-color: var(--marca);
		background: var(--melocoton);
		color: var(--marca-fuerte);
	}

	.acceso__foto-boton:focus-visible {
		outline: 2px solid var(--acento);
		outline-offset: 2px;
	}

	.acceso__foto-ayuda {
		margin: 6px 0 0;
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
		overflow-wrap: anywhere;
	}

	.acceso__grilla {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: var(--e-4);
	}

	.acceso__grilla :global(.ui-campo) {
		margin-bottom: 0;
	}

	/* Métricas del mockup 14 (48px / 10px) sobre los controles de la card. */
	.acceso__grilla input,
	.acceso__grilla select {
		min-height: 48px;
		font-size: 0.9375rem;
	}

	:global(.acceso__cta.ui-boton) {
		min-height: 54px;
		border-radius: var(--radio);
		font-size: var(--texto-md);
	}

	.acceso__pie {
		margin-top: var(--e-5);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	@media (max-width: 800px) {
		.acceso {
			gap: var(--e-5);
		}

		.acceso__panel {
			order: 1;
			padding: var(--e-5);
		}

		.acceso__card {
			padding: var(--e-5);
		}
	}
</style>
