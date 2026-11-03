<script>
	// Puntaje de solo lectura (1 a 5) como estrellas; el texto accesible lo dice en palabras.
	import { estrellas } from '$lib/resenas.js';

	let { puntaje, tamano = 14 } = $props();

	const posiciones = $derived(estrellas(puntaje));
	const etiqueta = $derived(`${Math.round(Number(puntaje) || 0)} de 5 estrellas`);
</script>

<span class="estrellas" role="img" aria-label={etiqueta}>
	{#each posiciones as llena, i (i)}
		<svg
			width={tamano}
			height={tamano}
			viewBox="0 0 24 24"
			class:estrellas__llena={llena}
			aria-hidden="true"
		>
			<path d="M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4l-5.9 3.1 1.2-6.5L2.5 9.4l6.6-.9z" />
		</svg>
	{/each}
</span>

<style>
	.estrellas {
		display: inline-flex;
		gap: 1px;
		vertical-align: middle;
	}

	svg {
		fill: var(--linea-fuerte);
	}

	.estrellas__llena {
		fill: var(--acento-naranja);
	}
</style>
