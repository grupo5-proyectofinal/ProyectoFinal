<script>
	import InfoAyuda from '$lib/InfoAyuda.svelte';
</script>

<!-- Qué pasa al llegar la fecha de caducidad (espeja el backend: 7 días de espera). -->
<InfoAyuda titulo="¿Qué pasa cuando caduca el pool?" etiqueta="¿Qué pasa cuando caduca el pool?">
	<strong>Es el último día para completar el cupo</strong>. Si llega y no
	se completó:
	<ul>
		<li>Sin participantes, se cancela solo.</li>
		<li>
			Con participantes, pasa a «Caducado»: vos decidís si extender el plazo o cancelarlo.
		</li>
		<li>Si no decidís en 7 días, se cancela.</li>
	</ul>
</InfoAyuda>
