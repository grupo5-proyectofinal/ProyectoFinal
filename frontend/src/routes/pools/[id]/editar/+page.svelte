<script>
	import { tick } from 'svelte';
	import { beforeNavigate, goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api, fieldErrors } from '$lib/api.js';
	import { armarCuerpoEdicion, pasoConError } from '$lib/borradorPool.js';
	import { confirmar } from '$lib/confirmacion.svelte.js';
	import { etiquetaEstado, puedeEditar } from '$lib/estados.js';
	import { moneda } from '$lib/formato.js';
	import { motivoImagen } from '$lib/imagenes.js';
	import { prefiereMenosMovimiento } from '$lib/movimiento.js';
	import { notificar } from '$lib/toast.svelte.js';
	import AutocompletarDireccion from '$lib/AutocompletarDireccion.svelte';
	import { AYUDAS } from '$lib/ayudasPool.js';
	import InfoCaducidad from '$lib/InfoCaducidad.svelte';
	import SelectorCategoria from '$lib/SelectorCategoria.svelte';
	import { precioTotal } from '$lib/producto.js';
	import { session } from '$lib/session.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Pasos from '$lib/ui/Pasos.svelte';
	import Dialogo from '$lib/ui/Dialogo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let pool = $state(null);
	let categorias = $state([]);
	let cargando = $state(true);
	let error = $state('');
	let errors = $state({});
	let general = $state('');
	let exito = $state('');
	let form = $state();
	// Borrado de imágenes con confirmación del sistema, no con `confirm()` nativo.
	let imagenAEliminar = $state(null);
	let borrando = $state(false);
	let guardando = $state(false);
	let publicando = $state(false);
	const ocupando = $derived(guardando || publicando);
	let categoriaId = $state('');
	let atributos = $state({});
	// Precio total calculado en vivo (unitario × cantidad); null = usar los del pool.
	let precioEditado = $state(null);
	let cantidadEditada = $state(null);
	let sucio = $state(false);
	// Mismo esquema de pasos que "Crear pool": una sección visible por vez.
	const PASOS = [
		{
			id: 'producto',
			titulo: 'Producto',
			campos: ['titulo', 'enlace', 'nombre_producto', 'categoria', 'atributos', 'descripcion']
		},
		{
			id: 'precio',
			titulo: 'Precio y cantidades',
			campos: [
				'precio_unitario',
				'cantidad_total',
				'cantidad_creador',
				'min_por_integrante'
			]
		},
		{
			id: 'entrega',
			titulo: 'Entrega y pago',
			campos: ['fecha_caducidad', 'tipo_pago', 'alias_cbu', 'titular_cuenta', 'direccion', 'ciudad']
		}
	];
	let paso = $state(0);

	async function irAPaso(indice) {
		paso = Math.min(Math.max(indice, 0), PASOS.length - 1);
		await tick();
		const fieldset = document.getElementById(`paso-${PASOS[paso].id}`);
		fieldset?.focus({ preventScroll: true });
		fieldset?.scrollIntoView({
			block: 'start',
			behavior: prefiereMenosMovimiento() ? 'auto' : 'smooth'
		});
	}

	function anterior() {
		irAPaso(paso - 1);
	}

	function siguiente() {
		irAPaso(paso + 1);
	}

	beforeNavigate(async ({ cancel }) => {
		if (!sucio) return;
		const salir = await confirmar({
			titulo: '¿Salir sin guardar?',
			descripcion: 'Tenés cambios en el pool que todavía no guardaste.',
			confirmar: 'Salir sin guardar'
		});
		if (!salir) cancel();
	});

	function alSalir(evento) {
		if (!sucio) return;
		evento.preventDefault();
		evento.returnValue = '';
	}

	const TIPOS_PAGO = [
		['transferencia', 'Transferencia'],
		['sin_especificar', 'Sin especificar']
	];
	const HOY = new Date().toISOString().slice(0, 10);
	const MAX_FECHA = new Date(Date.now() + 30 * 86_400_000).toISOString().slice(0, 10);

	$effect(() => {
		cargar(page.params.id);
	});

	async function cargar(id) {
		cargando = true;
		try {
			pool = await api(`/pools/${id}/`);
			categoriaId = String(pool.categoria);
			atributos = pool.atributos ?? {};
			categorias = await api('/categories/').then((r) => r.results ?? r);
		} catch (e) {
			error = e.status === 404 ? 'El pool no existe.' : 'No se pudo cargar el pool.';
		} finally {
			cargando = false;
		}
	}

	const esCreador = $derived(session.user?.id === pool?.creador?.id);
	const esEditable = $derived(puedeEditar(pool, session.user?.id));
	// Un borrador se guarda a medias: ningún dato es obligatorio hasta publicarlo.
	const esBorrador = $derived(pool?.estado === 'borrador');
	let tipoPagoElegido = $state(null);
	const cobraPorTransferencia = $derived((tipoPagoElegido ?? pool?.tipo_pago) === 'transferencia');
	const hayOtrosIntegrantes = $derived(
		pool?.miembros?.some((m) => m.usuario.id !== pool.creador.id) ?? false
	);
	const portada = $derived(pool?.imagenes?.[0]?.imagen ?? null);
	const comprometido = $derived(pool ? pool.cantidad_total - pool.disponible : 0);
	const totalEditado = $derived(
		precioTotal(precioEditado ?? pool?.precio_unitario, cantidadEditada ?? pool?.cantidad_total)
	);

	// Elegir una sugerencia de dirección completa también la ciudad.
	function alElegirDireccion(sugerencia) {
		if (sugerencia.ciudad) form.ciudad.value = sugerencia.ciudad;
		sucio = true;
	}

	function leerValoresFormulario() {
		const valores = {
			descripcion: form.descripcion.value,
			fecha_caducidad: form.fecha_caducidad.value,
			cantidad_creador: form.cantidad_creador.value,
			min_por_integrante: form.min_por_integrante.value,
			tipo_pago: form.tipo_pago.value
		};
		if (form.tipo_pago.value === 'transferencia') {
			valores.alias_cbu = form.alias_cbu?.value ?? '';
			valores.titular_cuenta = form.titular_cuenta?.value ?? '';
		}
		if (!hayOtrosIntegrantes) {
			Object.assign(valores, {
				titulo: form.titulo.value,
				nombre_producto: form.nombre_producto.value,
				precio_unitario: form.precio_unitario.value,
				cantidad_total: form.cantidad_total.value,
				direccion: form.direccion.value,
				ciudad: form.ciudad.value,
				categoria: categoriaId,
				atributos: form.atributos.value
			});
		}
		if (esBorrador) {
			valores.enlace = form.enlace.value;
		}
		return valores;
	}

	async function aplicarErrorApi(e, mensajePorDefecto, { mensajeConCampos = '' } = {}) {
		if (e.status === 401) {
			// api.js ya avisó "Tu sesión expiró" y el layout lleva al login.
			general = 'Tu sesión expiró. Iniciá sesión de nuevo para guardar los cambios.';
			return;
		}
		if (e.status === 403) {
			general = 'Solo el creador puede editar este pool.';
			return;
		}
		const { detail, non_field_errors, ...porCampo } = fieldErrors(e.data);
		errors = porCampo;
		const tieneCampos = Object.keys(errors).length > 0;
		general =
			detail ||
			non_field_errors ||
			(tieneCampos ? mensajeConCampos : mensajePorDefecto);
		const indice = pasoConError(porCampo, PASOS);
		if (indice >= 0) await irAPaso(indice);
	}

	async function guardarPool() {
		const cuerpo = armarCuerpoEdicion(leerValoresFormulario(), {
			esBorrador,
			hayOtrosIntegrantes
		});
		try {
			pool = await api(`/pools/${pool.id}/`, { method: 'PATCH', body: cuerpo });
			sucio = false;
			return true;
		} catch (e) {
			await aplicarErrorApi(e, 'No se pudo guardar.');
			return false;
		}
	}

	async function enviar(event) {
		event.preventDefault();
		if (ocupando) return;
		errors = {};
		general = '';
		exito = '';
		guardando = true;
		try {
			if (await guardarPool()) {
				exito = esBorrador ? 'Borrador guardado.' : 'Cambios guardados.';
			}
		} finally {
			guardando = false;
		}
	}

	async function publicar() {
		if (ocupando || !esBorrador) return;
		errors = {};
		general = '';
		exito = '';
		publicando = true;
		try {
			if (!(await guardarPool())) return;
			await api(`/pools/${pool.id}/publicar/`, { method: 'POST' });
			sucio = false;
			notificar('Pool publicado: ya aparece en Explorar.');
			goto(resolve(`/pools/${pool.id}`));
		} catch (e) {
			await aplicarErrorApi(e, 'No se pudo publicar el pool.', {
				mensajeConCampos: 'Faltan datos para publicar el pool. Revisá los campos marcados.'
			});
		} finally {
			publicando = false;
		}
	}

	async function subirImagenes(event) {
		const lista = event.target.files;
		if (!lista?.length) return;
		general = '';
		const fallidas = [];
		for (const archivo of lista) {
			const fd = new FormData();
			fd.append('imagen', archivo);
			try {
				await api(`/pools/${pool.id}/imagenes/`, { method: 'POST', body: fd, form: true });
			} catch (error) {
				fallidas.push(`${archivo.name}: ${motivoImagen(error)}`);
			}
		}
		event.target.value = '';
		await cargar(pool.id);
		if (fallidas.length) general = `No se pudieron subir: ${fallidas.join(' · ')}`;
	}

	async function borrarImagen() {
		if (imagenAEliminar === null || borrando) return;
		borrando = true;
		general = '';
		try {
			await api(`/pools/${pool.id}/imagenes/${imagenAEliminar}/`, { method: 'DELETE' });
			imagenAEliminar = null;
			await cargar(pool.id);
		} catch (e) {
			general = fieldErrors(e.data).detail ?? 'No se pudo borrar la imagen.';
			imagenAEliminar = null;
		} finally {
			borrando = false;
		}
	}
</script>

<svelte:window onbeforeunload={alSalir} />

<svelte:head>
	<title>Editar pool — PoolShop</title>
</svelte:head>

{#if cargando}
	<div class="cargando" role="status"><span class="spinner spinner--grande"></span> Cargando el pool…</div>
{:else if error}
	<div class="vacio">
		<h3>{error}</h3>
		<Boton variante="secundario" href={resolve('/pools')}>Volver a pools</Boton>
	</div>
{:else if !esCreador}
	<div class="vacio">
		<h3>Solo el creador puede editar este pool</h3>
		<p>Si necesitás cambios, pedile al creador que los haga.</p>
		<Boton variante="secundario" href={resolve(`/pools/${pool.id}`)}>Volver al detalle</Boton>
	</div>
{:else if !esEditable}
	<div class="vacio">
		<h3>Este pool ya no se puede editar</h3>
		<p>Solo se puede editar mientras el pool esté en borrador o abierto.</p>
		<Boton variante="secundario" href={resolve(`/pools/${pool.id}`)}>Volver al detalle</Boton>
	</div>
{:else}
	<a class="volver" href={resolve(`/pools/${pool.id}`)}>← Volver al pool</a>

	<header class="cabecera-pool">
		<div class="cabecera-pool__media">
			{#if portada}
				<img src={portada} alt={pool.titulo} width="84" height="84" />
			{:else}
				<svg
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.4"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<path d="M3 8l9-5 9 5v8l-9 5-9-5z" />
					<path d="M3 8l9 5 9-5M12 13v8" />
				</svg>
			{/if}
		</div>
		<div class="cabecera-pool__datos">
			<div class="cabecera-pool__rol">
				<span>Sos el organizador</span>
				<Badge variante={pool.estado}>{etiquetaEstado(pool.estado)}</Badge>
			</div>
			<h1>{pool.titulo}</h1>
			<p class="cabecera-pool__meta">
				{comprometido} / {pool.cantidad_total} unidades ·
				{moneda(pool.precio_unitario)} c/u ·
				{pool.integrantes}
				{pool.integrantes === 1 ? 'participante' : 'participantes'} · {pool.ciudad}
			</p>
		</div>
	</header>

	{#if hayOtrosIntegrantes}
		<div class="editar__aviso">
			<Aviso variante="info">
				Ya hay integrantes en el pool: el título, el producto, el precio, la cantidad total y el
				domicilio no se pueden cambiar.
			</Aviso>
		</div>
	{/if}

	<Pasos pasos={PASOS} {paso} onir={irAPaso} etiqueta="Pasos para editar el pool" />

	<form bind:this={form} onsubmit={enviar} oninput={() => (sucio = true)} novalidate>
		<fieldset class="seccion" id="paso-producto" tabindex="-1" hidden={paso !== 0}>
			<legend class="seccion__titulo">Producto</legend>
			<div class="grilla-campos">
				<Campo id="titulo" info={AYUDAS.titulo} etiqueta="Título" error={errors.titulo}>
					{#snippet children(props)}
						<input
							id="titulo"
							name="titulo"
							type="text"
							value={pool.titulo}
							disabled={hayOtrosIntegrantes}
							{...props}
						/>
					{/snippet}
				</Campo>
				{#if esBorrador}
					<Campo
						id="enlace"
						info={AYUDAS.enlace}
						etiqueta="Enlace de la tienda"
						ayuda="Obligatorio para publicar."
						error={errors.enlace}
					>
						{#snippet children(props)}
							<input id="enlace" name="enlace" type="url" value={pool.enlace} {...props} />
						{/snippet}
					</Campo>
				{/if}
				<Campo id="nombre_producto" info={AYUDAS.nombre_producto} etiqueta="Producto" error={errors.nombre_producto}>
					{#snippet children(props)}
						<input
							id="nombre_producto"
							name="nombre_producto"
							type="text"
							value={pool.nombre_producto}
							disabled={hayOtrosIntegrantes}
							{...props}
						/>
					{/snippet}
				</Campo>
			</div>
			<div class="categoria-variantes">
				<SelectorCategoria
					{categorias}
					bind:categoriaId
					bind:atributos
					errores={errors}
					bloqueado={hayOtrosIntegrantes}
				/>
			</div>
			<Campo id="descripcion" info={AYUDAS.descripcion} etiqueta="Descripción" error={errors.descripcion}>
				{#snippet children(props)}
					<textarea id="descripcion" name="descripcion" rows="3" {...props}>{pool.descripcion}</textarea>
				{/snippet}
			</Campo>
		</fieldset>

		<fieldset class="seccion" id="paso-precio" tabindex="-1" hidden={paso !== 1}>
			<legend class="seccion__titulo">Precio y cantidades</legend>
			<div class="grilla-campos">
				<Campo id="precio_unitario" info={AYUDAS.precio_unitario} etiqueta="Precio unitario" error={errors.precio_unitario}>
					{#snippet children(props)}
						<input
							id="precio_unitario"
							name="precio_unitario"
							type="number"
							min="0"
							step="0.01"
							value={pool.precio_unitario}
							disabled={hayOtrosIntegrantes}
							oninput={(e) => (precioEditado = e.currentTarget.value)}
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo id="cantidad_total" info={AYUDAS.cantidad_total} etiqueta="Cantidad total" error={errors.cantidad_total}>
					{#snippet children(props)}
						<input
							id="cantidad_total"
							name="cantidad_total"
							type="number"
							min="1"
							value={pool.cantidad_total}
							disabled={hayOtrosIntegrantes}
							oninput={(e) => (cantidadEditada = e.currentTarget.value)}
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo id="precio_total" info={AYUDAS.precio_total} etiqueta="Precio total" ayuda="Se calcula solo: unitario × cantidad, sin el envío.">
					{#snippet children(props)}
						<output id="precio_total" class="calculado" for="precio_unitario cantidad_total" {...props}>
							{totalEditado ? moneda(totalEditado) : '—'}
						</output>
					{/snippet}
				</Campo>
				<Campo
					id="cantidad_creador"
					info={AYUDAS.cantidad_creador}
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
							value={pool.cantidad_creador}
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo
					id="min_por_integrante"
					info={AYUDAS.min_por_integrante}
					etiqueta="Mínimo por integrante"
					error={errors.min_por_integrante}
				>
					{#snippet children(props)}
						<input
							id="min_por_integrante"
							name="min_por_integrante"
							type="number"
							min="1"
							value={pool.min_por_integrante}
							{...props}
						/>
					{/snippet}
				</Campo>
			</div>
		</fieldset>

		<fieldset class="seccion" id="paso-entrega" tabindex="-1" hidden={paso !== 2}>
			<legend class="seccion__titulo">Entrega y pago</legend>
			<div class="grilla-campos">
				<Campo
					id="fecha_caducidad"
					etiqueta="Caducidad"
					ayuda="Último día para completar el cupo. Si la adelantás, el pool puede cancelarse."
					error={errors.fecha_caducidad}
				>
					{#snippet info()}<InfoCaducidad />{/snippet}
					{#snippet children(props)}
						<input
							id="fecha_caducidad"
							name="fecha_caducidad"
							type="date"
							min={HOY}
							max={MAX_FECHA}
							value={pool.fecha_caducidad}
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo id="tipo_pago" info={AYUDAS.tipo_pago} etiqueta="Tipo de pago" error={errors.tipo_pago}>
					{#snippet children(props)}
						<select
							id="tipo_pago"
							name="tipo_pago"
							value={pool.tipo_pago}
							onchange={(e) => (tipoPagoElegido = e.currentTarget.value)}
							{...props}
						>
							{#each TIPOS_PAGO as [valor, texto] (valor)}
								<option value={valor}>{texto}</option>
							{/each}
						</select>
					{/snippet}
				</Campo>
				{#if cobraPorTransferencia}
					<Campo
						id="alias_cbu"
						info={AYUDAS.alias_cbu}
						etiqueta="Alias o CBU"
						ayuda="Lo ven las personas que se suman al pool."
						error={errors.alias_cbu}
					>
						{#snippet children(props)}
							<input
								id="alias_cbu"
								name="alias_cbu"
								type="text"
								autocomplete="off"
								value={pool.alias_cbu ?? ''}
								{...props}
							/>
						{/snippet}
					</Campo>
					<Campo id="titular_cuenta" info={AYUDAS.titular_cuenta} etiqueta="Titular de la cuenta" error={errors.titular_cuenta}>
						{#snippet children(props)}
							<input
								id="titular_cuenta"
								name="titular_cuenta"
								type="text"
								autocomplete="name"
								value={pool.titular_cuenta ?? ''}
								{...props}
							/>
						{/snippet}
					</Campo>
				{/if}
				<Campo id="direccion" info={AYUDAS.direccion} etiqueta="Dirección" error={errors.direccion}>
					{#snippet children(props)}
						<AutocompletarDireccion
							id="direccion"
							name="direccion"
							value={pool.direccion}
							ciudad={pool.ciudad}
							disabled={hayOtrosIntegrantes}
							onelegir={alElegirDireccion}
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo id="ciudad" info={AYUDAS.ciudad} etiqueta="Ciudad" error={errors.ciudad}>
					{#snippet children(props)}
						<input
							id="ciudad"
							name="ciudad"
							type="text"
							value={pool.ciudad}
							disabled={hayOtrosIntegrantes}
							{...props}
						/>
					{/snippet}
				</Campo>
			</div>
		</fieldset>

		{#if exito}
			<div class="editar__aviso">
				<Aviso variante="exito">{exito}</Aviso>
			</div>
		{/if}
		{#if general}
			<div class="editar__aviso">
				<Aviso variante="error">{general}</Aviso>
			</div>
		{/if}

		<div class="acciones">
			{#if paso > 0}
				<Boton variante="ghost" onclick={anterior} disabled={ocupando}>← Volver</Boton>
			{/if}
			<Boton
				variante="secundario"
				href={resolve(`/pools/${pool.id}`)}
				onclick={() => (sucio = false)}>Descartar</Boton
			>
			{#if esBorrador && paso < PASOS.length - 1}
				<Boton tipo="submit" variante="secundario" disabled={ocupando}>
					{guardando ? 'Guardando…' : 'Guardar borrador'}
				</Boton>
			{/if}
			{#if paso < PASOS.length - 1}
				<Boton variante="primario" onclick={siguiente} disabled={ocupando}>Continuar</Boton>
			{:else if esBorrador}
				<Boton tipo="submit" variante="secundario" disabled={ocupando}>
					{guardando ? 'Guardando…' : 'Guardar borrador'}
				</Boton>
				<Boton variante="primario" onclick={publicar} disabled={ocupando}>
					{publicando ? 'Publicando…' : 'Publicar pool'}
				</Boton>
			{:else}
				<Boton tipo="submit" variante="primario" disabled={ocupando}>
					{guardando ? 'Guardando…' : 'Guardar cambios'}
				</Boton>
			{/if}
		</div>
	</form>

	<div class="imagenes-panel">
		<Tarjeta>
			<div class="imagenes">
				<h2 class="imagenes__titulo">Imágenes</h2>
				{#if pool.imagenes.length}
					<ul class="imagenes__lista">
						{#each pool.imagenes as imagen (imagen.id)}
							<li class="imagen">
								<img
									class="imagen__img"
									src={imagen.imagen}
									alt={pool.titulo}
									width="160"
									height="120"
									loading="lazy"
								/>
								<Boton
									variante="peligro-suave"
									tamano="sm"
									onclick={() => (imagenAEliminar = imagen.id)}
								>
									Borrar
								</Boton>
							</li>
						{/each}
					</ul>
				{:else}
					<p class="imagenes__vacio">Sin imágenes todavía.</p>
				{/if}
				<div class="imagenes__agregar">
					<input
						id="nuevas"
						class="archivo__input"
						type="file"
						accept="image/*"
						multiple
						onchange={subirImagenes}
						aria-describedby="nuevas-ayuda"
					/>
					<label class="imagenes__tile" for="nuevas">
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
					<span class="imagenes__ayuda" id="nuevas-ayuda">Hasta 10 · JPG, PNG, HEIC o WEBP</span>
				</div>
			</div>
		</Tarjeta>
	</div>

	<Dialogo
		abierto={imagenAEliminar !== null}
		titulo="¿Borrar esta imagen?"
		descripcion="Se quita del pool y no se puede deshacer. Si era la portada, se usa la siguiente."
		confirmar={borrando ? 'Borrando…' : 'Borrar imagen'}
		variante="peligro-suave"
		oncancelar={() => (imagenAEliminar = null)}
		onconfirmar={borrarImagen}
	/>
{/if}

<style>

	.cabecera-pool {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-4);
		margin-bottom: var(--e-6);
	}

	.cabecera-pool__media {
		display: grid;
		place-items: center;
		flex: none;
		width: 84px;
		height: 84px;
		border-radius: var(--radio);
		background: var(--melocoton-fuerte);
		overflow: hidden;
	}

	/* Completa, sin recortar: las fotos de tienda suelen tener el producto al borde. */
	.cabecera-pool__media img {
		width: 100%;
		height: 100%;
		object-fit: contain;
		background: var(--superficie);
	}

	.cabecera-pool__media svg {
		width: 40px;
		height: 40px;
		color: var(--naranja-fuerte);
	}

	.cabecera-pool__datos {
		flex: 1 1 20rem;
		min-width: 0;
	}

	.cabecera-pool__rol {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-2);
		font-size: var(--texto-xs);
		font-weight: 700;
		color: var(--naranja-fuerte);
	}

	.cabecera-pool__datos h1 {
		margin: var(--e-1) 0;
		font-size: var(--texto-xl);
		letter-spacing: -0.02em;
		overflow-wrap: anywhere;
	}

	.cabecera-pool__meta {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.editar__aviso {
		margin-bottom: var(--e-4);
	}

	.imagenes-panel {
		margin-top: var(--e-6);
	}

	.seccion {
		margin: 0 0 var(--e-6);
		padding: 0;
		border: 0;
	}

	.seccion__titulo {
		padding: 0 0 var(--e-3);
		font-family: var(--fuente-display);
		font-size: var(--texto-lg);
		font-weight: 800;
		letter-spacing: -0.01em;
		color: var(--tinta);
	}

	.imagenes {
		display: flex;
		flex-direction: column;
		gap: var(--e-4);
		padding: clamp(1.25rem, 2.5vw, 2rem);
	}

	.imagenes__titulo {
		margin: 0;
		font-family: var(--fuente-display);
		font-size: var(--texto-lg);
		font-weight: 800;
		letter-spacing: -0.01em;
	}

	.imagenes__lista {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
		gap: var(--e-3);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.imagen {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--e-2);
	}

	.imagen__img {
		width: 100%;
		aspect-ratio: 4 / 3;
		object-fit: contain;
		background: var(--superficie);
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
	}

	.imagenes__vacio {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	.imagenes__agregar {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3);
	}

	.imagenes__tile {
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

	.imagenes__tile:hover {
		border-color: var(--naranja-fuerte);
		color: var(--naranja-fuerte);
	}

	.imagenes__tile svg {
		width: 22px;
		height: 22px;
	}

	.imagenes__ayuda {
		font-size: var(--texto-xs);
		color: var(--tinta-suave);
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

	.categoria-variantes {
		display: grid;
		gap: var(--e-4);
		margin: var(--e-4) 0;
	}
</style>
