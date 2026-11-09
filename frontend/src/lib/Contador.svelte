<script>
	// Número que acompaña los cambios de valor. Arranca en el valor real para
	// que el HTML sin JS (y el SSR) no muestre un 0.
	import { cubicOut } from 'svelte/easing';
	import { Tween } from 'svelte/motion';
	import { duracion } from '$lib/movimiento.js';

	let { valor = 0 } = $props();

	const inicial = Number(valor) || 0;
	const numero = new Tween(inicial, { easing: cubicOut });
	let previo = inicial;

	$effect(() => {
		const destino = Number(valor) || 0;
		if (destino === previo) return;
		previo = destino;
		numero.set(destino, { duration: duracion(Math.min(1200, 500 + destino * 40)) });
	});
</script>

<span aria-hidden="true">{Math.round(numero.current)}</span><span class="sr-only">{valor}</span>
