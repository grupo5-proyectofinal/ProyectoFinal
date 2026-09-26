<script>
	import { resolve } from '$app/paths';
	import { etiquetaEstado } from '$lib/estados.js';

	let { pool } = $props();
</script>

<article class="card">
	{#if pool.imagenes?.length}
		<img class="card-img" src={pool.imagenes[0].imagen} alt={pool.titulo} />
	{:else}
		<div class="card-img sin-img">Sin imagen</div>
	{/if}
	<div class="card-body">
		<span class="badge badge-{pool.estado}">{etiquetaEstado(pool.estado)}</span>
		<h3>{pool.titulo}</h3>
		<p class="muted">{pool.nombre_producto}</p>
		<p>$ {pool.precio_unitario} · disponible {pool.disponible}/{pool.cantidad_total}</p>
		<p class="muted">Por {pool.creador.username}</p>
		<a class="btn secundario" href={resolve(`/pools/${pool.id}`)}>VER</a>
	</div>
</article>
