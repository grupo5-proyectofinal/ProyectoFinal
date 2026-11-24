<script>
	import { api } from '$lib/api.js';
	import { DEMORA_MS, consultaDireccion, moverActivo } from '$lib/direcciones.js';

	// Campo de dirección con sugerencias mientras se escribe la calle (servicio externo,
	// vía el backend). Si el servicio falla o no hay resultados, se escribe a mano como siempre.
	// El valor vive en el propio <input> (el formulario lo lee con FormData).
	let { id, name, ciudad = '', onelegir, ...resto } = $props();

	let entrada = $state();
	let sugerencias = $state([]);
	let abierto = $state(false);
	let activo = $state(-1);
	let pedido = 0;
	let temporizador;

	$effect(() => () => clearTimeout(temporizador));

	function alEscribir() {
		clearTimeout(temporizador);
		const consulta = consultaDireccion(entrada.value, ciudad);
		if (!consulta) return cerrar();
		temporizador = setTimeout(() => buscar(consulta), DEMORA_MS);
	}

	async function buscar(consulta) {
		const actual = ++pedido;
		try {
			const r = await api('/pools/buscar-direccion/', { query: { q: consulta } });
			if (actual !== pedido) return;
			sugerencias = Array.isArray(r) ? r : [];
			activo = -1;
			abierto = sugerencias.length > 0;
		} catch {
			if (actual === pedido) cerrar();
		}
	}

	function cerrar() {
		pedido += 1;
		sugerencias = [];
		abierto = false;
		activo = -1;
	}

	function elegir(sugerencia) {
		entrada.value = sugerencia.direccion;
		cerrar();
		onelegir?.(sugerencia);
	}

	function alTeclear(event) {
		if (!abierto) return;
		if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
			event.preventDefault();
			activo = moverActivo(activo, sugerencias.length, event.key);
		} else if (event.key === 'Enter' && activo >= 0) {
			// Elegir una sugerencia no debe avanzar de paso ni enviar el formulario.
			event.preventDefault();
			event.stopPropagation();
			elegir(sugerencias[activo]);
		} else if (event.key === 'Escape') {
			cerrar();
		}
	}
</script>

<div class="direccion">
	<input
		bind:this={entrada}
		{id}
		{name}
		type="text"
		role="combobox"
		autocomplete="off"
		aria-autocomplete="list"
		aria-expanded={abierto}
		aria-controls="{id}-sugerencias"
		aria-activedescendant={activo >= 0 ? `${id}-sugerencia-${activo}` : undefined}
		oninput={alEscribir}
		onkeydown={alTeclear}
		onblur={() => setTimeout(cerrar, 150)}
		{...resto}
	/>
	{#if abierto}
		<ul class="direccion__lista" id="{id}-sugerencias" role="listbox" aria-label="Direcciones sugeridas">
			{#each sugerencias as sugerencia, i (sugerencia.etiqueta)}
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<li
					id="{id}-sugerencia-{i}"
					role="option"
					aria-selected={i === activo}
					class:activa={i === activo}
					onmousedown={(event) => {
						event.preventDefault();
						elegir(sugerencia);
					}}
				>
					<strong>{sugerencia.direccion}</strong>
					{#if sugerencia.ciudad}<span>{sugerencia.ciudad}</span>{/if}
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.direccion {
		position: relative;
	}

	.direccion__lista {
		position: absolute;
		z-index: 20;
		top: calc(100% + 4px);
		left: 0;
		right: 0;
		margin: 0;
		padding: var(--e-1);
		list-style: none;
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
		background: var(--superficie);
		box-shadow: 0 8px 24px rgba(31, 21, 18, 0.14);
		max-height: 16rem;
		overflow-y: auto;
	}

	.direccion__lista li {
		display: flex;
		flex-direction: column;
		padding: var(--e-2) var(--e-3);
		border-radius: var(--radio-sm);
		cursor: pointer;
	}

	.direccion__lista li span {
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
	}

	.direccion__lista li:hover,
	.direccion__lista li.activa {
		background: var(--crema);
	}
</style>
