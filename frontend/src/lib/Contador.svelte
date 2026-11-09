<script>
	// Número que sube desde 0 hasta su valor al aparecer (y acompaña si cambia).
	// Los lectores de pantalla leen solo el valor final.
	import { cubicOut } from 'svelte/easing';
	import { Tween } from 'svelte/motion';
	import { duracion } from '$lib/movimiento.js';

	let { valor = 0 } = $props();

	const numero = new Tween(0, { easing: cubicOut });

	$effect(() => {
		const destino = Number(valor) || 0;
		numero.set(destino, { duration: duracion(Math.min(1200, 500 + destino * 40)) });
	});
</script>

<span aria-hidden="true">{Math.round(numero.current)}</span><span class="sr-only">{valor}</span>
