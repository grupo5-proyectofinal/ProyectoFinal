<script>
	import { cerrar, toasts } from '$lib/toast.svelte.js';
</script>

<div class="toasts" role="status" aria-live="polite">
	{#each toasts as aviso (aviso.id)}
		<div class="toast toast--{aviso.tipo}">
			<span>{aviso.mensaje}</span>
			<button
				class="toast__cerrar"
				type="button"
				onclick={() => cerrar(aviso.id)}
				aria-label="Cerrar aviso"
			>
				×
			</button>
		</div>
	{/each}
</div>

<style>
	.toasts {
		position: fixed;
		right: var(--e-4);
		bottom: var(--e-4);
		z-index: 60;
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		width: min(22rem, calc(100vw - 2rem));
		pointer-events: none;
	}

	.toast {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--e-3);
		padding: 0.7rem 0.8rem 0.7rem 1rem;
		border: 1px solid var(--linea);
		border-left: 3px solid var(--tinta-suave);
		border-radius: var(--radio-sm);
		background: var(--superficie);
		box-shadow: var(--sombra-md);
		font-size: var(--texto-sm);
		pointer-events: auto;
	}

	.toast--exito {
		border-left-color: var(--exito);
	}

	.toast--error {
		border-left-color: var(--peligro);
	}

	.toast--aviso {
		border-left-color: var(--alerta);
	}

	.toast--info {
		border-left-color: var(--acento);
	}

	.toast__cerrar {
		flex: none;
		width: 1.5rem;
		height: 1.5rem;
		display: grid;
		place-items: center;
		border: 0;
		border-radius: var(--radio-xs);
		background: transparent;
		color: var(--tinta-suave);
		font-size: 1.1rem;
		line-height: 1;
		cursor: pointer;
	}

	.toast__cerrar:hover {
		background: var(--superficie-alt);
		color: var(--tinta);
	}
</style>
