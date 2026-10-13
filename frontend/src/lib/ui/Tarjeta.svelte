<script>
	// Primitiva Tarjeta: superficie con borde y sombra. Slot libre para el contenido.
	let { class: clase = '', children, ...rest } = $props();
</script>

<div class="ui-tarjeta {clase}" {...rest}>
	{@render children()}
</div>

<style>
	.ui-tarjeta {
		background: var(--superficie);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		box-shadow: var(--sombra-sm);
	}
</style>
