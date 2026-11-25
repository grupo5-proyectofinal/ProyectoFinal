<script>
	// Primitiva Campo: dueña de la etiqueta, ayuda, error y del wiring ARIA.
	// El caller suelta el control en el slot y solo esparce `{...controlProps}`
	// sobre el input: no escribe `aria-describedby` ni `aria-invalid` a mano.
	// `info`: explicación del campo detrás de un ícono (?) junto a la etiqueta. Un texto
	// arma el diálogo con el nombre del campo; un snippet trae su propio diálogo.
	import InfoAyuda from '$lib/InfoAyuda.svelte';
	import { animarUnaVez, prefiereMenosMovimiento } from '$lib/movimiento.js';

	let { id, etiqueta, ayuda, error, info, requerido = false, children } = $props();

	let raiz = $state();
	let teniaError = false;

	// Cuando aparece un error: el campo se sacude y, si es el primero con error
	// del formulario, se lo lleva a la vista (en celular suele quedar fuera).
	$effect(() => {
		const hayError = Boolean(error);
		if (hayError && !teniaError && raiz) {
			animarUnaVez(raiz, 'sacudir');
			const contenedor = raiz.closest('form') ?? document;
			if (contenedor.querySelector('.ui-campo--error') === raiz) llevarALaVista(contenedor);
		}
		teniaError = hayError;
	});

	function llevarALaVista(contenedor) {
		const rect = raiz.getBoundingClientRect();
		if (rect.top < 80 || rect.bottom > window.innerHeight) {
			raiz.scrollIntoView({
				block: 'center',
				behavior: prefiereMenosMovimiento() ? 'auto' : 'smooth'
			});
		}
		// Solo se mueve el foco si venía del botón de enviar (no se le saca a quien escribe).
		const activo = document.activeElement;
		// El botón de enviar puede estar fuera del <form> y usar form="...".
		const desdeEnvio =
			!activo ||
			activo === document.body ||
			(activo.type === 'submit' &&
				(contenedor === document
					? document.contains(activo)
					: contenedor.contains(activo) || activo.form === contenedor));
		if (desdeEnvio) raiz.querySelector('input, select, textarea')?.focus({ preventScroll: true });
	}

	const descrito = $derived(
		[ayuda ? `${id}-ayuda` : null, error ? `${id}-error` : null].filter(Boolean).join(' ') ||
			undefined
	);
	const invalid = $derived(error ? true : undefined);
</script>

<div class="ui-campo" class:ui-campo--error={error} bind:this={raiz}>
	<div class="ui-campo__cabecera">
		<label class="ui-campo__etiqueta" for={id}>
			{etiqueta}
			{#if requerido}<span class="ui-campo__requerido" aria-hidden="true"> *</span>{/if}
		</label>
		{#if typeof info === 'function'}
			{@render info()}
		{:else if info}
			<InfoAyuda titulo={etiqueta} etiqueta={`Qué es «${etiqueta}»`}>{info}</InfoAyuda>
		{/if}
	</div>
	{@render children({ 'aria-describedby': descrito, 'aria-invalid': invalid })}
	{#if ayuda}<p id={`${id}-ayuda`} class="ui-campo__ayuda">{ayuda}</p>{/if}
	{#if error}<p id={`${id}-error`} class="ui-campo__error" role="alert">{error}</p>{/if}
</div>

<style>
	.ui-campo {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		margin-bottom: var(--e-4);
	}

	.ui-campo__cabecera {
		display: flex;
		align-items: center;
		gap: var(--e-1);
	}

	/* El ícono no agranda la fila de la etiqueta. */
	.ui-campo__cabecera :global(.info__boton) {
		width: 1.75rem;
		height: 1.75rem;
		margin-block: -0.4rem;
	}

	.ui-campo__cabecera :global(.info__boton svg) {
		width: 1.1rem;
		height: 1.1rem;
	}

	.ui-campo__etiqueta {
		font-size: var(--texto-sm);
		font-weight: 600;
		color: var(--tinta);
	}

	.ui-campo__requerido {
		color: var(--marca);
	}

	.ui-campo__ayuda {
		margin: 0;
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
	}

	.ui-campo__error {
		margin: 0;
		font-size: var(--texto-xs);
		font-weight: 500;
		color: var(--peligro);
	}
</style>
