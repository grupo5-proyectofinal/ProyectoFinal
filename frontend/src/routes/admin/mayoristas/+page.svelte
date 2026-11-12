<script>
	// Backoffice del directorio: aprobar sugerencias, verificar, editar y los
	// parámetros (tipo de cambio y alícuotas) que usa el comparador.
	import { resolve } from '$app/paths';
	import { api, fieldErrors } from '$lib/api.js';
	import { ESTADOS_PROVEEDOR } from '$lib/comparador.js';
	import { esStaff } from '$lib/admin.js';
	import { confirmar } from '$lib/confirmacion.svelte.js';
	import { session } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let estado = $state('pendiente');
	let proveedores = $state([]);
	let parametros = $state([]);
	let nuevo = $state({ nombre: '', sitio_url: '', provincia: '', compra_minima: '' });
	let erroresNuevo = $state({});
	let pedido = 0;
	let cargando = $state(true);
	let errorCarga = $state('');
	let errorAccion = $state('');
	let accionEnCurso = $state('');
	let errorParametros = $state('');
	let cargandoParametros = $state(true);
	let guardandoParametro = $state('');
	let creando = $state(false);

	$effect(() => {
		if (esStaff(session.user)) cargar(estado);
	});

	$effect(() => {
		if (esStaff(session.user)) {
			api('/parametros-costo/')
				.then((r) => {
					parametros = r;
					errorParametros = '';
				})
				.catch(() => {
					errorParametros = 'No se pudieron cargar los parámetros.';
				})
				.finally(() => {
					cargandoParametros = false;
				});
		}
	});

	async function cargar(filtro) {
		const actual = ++pedido;
		cargando = true;
		errorCarga = '';
		try {
			const r = await api('/proveedores/', { query: { estado: filtro } });
			if (actual === pedido) proveedores = r.results ?? r;
		} catch {
			if (actual === pedido) {
				proveedores = [];
				errorCarga = 'No se pudieron cargar los mayoristas.';
			}
		} finally {
			if (actual === pedido) cargando = false;
		}
	}

	async function accion(proveedor, nombre) {
		if (accionEnCurso) return;
		if (nombre === 'rechazar') {
			const aceptada = await confirmar({
				titulo: `¿Rechazar ${proveedor.nombre}?`,
				descripcion: 'Deja de aparecer en el directorio aprobado. Podés volver a aprobarlo después.',
				confirmar: 'Rechazar'
			});
			if (!aceptada) return;
		}
		errorAccion = '';
		accionEnCurso = `${proveedor.id}-${nombre}`;
		try {
			await api(`/proveedores/${proveedor.id}/${nombre}/`, { method: 'POST' });
			notificar(
				nombre === 'aprobar' ? `${proveedor.nombre} publicado.` : `${proveedor.nombre} rechazado.`
			);
			await cargar(estado);
		} catch (e) {
			errorAccion = fieldErrors(e.data).detail ?? 'No se pudo completar la acción.';
		} finally {
			accionEnCurso = '';
		}
	}

	async function alternarVerificado(proveedor) {
		if (accionEnCurso) return;
		if (proveedor.verificado) {
			const aceptada = await confirmar({
				titulo: `¿Quitar el verificado a ${proveedor.nombre}?`,
				descripcion: 'La ficha deja de mostrar la insignia de confianza.',
				confirmar: 'Quitar verificado'
			});
			if (!aceptada) return;
		}
		errorAccion = '';
		accionEnCurso = `${proveedor.id}-verificado`;
		try {
			await api(`/proveedores/${proveedor.id}/`, {
				method: 'PATCH',
				body: { verificado: !proveedor.verificado }
			});
			await cargar(estado);
		} catch (e) {
			errorAccion = fieldErrors(e.data).detail ?? 'No se pudo cambiar el verificado.';
		} finally {
			accionEnCurso = '';
		}
	}

	async function borrar(proveedor) {
		const aceptada = await confirmar({
			titulo: `¿Borrar ${proveedor.nombre}?`,
			descripcion: 'Se quita del directorio y no se puede deshacer.',
			confirmar: 'Borrar'
		});
		if (!aceptada) return;
		try {
			await api(`/proveedores/${proveedor.id}/`, { method: 'DELETE' });
			cargar(estado);
		} catch (e) {
			notificar(fieldErrors(e.data).detail ?? 'No se pudo borrar el mayorista.', 'error');
		}
	}

	async function crear(evento) {
		evento.preventDefault();
		if (creando) return;
		erroresNuevo = {};
		creando = true;
		try {
			await api('/proveedores/', { method: 'POST', body: nuevo });
			nuevo = { nombre: '', sitio_url: '', provincia: '', compra_minima: '' };
			notificar('Mayorista agregado y publicado.');
			estado = 'aprobado';
			cargar(estado);
		} catch (e) {
			erroresNuevo = fieldErrors(e.data);
			if (!Object.keys(erroresNuevo).length) erroresNuevo = { detail: 'No se pudo agregar.' };
		} finally {
			creando = false;
		}
	}

	async function guardarParametro(parametro, valor) {
		guardandoParametro = parametro.clave;
		try {
			const actualizado = await api(`/parametros-costo/${parametro.clave}/`, {
				method: 'PATCH',
				body: { valor }
			});
			parametros = parametros.map((p) => (p.clave === parametro.clave ? actualizado : p));
			if (Number(valor) === 0 && parametro.clave.startsWith('tipo_cambio_')) {
				notificar(
					`${parametro.nombre} quedó en 0: las ofertas de esa moneda se muestran como "falta tipo de cambio".`,
					'aviso'
				);
			} else {
				notificar(`${parametro.nombre} actualizado.`);
			}
		} catch (e) {
			notificar(fieldErrors(e.data).valor ?? 'No se pudo guardar.', 'error');
		} finally {
			guardandoParametro = '';
		}
	}
</script>

<svelte:head>
	<title>Mayoristas (admin) — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Mayoristas</h1>
		<p>Revisá las sugerencias, marcá los verificados y cargá los valores que usa el comparador.</p>
	</div>
</div>

{#if errorAccion}
	<Aviso variante="error">{errorAccion}</Aviso>
{/if}

<div class="columnas">
	<section>
		<div class="filtro" role="group" aria-label="Estado">
			{#each Object.entries(ESTADOS_PROVEEDOR) as [clave, datos] (clave)}
				<button
					type="button"
					class="filtro__boton"
					class:activo={estado === clave}
					aria-pressed={estado === clave}
					disabled={cargando}
					onclick={() => (estado = clave)}
				>
					{datos.texto}
				</button>
			{/each}
		</div>
		{#if cargando}
			<p class="muted" role="status">Cargando mayoristas…</p>
		{:else if errorCarga}
			<Aviso variante="error">
				{errorCarga}
				<Boton variante="ghost" tamano="sm" onclick={() => cargar(estado)}>Reintentar</Boton>
			</Aviso>
		{:else if !proveedores.length}
			<div class="vacio vacio--compacto">
				<p>No hay mayoristas en este estado.</p>
				<Boton variante="secundario" href="#nuevo-mayorista">Agregar mayorista</Boton>
			</div>
		{:else}
			<ul class="lista">
				{#each proveedores as proveedor (proveedor.id)}
					<li class="item">
						<div>
							<a href={resolve(`/mayoristas/${proveedor.id}`)}><strong>{proveedor.nombre}</strong></a>
							<span class="item__dominio">{proveedor.dominio}</span>
							{#if proveedor.verificado}<Badge variante="abierto">✓ Verificado</Badge>{/if}
						</div>
						<div class="item__acciones">
							{#if proveedor.estado !== 'aprobado'}
								<Boton
									tamano="sm"
									variante="primario"
									disabled={!!accionEnCurso}
									onclick={() => accion(proveedor, 'aprobar')}
								>
									{accionEnCurso === `${proveedor.id}-aprobar` ? 'Aprobando…' : 'Aprobar'}
								</Boton>
							{/if}
							{#if proveedor.estado !== 'rechazado'}
								<Boton
									tamano="sm"
									variante="secundario"
									disabled={!!accionEnCurso}
									onclick={() => accion(proveedor, 'rechazar')}
								>
									{accionEnCurso === `${proveedor.id}-rechazar` ? 'Rechazando…' : 'Rechazar'}
								</Boton>
							{/if}
							{#if proveedor.estado === 'aprobado'}
								<Boton
									tamano="sm"
									variante="ghost"
									disabled={!!accionEnCurso}
									onclick={() => alternarVerificado(proveedor)}
								>
									{accionEnCurso === `${proveedor.id}-verificado`
										? 'Guardando…'
										: proveedor.verificado
											? 'Quitar verificado'
											: 'Marcar verificado'}
								</Boton>
							{/if}
							<Boton
								tamano="sm"
								variante="peligro-suave"
								disabled={!!accionEnCurso}
								onclick={() => borrar(proveedor)}
							>
								Borrar
							</Boton>
						</div>
					</li>
				{/each}
			</ul>
		{/if}
		<p class="ayuda">
			Para cargar muchos de una vez: <code>python manage.py importar_mayoristas archivo.csv</code>.
		</p>
	</section>

	<div class="lateral">
		<Tarjeta class="relleno" id="nuevo-mayorista">
			<form class="form" onsubmit={crear}>
				<h2>Agregar mayorista</h2>
				<Campo id="nuevo-nombre" etiqueta="Nombre" requerido error={erroresNuevo.nombre}>
					{#snippet children(props)}
						<input id="nuevo-nombre" bind:value={nuevo.nombre} required {...props} />
					{/snippet}
				</Campo>
				<Campo id="nuevo-sitio" etiqueta="Sitio" requerido error={erroresNuevo.sitio_url}>
					{#snippet children(props)}
						<input
							id="nuevo-sitio"
							type="url"
							bind:value={nuevo.sitio_url}
							required
							placeholder="https://…"
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo id="nuevo-provincia" etiqueta="Provincia" error={erroresNuevo.provincia}>
					{#snippet children(props)}
						<input id="nuevo-provincia" bind:value={nuevo.provincia} {...props} />
					{/snippet}
				</Campo>
				<Campo id="nuevo-minima" etiqueta="Compra mínima" error={erroresNuevo.compra_minima}>
					{#snippet children(props)}
						<input
							id="nuevo-minima"
							bind:value={nuevo.compra_minima}
							placeholder="Ej.: $ 50.000 o 12 unidades"
							{...props}
						/>
					{/snippet}
				</Campo>
				<div class="acciones">
					<Boton tipo="submit" variante="primario">Agregar</Boton>
				</div>
			</form>
		</Tarjeta>
		<Tarjeta class="relleno">
			<div class="form">
				<h2>Parámetros del comparador</h2>
				<p class="ayuda">Son valores de referencia: el comparador los muestra como estimación.</p>
				{#if cargandoParametros}
					<p class="ayuda" role="status">Cargando parámetros…</p>
				{/if}
				{#if errorParametros}
					<Aviso variante="error">{errorParametros}</Aviso>
				{/if}
				{#each parametros as parametro (parametro.clave)}
					<Campo
						id="parametro-{parametro.clave}"
						etiqueta={parametro.nombre}
						ayuda={`${parametro.ayuda ?? ''}${
							Number(parametro.valor) === 0 && parametro.clave.startsWith('tipo_cambio_')
								? ' Sin cargar: las ofertas de esa moneda no se convierten.'
								: ''
						}`}
					>
						{#snippet children(props)}
							<input
								id="parametro-{parametro.clave}"
								type="number"
								min="0"
								step="0.01"
								value={Number(parametro.valor)}
								disabled={guardandoParametro === parametro.clave}
								onchange={(e) => guardarParametro(parametro, e.currentTarget.value)}
								{...props}
							/>
						{/snippet}
					</Campo>
					{#if guardandoParametro === parametro.clave}
						<p class="ayuda" role="status">Guardando…</p>
					{/if}
				{/each}
			</div>
		</Tarjeta>
	</div>
</div>

<style>
	.columnas {
		display: grid;
		grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
		gap: var(--e-6);
		align-items: start;
	}

	.lateral {
		display: grid;
		gap: var(--e-5);
	}

	.filtro {
		display: flex;
		gap: var(--e-2);
		margin-bottom: var(--e-4);
	}

	.filtro__boton {
		min-height: var(--alto-tap);
		padding: 0.4rem 0.85rem;
		border: 1px solid var(--linea-control);
		border-radius: var(--radio-full);
		background: var(--superficie);
		font: inherit;
		font-size: var(--texto-sm);
		cursor: pointer;
	}

	.filtro__boton:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}

	.filtro__boton.activo {
		border-color: var(--marca-fuerte);
		background: var(--melocoton);
		color: var(--marca-fuerte);
		font-weight: 600;
	}

	.lista {
		display: grid;
		gap: var(--e-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.item {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: var(--e-3);
		padding: var(--e-3) 0;
		border-bottom: 1px solid var(--linea);
	}

	.item__dominio {
		margin: 0 var(--e-2);
		color: var(--tinta-tenue);
		font-size: var(--texto-sm);
	}

	.item__acciones {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
	}

	.form {
		display: grid;
	}

	.form h2 {
		margin: 0 0 var(--e-4);
		font-size: 1.1rem;
	}

	.vacio {
		color: var(--tinta-tenue);
		font-size: var(--texto-sm);
		font-weight: 400;
	}

	@media (max-width: 900px) {
		.columnas {
			grid-template-columns: 1fr;
		}
	}
</style>
