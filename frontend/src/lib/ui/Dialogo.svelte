<script>
	import Boton from './Boton.svelte';

	// Diálogo modal nativo: atrapa el foco, cierra con Esc y devuelve el foco al
	// elemento que lo abrió. El estado vive en quien lo usa (`abierto`).
	let {
		abierto = false,
		titulo,
		descripcion = '',
		confirmar = 'Confirmar',
		cancelar = 'Cancelar',
		variante = 'primario',
		onconfirmar,
		oncancelar,
		children
	} = $props();

	let dialogo = $state();

	$effect(() => {
		if (!dialogo) return;
		if (abierto && !dialogo.open) dialogo.showModal();
		else if (!abierto && dialogo.open) dialogo.close();
	});

	function alCerrar() {
		// Esc o cierre nativo: avisar para que el estado del padre acompañe.
		if (abierto) oncancelar?.();
	}
</script>

<dialog class="dialogo" bind:this={dialogo} onclose={alCerrar}>
	<div class="dialogo__caja">
		<h2 class="dialogo__titulo">{titulo}</h2>
		{#if descripcion}
			<p class="dialogo__texto">{descripcion}</p>
		{/if}
		{@render children?.()}
		<div class="dialogo__acciones">
			<Boton variante="secundario" onclick={oncancelar}>{cancelar}</Boton>
			<Boton variante={variante} onclick={onconfirmar}>{confirmar}</Boton>
		</div>
	</div>
</dialog>

<style>
	.dialogo {
		width: min(30rem, calc(100vw - 2rem));
		max-width: none;
		padding: 0;
		border: 0;
		border-radius: var(--radio-lg);
		background: var(--superficie);
		color: var(--tinta);
		box-shadow: var(--sombra-lg, 0 24px 60px rgba(31, 21, 18, 0.24));
	}

	.dialogo::backdrop {
		background: rgba(31, 21, 18, 0.5);
		backdrop-filter: blur(2px);
	}

	.dialogo__caja {
		display: flex;
		flex-direction: column;
		gap: var(--e-3);
		padding: var(--e-6);
	}

	.dialogo__titulo {
		margin: 0;
		font-family: var(--fuente-display);
		font-size: var(--texto-lg);
	}

	.dialogo__texto {
		margin: 0;
		color: var(--tinta-suave);
	}

	.dialogo__acciones {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		gap: var(--e-3);
		margin-top: var(--e-2);
	}
</style>
