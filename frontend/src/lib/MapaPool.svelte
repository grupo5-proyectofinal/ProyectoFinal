<script>
	import L from 'leaflet';
	import 'leaflet/dist/leaflet.css';
	import icono from 'leaflet/dist/images/marker-icon.png';
	import icono2x from 'leaflet/dist/images/marker-icon-2x.png';
	import sombra from 'leaflet/dist/images/marker-shadow.png';

	let { lat, lng, titulo } = $props();
	let contenedor = $state();

	L.Icon.Default.mergeOptions({ iconUrl: icono, iconRetinaUrl: icono2x, shadowUrl: sombra });

	$effect(() => {
		if (!contenedor) return;
		const punto = [Number(lat), Number(lng)];
		const mapa = L.map(contenedor, { scrollWheelZoom: false }).setView(punto, 15);
		L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
			maxZoom: 19,
			attribution: '&copy; OpenStreetMap'
		}).addTo(mapa);
		L.marker(punto, { title: titulo }).addTo(mapa);
		return () => mapa.remove();
	});
</script>

<div
	class="mapa-pool"
	bind:this={contenedor}
	role="img"
	aria-label={`Mapa con la ubicación de ${titulo}`}
></div>

<style>
	.mapa-pool {
		position: relative;
		z-index: 0;
		width: 100%;
		height: 20rem;
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		overflow: hidden;
	}
</style>
