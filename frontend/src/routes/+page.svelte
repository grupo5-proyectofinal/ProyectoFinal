<script>
	import { resolve } from '$app/paths';
	import { session } from '$lib/session.svelte.js';
</script>

<section class="tarjeta">
	<h1>Comprá en grupo, pagá menos</h1>
	<p class="muted">
		PoolShop organiza compras colectivas: creás un pool, se suman vecinos y compran al por
		mayor.
	</p>
	{#if session.access}
		<p>Hola{session.user?.first_name ? `, ${session.user.first_name}` : ''}.</p>
		<a class="btn" href={resolve('/perfil')}>Mi perfil</a>
	{:else}
		<a class="btn" href={resolve('/registro')}>Crear cuenta</a>
		<a class="btn secundario" href={resolve('/login')}>Ingresar</a>
	{/if}
</section>
