<script>
	// "Eliminar mi cuenta": pide la contraseña, avisa qué pools activos lo impiden
	// y, si sale bien, cierra la sesión y vuelve al inicio.
	import { goto } from '$app/navigation';
	import { fieldErrors } from '$lib/api.js';
	import { etiquetaEstado } from '$lib/estados.js';
	import { eliminarCuenta } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let abierto = $state(false);
	let password = $state('');
	let errors = $state({});
	let pools = $state([]);
	let enviando = $state(false);

	function cancelar() {
		abierto = false;
		password = '';
		errors = {};
		pools = [];
	}

	async function confirmar(event) {
		event.preventDefault();
		errors = {};
		pools = [];
		enviando = true;
		try {
			await eliminarCuenta(password);
			notificar('Tu cuenta fue eliminada.');
			await goto('/');
		} catch (error) {
			if (error.status === 401) return; // api.js ya avisó que la sesión expiró
			if (error.status === 409) pools = error.data?.pools ?? [];
			if (error.status === 429) {
				errors = { detail: 'Demasiados intentos. Probá de nuevo más tarde.' };
			} else {
				errors = fieldErrors(error.data);
				if (!Object.keys(errors).length) errors = { detail: 'No se pudo eliminar la cuenta.' };
			}
		} finally {
			enviando = false;
		}
	}
</script>

<Tarjeta class="baja">
	<section class="baja__cuerpo" aria-labelledby="baja-titulo">
		<h2 id="baja-titulo" class="baja__titulo">Eliminar mi cuenta</h2>
		<p class="baja__texto">
			Se borran tus datos personales, tu foto y tus notificaciones, y se cierra la sesión en todos
			tus dispositivos. Tus mensajes y reseñas en pools terminados quedan como "Usuario
			eliminado". No se puede deshacer.
		</p>

		{#if !abierto}
			<div class="baja__acciones">
				<button type="button" class="baja__peligro" onclick={() => (abierto = true)}>
					Eliminar mi cuenta
				</button>
			</div>
		{:else}
			<form class="baja__form" onsubmit={confirmar}>
				{#if errors.detail}
					<Aviso variante="error">
						<div>
							{errors.detail}
							{#if pools.length}
								<ul class="baja__pools">
									{#each pools as pool (pool.id)}
										<li>
											<a href="/pools/{pool.id}">{pool.titulo}</a>
											— {etiquetaEstado(pool.estado)}{pool.organizador ? ' (lo organizás vos)' : ''}
										</li>
									{/each}
								</ul>
							{/if}
						</div>
					</Aviso>
				{/if}
				<Campo
					id="baja-password"
					etiqueta="Confirmá con tu contraseña"
					error={errors.password}
					requerido
				>
					{#snippet children(props)}
						<input
							id="baja-password"
							type="password"
							autocomplete="current-password"
							required
							bind:value={password}
							{...props}
						/>
					{/snippet}
				</Campo>
				<div class="baja__acciones">
					<Boton variante="secundario" onclick={cancelar}>Cancelar</Boton>
					<button type="submit" class="baja__peligro" disabled={enviando || !password}>
						{#if enviando}<span class="spinner spinner--chico"></span> Eliminando…{:else}Eliminar
							definitivamente{/if}
					</button>
				</div>
			</form>
		{/if}
	</section>
</Tarjeta>

<style>
	:global(.baja.ui-tarjeta) {
		border-color: var(--borde-peligro);
	}

	.baja__cuerpo {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
		padding: var(--e-6);
	}

	.baja__titulo {
		margin: 0;
		font-size: var(--texto-md);
		color: var(--texto-peligro);
	}

	.baja__texto {
		margin: 0;
		color: var(--tinta-suave);
	}

	.baja__form {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
	}

	.baja__pools {
		margin: var(--e-2) 0 0;
		padding-left: 1.25rem;
	}

	.baja__acciones {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		gap: var(--e-3);
	}

	.baja__peligro {
		display: inline-flex;
		align-items: center;
		gap: var(--e-2);
		min-height: 44px;
		padding: 0 var(--e-5);
		border: 1px solid var(--peligro);
		border-radius: var(--radio-sm);
		background: var(--peligro);
		color: #fff;
		font: inherit;
		font-weight: 600;
		cursor: pointer;
	}

	.baja__peligro:hover:not(:disabled) {
		background: var(--peligro-fuerte);
	}

	.baja__peligro:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
