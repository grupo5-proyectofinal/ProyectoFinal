<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { rutaTab } from '$lib/pestanas.js';

	$effect(() => {
		goto(resolve(rutaTab('unidos')), { replaceState: true });
	});
</script>

<svelte:head>
	<title>Unidos — PoolShop</title>
</svelte:head>

<p class="sr-only" role="status">Redirigiendo a Unidos…</p>
