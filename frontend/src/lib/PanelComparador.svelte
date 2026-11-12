<script>
	// Comparador de costo final: el mismo producto en varias tiendas, ordenado por
	// lo que realmente se paga (precio + envío + impuestos + aduana estimada).
	// La API manda el cálculo; acá se muestra, se agregan ofertas y se actualizan precios.
	import { resolve } from '$app/paths';
	import { api, fieldErrors } from '$lib/api.js';
	import { confirmar } from '$lib/confirmacion.svelte.js';
	import {
		avisoMinimo,
		desglose,
		enlaceCrearPool,
		faltante,
		precioEnMoneda,
		puntosTendencia,
		variacion
	} from '$lib/comparador.js';
	import { fechaHora } from '$lib/historial.js';
	import { moneda } from '$lib/formato.js';
	import { notificar } from '$lib/toast.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';

	let { comparacion, onactualizar } = $props();

	const MONEDAS = ['ARS', 'USD', 'EUR'];

	const VACIA = {
		tienda: '',
		url: '',
		precio_unitario: '',
		moneda: 'ARS',
		cantidad_minima: 1,
		costo_envio: '',
		impuestos_pct: '',
		es_importacion: false,
		derechos_pct: '',
		notas: ''
	};

	let nueva = $state({ ...VACIA });
	let errores = $state({});
	let general = $state('');
	let ocupado = $state(false);
	let leyendo = $state(false);
	let formularioAbierto = $state(false);

	const resumen = $derived(comparacion.resumen ?? {});
	const ofertas = $derived(comparacion.ofertas ?? []);
	const hayAduana = $derived(ofertas.some((o) => o.costo?.aduana));

	async function recargar(datos) {
		onactualizar?.(datos ?? (await api(`/comparaciones/${comparacion.id}/`)));
	}

	async function autocompletar() {
		if (!nueva.url.trim()) return;
		leyendo = true;
		general = '';
		try {
			const vista = await api('/pools/previsualizar-enlace/', {
				method: 'POST',
				body: { enlace: nueva.url.trim() }
			});
			nueva.url = vista.enlace ?? nueva.url;
			if (!vista.encontrado) {
				general = vista.detail;
				return;
			}
			// Acá sí sirve el precio en otra moneda (el comparador lo convierte), pero
			// solo en las que se pueden elegir; si no, se carga a mano.
			const moneda = vista.moneda ?? 'ARS';
			const precio = vista.precio_unitario ?? vista.precio_moneda;
			if (precio && MONEDAS.includes(moneda)) {
				nueva.precio_unitario = precio;
				nueva.moneda = moneda;
			} else if (precio) {
				general = `La tienda publica el precio en ${moneda}: convertilo y cargalo a mano.`;
			}
		} catch (e) {
			general = fieldErrors(e.data).enlace ?? 'No pudimos leer ese enlace.';
		} finally {
			leyendo = false;
		}
	}

	async function agregar(evento) {
		evento.preventDefault();
		errores = {};
		general = '';
		ocupado = true;
		try {
			const cuerpo = { ...nueva, comparacion: comparacion.id };
			for (const campo of ['costo_envio', 'impuestos_pct', 'derechos_pct']) {
				if (cuerpo[campo] === '') cuerpo[campo] = 0;
			}
			await api('/ofertas/', { method: 'POST', body: cuerpo });
			nueva = { ...VACIA };
			formularioAbierto = false;
			notificar('Oferta agregada.');
			await recargar();
		} catch (e) {
			const { detail, non_field_errors, comparacion: deComparacion, ...porCampo } = fieldErrors(e.data);
			errores = porCampo;
			general = detail || non_field_errors || deComparacion || '';
		} finally {
			ocupado = false;
		}
	}

	async function quitar(oferta) {
		const aceptada = await confirmar({
			titulo: `¿Quitar la oferta de ${oferta.tienda}?`,
			descripcion: 'Se quita de esta comparación junto con su historial de precios.',
			confirmar: 'Quitar oferta'
		});
		if (!aceptada) return;
		try {
			await api(`/ofertas/${oferta.id}/`, { method: 'DELETE' });
			await recargar();
		} catch {
			notificar('No se pudo quitar la oferta.', 'error');
		}
	}

	async function cambiarCantidad(evento) {
		const cantidad = Number(evento.currentTarget.value);
		if (!cantidad || cantidad < 1 || cantidad === comparacion.cantidad) return;
		try {
			await api(`/comparaciones/${comparacion.id}/`, { method: 'PATCH', body: { cantidad } });
			await recargar();
		} catch {
			notificar('No se pudo cambiar la cantidad.', 'error');
		}
	}

	async function actualizarPrecios() {
		ocupado = true;
		try {
			const r = await api(`/comparaciones/${comparacion.id}/actualizar-precios/`, { method: 'POST' });
			const partes = [`${r.actualizadas} actualizada(s)`, `${r.sin_cambios} sin cambios`];
			if (r.fallidas.length) partes.push(`no se pudo leer: ${r.fallidas.join(', ')}`);
			notificar(`Precios: ${partes.join(' · ')}.`, r.fallidas.length ? 'aviso' : 'exito');
			await recargar(r.comparacion);
		} catch (e) {
			notificar(
				e?.status === 429 ? 'Esperá un rato antes de volver a actualizar.' : 'No se pudieron actualizar.',
				'error'
			);
		} finally {
			ocupado = false;
		}
	}
</script>

<section class="comparador" aria-labelledby={`comparador-${comparacion.id}`}>
	<div class="comparador__cabecera">
		<div>
			<h1 id={`comparador-${comparacion.id}`}>{comparacion.titulo}</h1>
			<p class="comparador__ayuda">
				Ordenado por costo total para
				{#if comparacion.puede_editar}
					<input
						class="comparador__cantidad"
						type="number"
						min="1"
						value={comparacion.cantidad}
						onchange={cambiarCantidad}
						aria-label="Cantidad a comprar"
					/>
				{:else}
					<strong>{comparacion.cantidad}</strong>
				{/if}
				{comparacion.cantidad === 1 ? 'unidad' : 'unidades'}, no por el precio publicado.
			</p>
		</div>
		{#if comparacion.puede_editar}
			<div class="comparador__acciones">
				<Boton variante="secundario" tamano="sm" disabled={ocupado || !ofertas.length} onclick={actualizarPrecios}>
					Actualizar precios
				</Boton>
				<Boton variante="primario" tamano="sm" onclick={() => (formularioAbierto = !formularioAbierto)}>
					{formularioAbierto ? 'Cerrar' : 'Agregar oferta'}
				</Boton>
			</div>
		{/if}
	</div>

	{#if ofertas.length}
		<dl class="tiles">
			<div class="tile">
				<dt>Ofertas</dt>
				<dd>{resumen.ofertas}</dd>
			</div>
			<div class="tile">
				<dt>Mejor costo total</dt>
				<dd>{moneda(resumen.mejor_total)}</dd>
			</div>
			<div class="tile">
				<dt>Promedio</dt>
				<dd>{moneda(resumen.promedio)}</dd>
			</div>
			<div class="tile">
				<dt>Ahorro vs. la más cara</dt>
				<dd>{resumen.ahorro ? moneda(resumen.ahorro) : '—'}</dd>
			</div>
		</dl>

		<div class="tabla-envoltura">
			<table class="tabla">
				<thead>
					<tr>
						<th scope="col">Tienda</th>
						<th scope="col" class="num">Precio publicado</th>
						<th scope="col" class="num col-secundaria">Envío</th>
						<th scope="col" class="num col-secundaria">Impuestos</th>
						{#if hayAduana}<th scope="col" class="num col-secundaria">Aduana <span class="estimado">(estim.)</span></th>{/if}
						<th scope="col" class="num">Costo total</th>
						<th scope="col" class="num">Por unidad</th>
						<th scope="col" class="col-secundaria">Tendencia</th>
						<th scope="col"><span class="visualmente-oculto">Acciones</span></th>
					</tr>
				</thead>
				<tbody>
					{#each ofertas as oferta (oferta.id)}
						{@const costo = oferta.costo}
						{@const puntos = puntosTendencia(oferta.historial)}
						<tr class:mejor={oferta.es_mejor}>
							<td>
								<div class="tienda">
									{#if oferta.url}
										<a href={oferta.url} target="_blank" rel="noopener noreferrer">{oferta.tienda}</a>
									{:else}
										<span>{oferta.tienda}</span>
									{/if}
									{#if oferta.es_mejor}<Badge variante="abierto">Más conveniente</Badge>{/if}
									{#if oferta.es_importacion}<Badge variante="neutro">Importación</Badge>{/if}
								</div>
								{#if faltante(costo)}
									<p class="nota nota--aviso">{faltante(costo)}</p>
								{:else}
									{#if avisoMinimo(costo, comparacion.cantidad)}
										<p class="nota">{avisoMinimo(costo, comparacion.cantidad)}</p>
									{/if}
									<details class="desglose">
										<summary>Ver desglose</summary>
										<ul>
											{#each desglose(costo) as fila (fila.rotulo)}
												<li>
													<span>{fila.rotulo}{#if fila.estimado} <span class="estimado">(estimado)</span>{/if}</span>
													<span class="num">{moneda(fila.valor)}</span>
												</li>
											{/each}
										</ul>
										{#if costo.tipo_cambio}
											<p class="nota">Tipo de cambio usado: {moneda(costo.tipo_cambio)} por {costo.moneda}.</p>
										{/if}
									</details>
								{/if}
								{#if oferta.notas}<p class="nota">{oferta.notas}</p>{/if}
							</td>
							<td class="num">{precioEnMoneda(oferta.precio_unitario, oferta.moneda)}</td>
							<td class="num col-secundaria">{costo.total === null ? '—' : moneda(costo.envio)}</td>
							<td class="num col-secundaria">{costo.total === null ? '—' : moneda(costo.impuestos)}</td>
							{#if hayAduana}<td class="num col-secundaria">{costo.aduana ? moneda(costo.aduana.total) : '—'}</td>{/if}
							<td class="num total">{moneda(costo.total)}</td>
							<td class="num">{moneda(costo.por_unidad)}</td>
							<td class="col-secundaria">
								{#if puntos.length > 1}
									<svg class="tendencia" viewBox="0 0 80 24" width="80" height="24" role="img" aria-label={variacion(oferta.historial)}>
										<polyline points={puntos.map((p) => `${p.x},${p.y}`).join(' ')} />
										<circle class="tendencia__fin" cx={puntos.at(-1).x} cy={puntos.at(-1).y} r="3" />
										{#each puntos as punto, i (i)}
											<circle class="tendencia__hover" cx={punto.x} cy={punto.y} r="8">
												<title>{fechaHora(punto.fecha)}: {precioEnMoneda(punto.precio, oferta.moneda)}</title>
											</circle>
										{/each}
									</svg>
									<span class="tendencia__texto">{variacion(oferta.historial)}</span>
								{:else}
									<span class="tendencia__texto">—</span>
								{/if}
							</td>
							<td>
								<div class="fila-acciones">
									<a class="enlace-accion" href={resolve(enlaceCrearPool(oferta, comparacion))}>Crear pool</a>
									{#if comparacion.puede_editar}
										<button type="button" class="enlace-accion enlace-accion--peligro" onclick={() => quitar(oferta)}>
											Quitar
										</button>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		{#if ofertas.length === 1}
			<p class="nota">
				Con una sola oferta todavía no hay comparación: agregá otra tienda para ver el ahorro.
			</p>
		{/if}
		{#if hayAduana}
			<p class="nota">
				La aduana es una estimación con valores de referencia (tipo de cambio y alícuotas que carga el
				equipo de PoolShop). El monto real depende del producto y del régimen de importación.
			</p>
		{/if}
	{:else}
		<p class="vacio">
			{comparacion.puede_editar
				? 'Agregá al menos dos ofertas del mismo producto para comparar.'
				: 'Todavía no hay ofertas cargadas.'}
		</p>
	{/if}

	{#if comparacion.puede_editar && (formularioAbierto || !ofertas.length)}
		<form class="nueva" onsubmit={agregar}>
			<h3>Nueva oferta</h3>
			<Campo id="oferta-url" etiqueta="Enlace" ayuda="Opcional." error={errores.url}>
				{#snippet children(props)}
					<!-- Como en Crear pool: el botón va al lado del campo. -->
					<div class="nueva__enlace">
						<input id="oferta-url" type="url" placeholder="https://…" bind:value={nueva.url} {...props} />
						<Boton variante="secundario" disabled={leyendo || !nueva.url} onclick={autocompletar}>
							{leyendo ? 'Leyendo…' : 'Autocompletar'}
						</Boton>
					</div>
				{/snippet}
			</Campo>
			<div class="nueva__grilla">
				<Campo id="oferta-tienda" etiqueta="Tienda" error={errores.tienda}>
					{#snippet children(props)}
						<input id="oferta-tienda" bind:value={nueva.tienda} maxlength="120" placeholder="Se completa con el sitio" {...props} />
					{/snippet}
				</Campo>
				<Campo id="oferta-precio" etiqueta="Precio por unidad" requerido error={errores.precio_unitario}>
					{#snippet children(props)}
						<input id="oferta-precio" type="number" min="0.01" step="0.01" required bind:value={nueva.precio_unitario} {...props} />
					{/snippet}
				</Campo>
				<Campo id="oferta-moneda" etiqueta="Moneda" error={errores.moneda}>
					{#snippet children(props)}
						<select id="oferta-moneda" bind:value={nueva.moneda} {...props}>
							<option value="ARS">ARS (pesos)</option>
							<option value="USD">USD (dólares)</option>
							<option value="EUR">EUR (euros)</option>
						</select>
					{/snippet}
				</Campo>
				<Campo id="oferta-minima" etiqueta="Compra mínima (u.)" error={errores.cantidad_minima}>
					{#snippet children(props)}
						<input id="oferta-minima" type="number" min="1" bind:value={nueva.cantidad_minima} {...props} />
					{/snippet}
				</Campo>
				<Campo id="oferta-envio" etiqueta="Envío total" error={errores.costo_envio}>
					{#snippet children(props)}
						<input id="oferta-envio" type="number" min="0" step="0.01" bind:value={nueva.costo_envio} placeholder="0" {...props} />
					{/snippet}
				</Campo>
				<Campo id="oferta-impuestos" etiqueta="Impuestos no incluidos (%)" error={errores.impuestos_pct}>
					{#snippet children(props)}
						<input id="oferta-impuestos" type="number" min="0" max="100" step="0.01" bind:value={nueva.impuestos_pct} placeholder="0" {...props} />
					{/snippet}
				</Campo>
			</div>
			<label class="check">
				<input type="checkbox" bind:checked={nueva.es_importacion} />
				Es una importación (estimar costos de aduana por separado)
			</label>
			{#if nueva.es_importacion}
				<div class="campo--corto">
					<Campo id="oferta-derechos" etiqueta="Derechos de importación (%)" error={errores.derechos_pct}>
						{#snippet children(props)}
							<input id="oferta-derechos" type="number" min="0" max="100" step="0.01" bind:value={nueva.derechos_pct} placeholder="0" {...props} />
						{/snippet}
					</Campo>
				</div>
			{/if}
			<Campo id="oferta-notas" etiqueta="Notas" error={errores.notas}>
				{#snippet children(props)}
					<input id="oferta-notas" bind:value={nueva.notas} maxlength="255" placeholder="Ej.: envío gratis desde 20 unidades" {...props} />
				{/snippet}
			</Campo>
			{#if general}<Aviso variante="aviso">{general}</Aviso>{/if}
			<div class="acciones">
				{#if ofertas.length}
					<Boton variante="secundario" onclick={() => (formularioAbierto = false)}>Cancelar</Boton>
				{/if}
				<Boton tipo="submit" variante="primario" disabled={ocupado}>Agregar a la comparación</Boton>
			</div>
		</form>
	{/if}
</section>

<style>
	.comparador {
		display: grid;
		gap: var(--e-4);
	}

	.comparador__cabecera {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: var(--e-3);
		align-items: flex-start;
	}

	.comparador__cabecera h1 {
		margin: 0;
		font-size: var(--texto-xl);
	}

	.comparador__ayuda {
		margin: var(--e-1) 0 0;
		color: var(--tinta-suave);
		font-size: var(--texto-sm);
	}

	.comparador__cantidad {
		width: 4.5rem;
		padding: 0.15rem 0.35rem;
	}

	.comparador__acciones {
		display: flex;
		gap: var(--e-2);
	}

	.tiles {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: var(--e-3);
		margin: 0;
	}

	.tile {
		padding: var(--e-3) var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
		background: var(--superficie);
	}

	.tile dt {
		font-size: var(--texto-sm);
		color: var(--tinta-tenue);
	}

	.tile dd {
		margin: var(--e-1) 0 0;
		font-size: 1.35rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		color: var(--tinta);
	}

	.tabla-envoltura {
		overflow-x: auto;
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
	}

	.tabla {
		width: 100%;
		min-width: 760px;
		border-collapse: collapse;
		font-size: var(--texto-sm);
	}

	/* En el celular quedan las columnas que deciden: tienda, costo total y por
	   unidad. El desglose sigue disponible en cada fila. */
	@media (max-width: 700px) {
		.tabla {
			min-width: 0;
		}

		.col-secundaria {
			display: none;
		}

		.tabla th,
		.tabla td {
			padding: 0.55rem 0.45rem;
		}

		.tabla .tienda {
			min-width: 7.5rem;
		}
	}

	.tabla th,
	.tabla td {
		padding: 0.65rem 0.75rem;
		border-bottom: 1px solid var(--linea);
		text-align: left;
		vertical-align: top;
	}

	.tabla thead th {
		font-weight: 600;
		color: var(--tinta-suave);
		background: var(--crema);
	}

	.tabla .num {
		text-align: right;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}

	.tabla .total {
		font-weight: 700;
		color: var(--tinta);
	}

	.tabla tr.mejor td {
		background: var(--exito-suave);
	}

	.tienda {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
		align-items: center;
		font-weight: 600;
	}

	.estimado,
	.nota {
		color: var(--tinta-tenue);
		font-weight: 400;
		font-size: var(--texto-xs);
	}

	.nota {
		margin: var(--e-1) 0 0;
	}

	.nota--aviso {
		color: var(--texto-alerta);
	}

	.desglose summary {
		margin-top: var(--e-1);
		color: var(--marca-fuerte);
		font-size: var(--texto-xs);
		font-weight: 600;
		cursor: pointer;
	}

	.desglose ul {
		margin: var(--e-1) 0 0;
		padding: 0;
		list-style: none;
		font-size: var(--texto-xs);
	}

	.desglose li {
		display: flex;
		justify-content: space-between;
		gap: var(--e-3);
		min-width: 14rem;
	}

	.tendencia {
		display: block;
		overflow: visible;
	}

	.tendencia polyline {
		fill: none;
		stroke: var(--tinta-suave);
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}

	.tendencia__fin {
		fill: var(--tinta-suave);
		stroke: var(--superficie);
		stroke-width: 2;
	}

	.tendencia__hover {
		fill: transparent;
		cursor: help;
	}

	.tendencia__texto {
		font-size: var(--texto-xs);
		color: var(--tinta-tenue);
	}

	.fila-acciones {
		display: grid;
		gap: var(--e-1);
	}

	.enlace-accion {
		border: 0;
		background: none;
		padding: 0;
		font: inherit;
		font-weight: 600;
		color: var(--marca-fuerte);
		text-align: left;
		cursor: pointer;
		white-space: nowrap;
	}

	.enlace-accion--peligro {
		color: var(--peligro);
	}

	.vacio {
		margin: 0;
		color: var(--tinta-suave);
	}

	.nueva {
		display: grid;
		gap: 0;
		padding: var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
		background: var(--crema);
	}

	.nueva h3 {
		margin: 0 0 var(--e-4);
	}

	.nueva__enlace {
		display: flex;
		gap: var(--e-2);
	}

	.nueva__enlace input {
		flex: 1;
		min-width: 0;
	}

	.nueva__grilla {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		column-gap: var(--e-3);
	}

	.campo--corto {
		max-width: 16rem;
	}

	.check {
		display: flex;
		gap: var(--e-2);
		align-items: center;
		margin-bottom: var(--e-4);
		font-size: var(--texto-sm);
	}

	.visualmente-oculto {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0 0 0 0);
		white-space: nowrap;
	}
</style>
