<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { onMount, tick } from 'svelte';
	import { api, fieldErrors } from '$lib/api.js';
	import { aplicarBorrador, borrarBorrador, guardarBorrador, leerBorrador } from '$lib/borrador.js';
	import { moneda } from '$lib/formato.js';
	import {
		camposDesdeVistaPrevia,
		enlaceAnalizable,
		precioTotal
	} from '$lib/producto.js';
	import { mapaDesdeReparto, repartoDesdeMapa } from '$lib/variantes.js';
	import { session } from '$lib/session.svelte.js';
	import { motivoImagen } from '$lib/imagenes.js';
	import { animarUnaVez, prefiereMenosMovimiento } from '$lib/movimiento.js';
	import { notificar } from '$lib/toast.svelte.js';
	import PanelEnlace from '$lib/PanelEnlace.svelte';
	import SelectorCategoria from '$lib/SelectorCategoria.svelte';
	import PoolCard from '$lib/PoolCard.svelte';
	import RepartoVariantes from '$lib/RepartoVariantes.svelte';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Pasos from '$lib/ui/Pasos.svelte';

	const MAX_IMAGENES = 10;

	let categorias = $state([]);
	let errorCategorias = $state(false);
	let archivos = $state([]);
	let previews = $state([]);
	let errors = $state({});
	let general = $state('');
	let enviando = $state(false);
	let form = $state();
	// Valores vivos del form, solo para la vista previa: el envío sigue leyendo
	// `FormData(form)` como antes.
	let datos = $state({});
	// Autocompletado desde el enlace de la tienda.
	let vistaPrevia = $state(null);
	// Validaciones del sitio (https, acortadores, dominio raro…) antes de publicar.
	let analisisEnlace = $state(null);
	let analizando = $state(false);
	let avisoEnlace = $state('');
	let usarImagen = $state(true);
	let ultimoAnalizado = '';
	let pedidoEnlace = 0;
	// Categoría (dos niveles) y variantes ofrecidas: el selector las expone como
	// inputs ocultos `categoria` y `atributos` dentro del form.
	let categoriaId = $state('');
	let atributos = $state({});
	let reparto = $state({});
	// Borrador en sessionStorage: sobrevive a un login en el medio.
	const BORRADOR = 'pool-nuevo';
	let borradorRestaurado = $state(false);
	let borradorListo = false;

	const TIPOS_PAGO = [
		['transferencia', 'Transferencia'],
		['sin_especificar', 'Sin especificar']
	];

	// Tres pasos reales sobre los cinco bloques del formulario: el usuario ve una
	// decisión por vez en lugar de un índice que salta a un formulario completo.
	const PASOS = [
		{ id: 'producto', titulo: 'Producto', campos: ['titulo', 'nombre_producto', 'precio_unitario'] },
		{
			id: 'cantidades',
			titulo: 'Cantidades y plazo',
			campos: ['cantidad_total', 'cantidad_creador', 'min_por_integrante', 'fecha_caducidad']
		},
		{ id: 'entrega', titulo: 'Entrega y pago', campos: ['direccion', 'ciudad'] },
		{ id: 'fotos', titulo: 'Fotos y descripción', campos: [] }
	];
	let paso = $state(0);
	// Campos que completó el autocompletado: se nombran para que la persona sepa
	// qué revisar, y para no pisar lo que escribió a mano.
	let completados = $state([]);
	const ultimoAutocompletado = {};
	const pagoTransferencia = $derived(datos.tipo_pago === 'transferencia');

	$effect(() => {
		api('/categories/')
			.then((r) => {
				categorias = r.results ?? r;
				errorCategorias = false;
			})
			.catch(() => {
				errorCategorias = true;
			})
			// Con las opciones de categoría ya en el DOM, se puede restaurar el borrador.
			.finally(restaurarBorrador);
	});

	async function restaurarBorrador() {
		// El $effect de categorías vuelve a correr cuando cambia el token (renovación,
		// sesión vencida): el borrador se restaura una sola vez, al entrar.
		if (borradorListo) return;
		await tick();
		// Si vino desde un mayorista o el comparador, eso manda sobre un borrador viejo.
		if (form && precargarDesdeUrl()) {
			borradorListo = true;
			return;
		}
		const borrador = leerBorrador(BORRADOR);
		if (form && borrador && aplicarBorrador(form.elements, borrador)) {
			// Los inputs ocultos del selector no alcanzan: su estado vive en el componente.
			categoriaId = borrador.categoria ?? '';
			try {
				atributos = JSON.parse(borrador.atributos || '{}');
				reparto = mapaDesdeReparto(JSON.parse(borrador.reparto || '[]'));
			} catch {
				atributos = {};
				reparto = {};
			}
			borradorRestaurado = true;
			alInput();
		}
		borradorListo = true;
	}

	// Desde un mayorista o el comparador ("Crear pool con esta oferta"). Devuelve
	// true si precargó algo.
	const LARGOS = { enlace: 2000 };
	function precargarDesdeUrl() {
		const params = page.url.searchParams;
		const campos = {
			enlace: params.get('enlace'),
			nombre_producto: params.get('producto'),
			titulo: params.get('producto'),
			precio_unitario: params.get('precio'),
			cantidad_total: params.get('cantidad')
		};
		let alguno = false;
		for (const [nombre, valor] of Object.entries(campos)) {
			if (valor && form.elements[nombre]) {
				form.elements[nombre].value = valor.slice(0, LARGOS[nombre] ?? 200);
				alguno = true;
			}
		}
		if (!alguno) return false;
		alInput();
		// El análisis del sitio sirve igual; el precio que ya vino no se pisa.
		if (campos.enlace) analizarEnlace({ conservarPrecio: Boolean(campos.precio_unitario) });
		return true;
	}

	function descartarBorrador() {
		borrarBorrador(BORRADOR);
		form?.reset();
		categoriaId = '';
		atributos = {};
		reparto = {};
		borradorRestaurado = false;
		alInput();
	}

	// El `input` burbujea: un solo handler mantiene la vista previa sincronizada
	// (incluido el precio total, que se deriva de `datos`).
	async function alInput() {
		if (!form) return;
		// Los inputs ocultos del selector de categoría se actualizan en el próximo tick.
		await tick();
		datos = Object.fromEntries(new FormData(form));
		if (categoriaId && errors.categoria) {
			errors = { ...errors, categoria: undefined };
		}
		// No pisar el borrador guardado antes de haberlo restaurado.
		if (borradorListo) guardarBorrador(BORRADOR, datos);
	}

	async function analizarEnlace({ forzar = false, conservarPrecio = false } = {}) {
		const enlace = form?.elements.enlace.value.trim() ?? '';
		if (!enlaceAnalizable(enlace)) {
			// El panel de confianza es del enlace anterior: no aplica al campo vacío o inválido.
			analisisEnlace = null;
			ultimoAnalizado = '';
			if (forzar) avisoEnlace = 'Pegá un enlace que empiece con https://';
			return;
		}
		if (!forzar && enlace === ultimoAnalizado) return;
		ultimoAnalizado = enlace;
		const actual = ++pedidoEnlace;
		analizando = true;
		avisoEnlace = '';
		try {
			const vista = await api('/pools/previsualizar-enlace/', {
				method: 'POST',
				body: { enlace }
			});
			if (actual !== pedidoEnlace) return;
			analisisEnlace = vista.analisis ?? null;
			// El servidor devuelve el enlace sin parámetros de seguimiento: se guarda ese.
			if (vista.enlace && vista.enlace !== enlace) {
				form.elements.enlace.value = vista.enlace;
				ultimoAnalizado = vista.enlace;
			}
			vistaPrevia = vista.encontrado ? vista : null;
			usarImagen = Boolean(vista.imagen);
			if (!vista.encontrado) {
				avisoEnlace = vista.detail;
				return;
			}
			// Hay datos pero algo no cierra (por ejemplo, el precio está en dólares).
			avisoEnlace = vista.aviso ?? '';
			const actuales = {
				titulo: form.elements.titulo.value,
				descripcion: form.elements.descripcion.value
			};
			const ETIQUETAS = {
				nombre_producto: 'Producto',
				titulo: 'Título',
				precio_unitario: 'Precio',
				descripcion: 'Descripción'
			};
			const aplicados = [];
			for (const [campo, valor] of Object.entries(camposDesdeVistaPrevia(vista, actuales))) {
				if (conservarPrecio && campo === 'precio_unitario') continue;
				const input = form.elements[campo];
				if (!input) continue;
				const escrito = String(input.value ?? '').trim();
				// Lo que la persona escribió (o corrigió) manda: solo se completa
				// un campo vacío o uno que había puesto esta misma vista previa.
				if (escrito && escrito !== String(ultimoAutocompletado[campo] ?? '')) continue;
				input.value = valor;
				ultimoAutocompletado[campo] = valor;
				aplicados.push(ETIQUETAS[campo] ?? campo);
				// Resalta lo que completó la app, para que se note qué revisar.
				animarUnaVez(input, 'recien-completado');
			}
			if (vista.imagen && usarImagen) aplicados.push('Imagen');
			completados = aplicados;
			alInput();
		} catch (e) {
			if (actual !== pedidoEnlace) return;
			vistaPrevia = null;
			analisisEnlace = null;
			avisoEnlace =
				e?.status === 429
					? 'Demasiados intentos. Esperá un minuto y volvé a probar.'
					: (fieldErrors(e.data).enlace ?? 'No pudimos leer ese enlace. Completá los datos a mano.');
		} finally {
			if (actual === pedidoEnlace) analizando = false;
		}
	}

	// Al pegar, el valor llega recién después del evento: se espera un tick del navegador.
	function alPegarEnlace() {
		setTimeout(() => analizarEnlace(), 0);
	}

	// Los `value` por defecto del DOM (cantidad del creador, mínimo) entran a la
	// vista previa sin duplicarlos en el script.
	onMount(alInput);

	async function irAPaso(indice) {
		paso = Math.min(Math.max(indice, 0), PASOS.length - 1);
		await tick();
		const leyenda = document.getElementById(`paso-${PASOS[paso].id}`);
		leyenda?.focus({ preventScroll: true });
		leyenda?.scrollIntoView({
			block: 'start',
			behavior: prefiereMenosMovimiento() ? 'auto' : 'smooth'
		});
	}

	// Valida solo lo visible del paso actual. El formulario usa `novalidate` para
	// que los campos de pasos anteriores no bloqueen el envío desde el paso 3.
	async function validarPaso(indice) {
		if (!form) return true;
		// La categoría viaja en un input oculto: el select visible no la valida solo.
		if (indice === 0 && !categoriaId) {
			errors = { ...errors, categoria: 'Elegí una categoría.' };
			document.getElementById('categoria')?.focus({ preventScroll: true });
			return false;
		}
		for (const nombre of PASOS[indice].campos) {
			const control = form.elements[nombre];
			if (control && !control.checkValidity()) {
				paso = indice;
				await tick();
				control.reportValidity();
				control.focus({ preventScroll: true });
				return false;
			}
		}
		// Cobrar por transferencia sin datos deja a los participantes sin cómo pagar.
		if (indice === 2 && form.elements.tipo_pago?.value === 'transferencia') {
			const alias = form.elements.alias_cbu;
			const titular = form.elements.titular_cuenta;
			if (!alias?.value.trim() || !titular?.value.trim()) {
				errors = {
					...errors,
					alias_cbu: alias?.value.trim() ? undefined : 'Ingresá el alias o CBU para cobrar.',
					titular_cuenta: titular?.value.trim() ? undefined : 'Ingresá el titular de la cuenta.'
				};
				await tick();
				(alias?.value.trim() ? titular : alias)?.focus({ preventScroll: true });
				return false;
			}
		}
		return true;
	}

	async function siguiente() {
		if (await validarPaso(paso)) await irAPaso(paso + 1);
	}

	async function anterior() {
		await irAPaso(paso - 1);
	}

	// Enter avanza de paso, como en cualquier formulario corto. En el último
	// paso, Enter envía.
	function alTeclearForm(event) {
		if (event.key !== 'Enter' || paso >= PASOS.length - 1) return;
		const tag = event.target?.tagName;
		if (tag === 'TEXTAREA' || tag === 'BUTTON') return;
		event.preventDefault();
		siguiente();
	}

	function alElegirImagenes(event) {
		const elegidos = [...(event.target.files ?? [])];
		if (elegidos.length > MAX_IMAGENES) {
			notificar(`Podés subir hasta ${MAX_IMAGENES} imágenes.`, 'aviso');
		}
		archivos = elegidos.slice(0, MAX_IMAGENES);
		sincronizarInputImagenes(archivos);
	}

	// Mantiene el input en sincronía con la lista (al recortar o quitar fotos).
	function sincronizarInputImagenes(lista) {
		const input = form?.elements.imagenes;
		if (!input || typeof DataTransfer === 'undefined') return;
		const transferencia = new DataTransfer();
		for (const archivo of lista) transferencia.items.add(archivo);
		input.files = transferencia.files;
	}

	// Vista previa local de las fotos elegidas; se libera al cambiar o desmontar.
	$effect(() => {
		const items = archivos.map((archivo) => ({ archivo, url: URL.createObjectURL(archivo) }));
		previews = items;
		return () => items.forEach((item) => URL.revokeObjectURL(item.url));
	});

	function quitarArchivo(indice) {
		const restantes = archivos.filter((_, i) => i !== indice);
		archivos = restantes;
		sincronizarInputImagenes(restantes);
	}

	async function enviar(event) {
		event.preventDefault();
		errors = {};
		general = '';
		const totalPool = Number(datos.cantidad_total);
		const asignado = repartoDesdeMapa(reparto, variantesOfrecidas).reduce(
			(suma, fila) => suma + fila.cantidad,
			0
		);
		if (totalPool && asignado > totalPool) {
			errors = {
				...errors,
				reparto: `El reparto suma ${asignado} y la cantidad total es ${totalPool}.`
			};
			paso = 0;
			await tick();
			return;
		}
		// Recorre los tres pasos: si falta algo, vuelve al paso que lo contiene.
		for (let i = 0; i < PASOS.length; i += 1) {
			if (!(await validarPaso(i))) return;
		}
		if (archivos.length > 10) {
			general = 'Podés subir hasta 10 imágenes.';
			return;
		}
		enviando = true;
		try {
			const fd = new FormData(form);
			fd.delete('imagenes');
			if (usarImagen && vistaPrevia?.imagen) fd.append('imagen_url', vistaPrevia.imagen);
			const creado = await api('/pools/', { method: 'POST', body: fd, form: true });
			let fallidas = 0;
			for (const archivo of archivos) {
				const imgFd = new FormData();
				imgFd.append('imagen', archivo);
				try {
					await api(`/pools/${creado.id}/imagenes/`, { method: 'POST', body: imgFd, form: true });
				} catch (error) {
					fallidas += 1;
					notificar(`No se pudo subir ${archivo.name}: ${motivoImagen(error)}`, 'error');
				}
			}
			borrarBorrador(BORRADOR);
			goto(resolve(fallidas ? `/pools/${creado.id}?aviso=imagenes` : `/pools/${creado.id}`));
		} catch (e) {
			if (e?.status === 401) {
				// api.js ya avisó y el layout lleva al login; el borrador queda guardado.
				general = 'Tu sesión expiró. Iniciá sesión y vas a encontrar estos datos acá.';
				return;
			}
			const { detail, non_field_errors, reparto: errorReparto, ...porCampo } =
				fieldErrors(e.data);
			errors = errorReparto ? { ...porCampo, reparto: errorReparto } : porCampo;
			if (errorReparto) {
				paso = 0;
				await tick();
			}
			if (detail || non_field_errors) general = detail || non_field_errors;
			else if (!Object.keys(errors).length) general = 'No se pudo crear el pool.';
		} finally {
			enviando = false;
		}
	}

	const categoriaElegida = $derived(
		categorias.find((c) => String(c.id) === String(categoriaId)) ?? null
	);
	const variantesOfrecidas = $derived(
		Object.entries(atributos).map(([nombre, opciones]) => ({ nombre, opciones }))
	);

	// --- Vista previa "Así se verá tu pool" (mockup 06) ---
	const HOY = new Date().toISOString().slice(0, 10);
	const MAX_FECHA = new Date(Date.now() + 30 * 86_400_000).toISOString().slice(0, 10);
	const numero = (valor) => Math.max(Number(valor) || 0, 0);
	const cantidadTotal = $derived(numero(datos.cantidad_total));
	const cantidadCreador = $derived(numero(datos.cantidad_creador));
	const minPorIntegrante = $derived(numero(datos.min_por_integrante));
	// Precio total = unitario × cantidad (dato calculado, no editable: Iteración 3).
	const precioTotalTexto = $derived(precioTotal(datos.precio_unitario, datos.cantidad_total));
	const totalPool = $derived(precioTotalTexto ? Number(precioTotalTexto) : null);
	const participantes = $derived(
		cantidadTotal && minPorIntegrante
			? Math.ceil(Math.max(cantidadTotal - cantidadCreador, 0) / minPorIntegrante)
			: null
	);

	// Objeto con defaults seguros para reusar `PoolCard` sin tocar el form.
	const preview = $derived({
		id: 0,
		estado: 'abierto',
		imagenes: usarImagen && vistaPrevia?.imagen ? [{ imagen: vistaPrevia.imagen }] : [],
		titulo: datos.titulo?.trim() || 'Tu pool',
		nombre_producto: datos.nombre_producto?.trim() || '',
		categoria_nombre: categoriaElegida?.nombre ?? '',
		categoria_padre_nombre:
			categorias.find((c) => String(c.id) === String(categoriaElegida?.padre))?.nombre ?? null,
		precio_unitario: datos.precio_unitario,
		cantidad_total: cantidadTotal,
		cantidad_creador: cantidadCreador,
		disponible: Math.max(cantidadTotal - cantidadCreador, 0),
		// Sin fecha la fila se oculta (clase `preview--sin-fecha`), pero el fallback
		// evita que `diasHasta` deje un "Vence en NaN días" en el DOM.
		fecha_caducidad: datos.fecha_caducidad || HOY,
		creador: { username: session.user?.username ?? '' }
	});
</script>

<svelte:head>
	<title>Crear pool — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Crear pool</h1>
		<p>
			Cargá el producto, el precio al por mayor y hasta cuándo se puede sumar la gente. Después
			compartí el enlace.
		</p>
	</div>
</div>

<Pasos pasos={PASOS} {paso} onir={irAPaso} etiqueta="Pasos para crear el pool" />

<div class="crear">
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<form
		id="pool-form"
		class="crear__form"
		bind:this={form}
		novalidate
		onsubmit={enviar}
		oninput={alInput}
		onkeydown={alTeclearForm}
	>
		{#if general}
			<Aviso variante="error">{general}</Aviso>
		{/if}
		{#if borradorRestaurado}
			<Aviso variante="info" class="borrador">
				<span>Recuperamos los datos que estabas cargando.</span>
				<button type="button" class="borrador__descartar" onclick={descartarBorrador}>
					Empezar de cero
				</button>
			</Aviso>
		{/if}
		<fieldset class="seccion" id="paso-producto" tabindex="-1" hidden={paso !== 0}>
			<legend class="seccion__titulo" tabindex="-1">Producto</legend>
			<Campo
				id="enlace"
				etiqueta="Enlace del producto"
				ayuda="Opcional. Pegalo y completamos nombre, precio e imagen del producto."
				error={errors.enlace}
			>
				{#snippet children(props)}
					<div class="enlace">
						<input
							id="enlace"
							name="enlace"
							type="url"
							placeholder="https://…"
							onpaste={alPegarEnlace}
							onchange={() => analizarEnlace()}
							{...props}
						/>
						<Boton
							variante="secundario"
							disabled={analizando}
							onclick={() => analizarEnlace({ forzar: true })}
						>
							{#if analizando}<span class="spinner spinner--chico"></span> Leyendo…{:else}Autocompletar{/if}
						</Boton>
					</div>
				{/snippet}
			</Campo>
			<div class="enlace__estado" role="status">
				{#if completados.length && !analizando}
					<p class="enlace__completado">
						Completamos {completados.join(', ').toLowerCase()} desde el enlace. Revisá lo que quedó
						cargado antes de publicar.
					</p>
				{/if}
				{#if analizando}
					Buscando los datos del producto…
				{:else if avisoEnlace && !vistaPrevia}
					<Aviso variante="aviso">{avisoEnlace}</Aviso>
				{:else if vistaPrevia}
					{#if avisoEnlace}
						<Aviso variante="aviso">{avisoEnlace}</Aviso>
					{/if}
					<div class="producto animar">
						{#if vistaPrevia.imagen}
							<img class="producto__imagen" src={vistaPrevia.imagen} alt="" width="72" height="72" />
						{/if}
						<div class="producto__datos">
							<p class="producto__nombre">{vistaPrevia.nombre_producto ?? 'Producto encontrado'}</p>
							<p class="producto__precio">
								{vistaPrevia.precio_unitario
									? `${moneda(vistaPrevia.precio_unitario)} por unidad`
									: 'Sin precio publicado: completalo abajo.'}
							</p>
							{#if vistaPrevia.imagen}
								<label class="producto__usar">
									<input type="checkbox" bind:checked={usarImagen} />
									Usar esta imagen como portada
								</label>
							{/if}
						</div>
					</div>
				{/if}
			</div>
			{#if analisisEnlace && !analizando}
				<PanelEnlace analisis={analisisEnlace} />
			{/if}
			<div class="grilla-campos">
				<Campo
					id="titulo"
					etiqueta="Título"
					requerido
					ayuda="Un nombre corto que resuma la compra."
					error={errors.titulo}
				>
					{#snippet children(props)}
						<input id="titulo" name="titulo" type="text" required {...props} />
					{/snippet}
				</Campo>
				<Campo
					id="nombre_producto"
					etiqueta="Producto"
					requerido
					ayuda="Marca y modelo. El título es cómo querés mostrarlo en el listado."
					error={errors.nombre_producto}
				>
					{#snippet children(props)}
						<input id="nombre_producto" name="nombre_producto" type="text" required {...props} />
					{/snippet}
				</Campo>
				<Campo
					id="precio_unitario"
					etiqueta="Precio por unidad"
					requerido
					ayuda="Precio al por mayor por unidad."
					error={errors.precio_unitario}
				>
					{#snippet children(props)}
						<input
							id="precio_unitario"
							name="precio_unitario"
							type="number"
							min="0"
							step="0.01"
							required
							{...props}
						/>
					{/snippet}
				</Campo>
			</div>
			<div class="categoria-variantes">
				<SelectorCategoria {categorias} bind:categoriaId bind:atributos errores={errors} />
				<RepartoVariantes
					variantes={variantesOfrecidas}
					bind:reparto
					cantidadTotal={datos.cantidad_total ?? null}
					error={errors.reparto}
				/>
			</div>
			{#if errorCategorias}
				<div class="crear__aviso">
					<Aviso variante="aviso">
						No se pudieron cargar las categorías. Recargá la página para volver a intentar.
					</Aviso>
				</div>
			{/if}
		</fieldset>

		<fieldset class="seccion" id="paso-cantidades" tabindex="-1" hidden={paso !== 1}>
			<legend class="seccion__titulo" tabindex="-1">Cantidades y plazo</legend>
			<div class="grilla-campos">
				<Campo
					id="cantidad_total"
					etiqueta="Cantidad total"
					requerido
					ayuda="Unidades que hay que juntar para comprar."
					error={errors.cantidad_total}
				>
					{#snippet children(props)}
						<input id="cantidad_total" name="cantidad_total" type="number" min="1" required {...props} />
					{/snippet}
				</Campo>
				<Campo
					id="cantidad_creador"
					etiqueta="Tu reserva inicial"
					ayuda="Cuántas unidades reservás vos."
					error={errors.cantidad_creador}
				>
					{#snippet children(props)}
						<input
							id="cantidad_creador"
							name="cantidad_creador"
							type="number"
							min="1"
							value="1"
							required
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo
					id="min_por_integrante"
					etiqueta="Mínimo por integrante"
					ayuda="Mínimo que puede reservar cada persona."
					error={errors.min_por_integrante}
				>
					{#snippet children(props)}
						<input
							id="min_por_integrante"
							name="min_por_integrante"
							type="number"
							min="1"
							value="1"
							required
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo
					id="fecha_caducidad"
					etiqueta="Caducidad"
					requerido
					ayuda="Hasta 30 días desde hoy."
					error={errors.fecha_caducidad}
				>
					{#snippet children(props)}
						<input
							id="fecha_caducidad"
							name="fecha_caducidad"
							type="date"
							min={HOY}
							max={MAX_FECHA}
							required
							{...props}
						/>
					{/snippet}
				</Campo>
			</div>
			<!-- Al lado de la cantidad total, de la que depende. -->
			<Campo
				id="precio_total"
				etiqueta="Precio total"
				ayuda="Se calcula solo: precio por unidad × cantidad total."
			>
				{#snippet children(props)}
					<output id="precio_total" class="calculado" for="precio_unitario cantidad_total" {...props}>
						{#if precioTotalTexto}
							{moneda(precioTotalTexto)}
						{:else}
							<span class="calculado__vacio">Completá el precio y la cantidad total</span>
						{/if}
					</output>
				{/snippet}
			</Campo>
		</fieldset>

		<fieldset class="seccion" id="paso-entrega" tabindex="-1" hidden={paso !== 2}>
			<legend class="seccion__titulo" tabindex="-1">Entrega y pago</legend>
			<div class="grilla-campos">
				<Campo id="direccion" etiqueta="Dirección" requerido error={errors.direccion}>
					{#snippet children(props)}
						<input id="direccion" name="direccion" type="text" required {...props} />
					{/snippet}
				</Campo>
				<Campo id="ciudad" etiqueta="Ciudad" requerido error={errors.ciudad}>
					{#snippet children(props)}
						<input id="ciudad" name="ciudad" type="text" required {...props} />
					{/snippet}
				</Campo>
				<Campo
					id="tipo_pago"
					etiqueta="Tipo de pago"
					ayuda="Si elegís transferencia, cargá acá los datos para cobrar."
					error={errors.tipo_pago}
				>
					{#snippet children(props)}
						<select id="tipo_pago" name="tipo_pago" {...props}>
							{#each TIPOS_PAGO as [valor, texto] (valor)}
								<option value={valor}>{texto}</option>
							{/each}
						</select>
					{/snippet}
				</Campo>
				{#if pagoTransferencia}
					<Campo
						id="alias_cbu"
						etiqueta="Alias o CBU"
						requerido
						ayuda="Lo ven las personas que se suman al pool."
						error={errors.alias_cbu}
					>
						{#snippet children(props)}
							<input
								id="alias_cbu"
								name="alias_cbu"
								type="text"
								autocomplete="off"
								oninput={() => (errors = { ...errors, alias_cbu: undefined })}
								{...props}
							/>
						{/snippet}
					</Campo>
					<Campo
						id="titular_cuenta"
						etiqueta="Titular de la cuenta"
						requerido
						error={errors.titular_cuenta}
					>
						{#snippet children(props)}
							<input
								id="titular_cuenta"
								name="titular_cuenta"
								type="text"
								autocomplete="name"
								oninput={() => (errors = { ...errors, titular_cuenta: undefined })}
								{...props}
							/>
						{/snippet}
					</Campo>
				{/if}
			</div>
		</fieldset>

		<fieldset class="seccion" id="paso-fotos" tabindex="-1" hidden={paso !== 3}>
			<legend class="seccion__titulo">Fotos y descripción</legend>
			<Campo
				id="imagenes"
				etiqueta="Imágenes del pool"
				ayuda="Opcional, hasta 10 fotos (JPG, PNG, HEIC o WEBP)."
			>
				{#snippet children(props)}
					<div class="tiles">
						<input
							id="imagenes"
							class="archivo__input"
							name="imagenes"
							type="file"
							accept="image/*"
							multiple
							onchange={alElegirImagenes}
							{...props}
						/>
						<label class="tiles__agregar" for="imagenes">
							<svg
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2.4"
								stroke-linecap="round"
								aria-hidden="true"
							>
								<path d="M12 5v14M5 12h14" />
							</svg>
							Agregar imágenes
						</label>
						{#if previews.length}
							<ul class="tiles__lista">
								{#each previews as item, indice (item.url)}
									<li class="tiles__item">
										<img src={item.url} alt="" width="104" height="104" />
										{#if indice === 0}
											<span class="tiles__portada">Portada</span>
										{/if}
										<button
											type="button"
											class="tiles__quitar"
											onclick={() => quitarArchivo(indice)}
											aria-label={`Quitar ${item.archivo.name}`}
											title="Quitar imagen"
										>
											<svg
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2.4"
												stroke-linecap="round"
												aria-hidden="true"
											>
												<path d="M6 6l12 12M18 6 6 18" />
											</svg>
										</button>
									</li>
								{/each}
							</ul>
							<p class="tiles__contador">
								{archivos.length} de {MAX_IMAGENES} · La primera es la portada
							</p>
						{/if}
					</div>
				{/snippet}
			</Campo>
			<Campo
				id="descripcion"
				etiqueta="Descripción"
				ayuda="Contá detalles útiles: marca, medidas, punto de entrega."
				error={errors.descripcion}
			>
				{#snippet children(props)}
					<textarea id="descripcion" name="descripcion" rows="3" {...props}></textarea>
				{/snippet}
			</Campo>
		</fieldset>
	</form>

	<aside class="crear__lateral" aria-label="Vista previa del pool">
		<h2 class="crear__preview-titulo">Así se verá tu pool</h2>
		<!-- La card es una referencia visual del pool que todavía no existe: `inert`
		     la saca del foco y del árbol de accesibilidad (su enlace iría a /pools/0). -->
		<div class="preview" class:preview--sin-fecha={!datos.fecha_caducidad} class:preview--sin-cantidad={!cantidadTotal} inert aria-hidden="true">
			<PoolCard pool={preview} />
		</div>
		<div class="resumen">
			<p class="resumen__fila">
				<span>Participantes estimados</span>
				<b>{participantes ?? '—'}</b>
			</p>
			<p class="resumen__fila">
				<span>Total del pool</span>
				<b>{totalPool === null ? '—' : moneda(totalPool)}</b>
			</p>
		</div>
		<!-- Mismo orden que el resto de los formularios: cancelar a la izquierda, la acción a la derecha. -->
		{#if paso > 0}
			<Boton variante="ghost" bloque onclick={anterior}>
				← Volver a {PASOS[paso - 1].titulo.toLowerCase()}
			</Boton>
		{/if}
		<div class="crear__acciones">
			<Boton variante="secundario" bloque href={resolve('/pools')}>Cancelar</Boton>
			{#if paso < PASOS.length - 1}
				<Boton class="crear__enviar-escritorio" variante="primario" bloque onclick={siguiente}>
					Continuar
				</Boton>
			{:else}
				<Boton
					class="crear__enviar-escritorio"
					tipo="submit"
					form="pool-form"
					variante="primario"
					bloque
					disabled={enviando}
				>
					{#if enviando}<span class="spinner spinner--chico"></span> Creando…{:else}Crear pool{/if}
				</Boton>
			{/if}
		</div>
	</aside>

	<div class="crear__barra">
		<div class="crear__barra-resumen">
			<span class="crear__barra-etiqueta">Total del pool</span>
			<strong>{totalPool === null ? '—' : moneda(totalPool)}</strong>
		</div>
		{#if paso < PASOS.length - 1}
			<Boton variante="primario" onclick={siguiente}>Continuar</Boton>
		{:else}
			<Boton tipo="submit" form="pool-form" variante="primario" disabled={enviando}>
				{#if enviando}<span class="spinner spinner--chico"></span> Creando…{:else}Crear pool{/if}
			</Boton>
		{/if}
	</div>
</div>

<style>
	.crear__acciones {
		display: grid;
		grid-template-columns: 1fr 2fr;
		gap: var(--e-3);
	}

	.crear {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		gap: var(--e-6);
	}

	.enlace__completado {
		margin: 0 0 var(--e-2);
		color: var(--exito);
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.crear__barra {
		display: none;
	}

	.crear__form {
		flex: 999 1 560px;
		min-width: 0;
		display: flex;
		flex-direction: column;
	}

	.crear__lateral {
		flex: 1 1 340px;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
	}

	.crear__preview-titulo {
		margin: 0;
		font-size: var(--texto-md);
		font-weight: 700;
	}

	.enlace {
		display: flex;
		gap: var(--e-2);
	}

	.enlace input {
		flex: 1;
		min-width: 0;
	}

	.enlace__estado {
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.producto {
		display: flex;
		align-items: center;
		gap: var(--e-3);
		padding: var(--e-3);
		border: 1px solid var(--linea);
		border-radius: var(--radio);
		background: var(--crema);
	}

	.producto__imagen {
		flex: none;
		width: 72px;
		height: 72px;
		border-radius: var(--radio-sm);
		background: var(--superficie);
		object-fit: contain;
	}

	.producto__datos p {
		margin: 0;
	}

	.producto__nombre {
		font-weight: 700;
		color: var(--tinta);
	}

	.producto__usar {
		display: inline-flex;
		align-items: center;
		gap: var(--e-2);
		margin-top: var(--e-1);
		cursor: pointer;
	}

	.crear__aviso {
		margin-top: var(--e-3);
	}

	.seccion {
		margin: 0 0 var(--e-6);
		padding: 0;
		border: 0;
		scroll-margin-top: calc(var(--alto-cabecera) + var(--e-4));
	}

	.seccion:last-of-type {
		margin-bottom: 0;
	}

	.seccion__titulo {
		padding: 0 0 var(--e-3);
		font-family: var(--fuente-display);
		font-size: var(--texto-lg);
		font-weight: 800;
		letter-spacing: -0.01em;
		color: var(--tinta);
	}

	/* Vista previa: la card real del listado, sin su CTA (el pool no existe aún). */
	.preview :global(.pool__accion) {
		display: none;
	}

	/* Sin fecha no hay fila de vencimiento (evita el "Vence en NaN días" del vacío). */
	.preview--sin-fecha :global(.pool__pie) {
		display: none;
	}

	/* Sin cantidad total no hay barra ni "X / Y": "0 / 0 Completo" sería un estado
	   imposible (el form exige cantidad_total ≥ 1). */
	.preview--sin-cantidad :global(progress.pool__barra),
	.preview--sin-cantidad :global(.pool__meta) {
		display: none;
	}

	.resumen {
		display: flex;
		flex-direction: column;
		gap: var(--e-2);
		padding: var(--e-4);
		border-radius: var(--radio);
		background: var(--crema);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.resumen__fila {
		display: flex;
		justify-content: space-between;
		gap: var(--e-3);
		margin: 0;
	}

	.resumen__fila b {
		color: var(--tinta);
	}

	.tiles {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3);
	}

	.tiles__agregar {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--e-2);
		width: 104px;
		height: 104px;
		padding: var(--e-2);
		border: 2px dashed var(--linea-fuerte);
		border-radius: var(--radio);
		background: var(--crema);
		color: var(--tinta-suave);
		font-size: var(--texto-xs);
		font-weight: 600;
		text-align: center;
		cursor: pointer;
		transition: border-color var(--transicion), color var(--transicion);
	}

	.tiles__agregar:hover {
		border-color: var(--naranja-fuerte);
		color: var(--naranja-fuerte);
	}

	/* El input de archivo está clipeado: el foco visible va en el recuadro. */
	.tiles:focus-within .tiles__agregar {
		border-color: var(--acento);
		outline: 2px solid var(--acento);
		outline-offset: 2px;
	}

	.tiles__agregar svg {
		width: 22px;
		height: 22px;
	}

	.tiles__contador {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.tiles__lista {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-3);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.tiles__item {
		position: relative;
		width: 104px;
		height: 104px;
		border-radius: var(--radio);
		overflow: hidden;
		background: var(--melocoton-fuerte);
	}

	.tiles__item img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.tiles__portada {
		position: absolute;
		left: var(--e-1);
		bottom: var(--e-1);
		padding: 2px 8px;
		border-radius: var(--radio-full);
		background: rgba(31, 21, 18, 0.78);
		color: #fff;
		font-size: var(--texto-xs);
		font-weight: 700;
	}

	.tiles__quitar {
		position: absolute;
		top: 4px;
		right: 4px;
		display: grid;
		place-items: center;
		width: 32px;
		height: 32px;
		border: 0;
		border-radius: var(--radio-full);
		background: rgba(31, 21, 18, 0.78);
		color: #fff;
		cursor: pointer;
	}

	.tiles__quitar:hover {
		background: var(--marca-fuerte);
	}

	.tiles__quitar svg {
		width: 16px;
		height: 16px;
	}

	@media (max-width: 900px) {
		.crear {
			gap: var(--e-5);
			padding-bottom: 5.5rem;
		}

		:global(.crear__enviar-escritorio) {
			display: none;
		}

		.crear__acciones {
			grid-template-columns: 1fr;
		}

		.crear__barra {
			position: fixed;
			right: 0;
			bottom: 0;
			left: 0;
			z-index: 40;
			display: flex;
			align-items: center;
			justify-content: space-between;
			gap: var(--e-3);
			padding: 0.65rem var(--e-4) calc(0.65rem + env(safe-area-inset-bottom));
			border-top: 1px solid var(--linea);
			background: var(--superficie);
			box-shadow: 0 -6px 20px rgba(31, 21, 18, 0.08);
		}

		.crear__barra-resumen {
			display: flex;
			flex-direction: column;
			line-height: 1.2;
		}

		.crear__barra-etiqueta {
			font-size: var(--texto-xs);
			color: var(--tinta-tenue);
		}
	}

	:global(.borrador) {
		justify-content: space-between;
		align-items: center;
	}

	.borrador__descartar {
		border: 0;
		background: none;
		padding: 0;
		font: inherit;
		font-weight: 600;
		color: inherit;
		text-decoration: underline;
		cursor: pointer;
	}

	.calculado {
		display: flex;
		align-items: center;
		min-height: 2.75rem;
		padding: 0 0.9rem;
		border: 1px dashed var(--linea-control);
		border-radius: var(--radio-sm);
		background: var(--crema);
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}

	.calculado__vacio {
		font-weight: 400;
		color: var(--tinta-tenue);
	}

	.categoria-variantes {
		display: grid;
		gap: var(--e-4);
		margin-bottom: var(--e-4);
	}
</style>
