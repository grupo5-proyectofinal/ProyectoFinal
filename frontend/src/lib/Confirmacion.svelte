<script>
	// Diálogo de confirmación compartido: se monta una vez en el layout.
	import { confirmacion, responder } from '$lib/confirmacion.svelte.js';
	import Dialogo from '$lib/ui/Dialogo.svelte';
</script>

<Dialogo
	abierto={confirmacion.abierta}
	titulo={confirmacion.titulo}
	descripcion={confirmacion.descripcion}
	confirmar={confirmacion.confirmar}
	variante={confirmacion.variante}
	oncancelar={() => responder(false)}
	onconfirmar={() => responder(true)}
/>
