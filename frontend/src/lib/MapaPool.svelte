<script>
	// Mapa Leaflet/OSM. El marcador es un pin propio (divIcon) con la marca del
	// sistema nuevo; los controles de Leaflet se re-tiñen con :global deliberado
	// (su DOM lo crea la librería fuera del scope de este componente).
	import L from 'leaflet';
	import 'leaflet/dist/leaflet.css';

	let { lat, lng, titulo } = $props();
	let contenedor = $state();

	const PIN = L.divIcon({
		className: 'mapa-pool__pin',
		html: '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12z" fill="#de3535" stroke="#ffffff" stroke-width="1.6"></path><circle cx="12" cy="9" r="2.6" fill="#ffffff"></circle></svg>',
		iconSize: [34, 34],
		iconAnchor: [17, 32]
	});

	$effect(() => {
		if (!contenedor) return;
		const punto = [Number(lat), Number(lng)];
		const mapa = L.map(contenedor, { scrollWheelZoom: false }).setView(punto, 15);
		L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
			maxZoom: 19,
			attribution: '&copy; OpenStreetMap'
		}).addTo(mapa);
		L.marker(punto, { title: titulo, icon: PIN, alt: `Ubicación de ${titulo}` }).addTo(mapa);
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
		border-radius: 18px;
		overflow: hidden;
	}

	:global(.mapa-pool .leaflet-control-zoom a) {
		background: var(--superficie);
		border-color: var(--linea);
		color: var(--tinta);
	}

	:global(.mapa-pool .leaflet-control-zoom a:hover) {
		background: var(--melocoton);
		color: var(--marca-fuerte);
	}

	:global(.mapa-pool .leaflet-control-attribution) {
		background: rgba(255, 255, 255, 0.85);
		color: var(--tinta-suave);
		font-size: 0.68rem;
	}

	:global(.mapa-pool .leaflet-control-attribution a) {
		color: var(--marca-fuerte);
	}
</style>
