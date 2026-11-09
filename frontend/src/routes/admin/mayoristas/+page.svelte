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
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let estado = $state('pendiente');
	let proveedores = $state([]);
	let parametros = $state([]);
	let nuevo = $state({ nombre: '', sitio_url: '', provincia: '', compra_minima: '' });
	let erroresNuevo = $state({});
	let pedido = 0;

	$effect(() => {
		if (esStaff(session.user)) cargar(estado);
	});

	$effect(() => {
		if (esStaff(session.user)) api('/parametros-costo/').then((r) => (parametros = r));
	});

	async function cargar(filtro) {
		const actual = ++pedido;
		const r = await api('/proveedores/', { query: { estado: filtro } });
		if (actual === pedido) proveedores = r.results ?? r;
	}

	async function accion(proveedor, nombre) {
		await api(`/proveedores/${proveedor.id}/${nombre}/`, { method: 'POST' });
		notificar(nombre === 'aprobar' ? `${proveedor.nombre} publicado.` : `${proveedor.nombre} rechazado.`);
		cargar(estado);
	}

	async function alternarVerificado(proveedor) {
		await api(`/proveedores/${proveedor.id}/`, {
			method: 'PATCH',
			body: { verificado: !proveedor.verificado }
		});
		cargar(estado);
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
		erroresNuevo = {};
		try {
			await api('/proveedores/', { method: 'POST', body: nuevo });
			nuevo = { nombre: '', sitio_url: '', provincia: '', compra_minima: '' };
			notificar('Mayorista agregado y publicado.');
			estado = 'aprobado';
			cargar(estado);
		} catch (e) {
			erroresNuevo = fieldErrors(e.data);
		}
	}

	async function guardarParametro(parametro, valor) {
		try {
			await api(`/parametros-costo/${parametro.clave}/`, { method: 'PATCH', body: { valor } });
			notificar(`${parametro.nombre} actualizado.`);
		} catch (e) {
			notificar(fieldErrors(e.data).valor ?? 'No se pudo guardar.', 'error');
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

<div class="columnas">
	<section>
		<div class="filtro" role="group" aria-label="Estado">
			{#each Object.entries(ESTADOS_PROVEEDOR) as [clave, datos] (clave)}
				<button type="button" class="filtro__boton" class:activo={estado === clave} onclick={() => (estado = clave)}>
					{datos.texto}
				</button>
			{/each}
		</div>
		{#if !proveedores.length}
			<p class="vacio">No hay mayoristas en este estado.</p>
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
								<Boton tamano="sm" variante="primario" onclick={() => accion(proveedor, 'aprobar')}>Aprobar</Boton>
							{/if}
							{#if proveedor.estado !== 'rechazado'}
								<Boton tamano="sm" variante="secundario" onclick={() => accion(proveedor, 'rechazar')}>Rechazar</Boton>
							{/if}
							{#if proveedor.estado === 'aprobado'}
								<Boton tamano="sm" variante="ghost" onclick={() => alternarVerificado(proveedor)}>
									{proveedor.verificado ? 'Quitar verificado' : 'Marcar verificado'}
								</Boton>
							{/if}
							<Boton tamano="sm" variante="peligro-suave" onclick={() => borrar(proveedor)}>Borrar</Boton>
						</div>
					</li>
				{/each}
			</ul>
		{/if}
		<p class="vacio">
			Para cargar muchos de una vez: <code>python manage.py importar_mayoristas archivo.csv</code>.
		</p>
	</section>

	<div class="lateral">
		<Tarjeta class="relleno">
			<form class="form" onsubmit={crear}>
				<h2>Agregar mayorista</h2>
				<label class="campo"><span>Nombre *</span><input bind:value={nuevo.nombre} required /></label>
				<label class="campo">
					<span>Sitio *</span><input type="url" bind:value={nuevo.sitio_url} required placeholder="https://…" />
					{#if erroresNuevo.sitio_url}<small class="error">{erroresNuevo.sitio_url}</small>{/if}
				</label>
				<label class="campo"><span>Provincia</span><input bind:value={nuevo.provincia} /></label>
				<label class="campo"><span>Compra mínima</span><input bind:value={nuevo.compra_minima} placeholder="Ej.: $ 50.000 o 12 unidades" /></label>
				<Boton type="submit" variante="primario">Agregar</Boton>
			</form>
		</Tarjeta>
		<Tarjeta class="relleno">
			<div class="form">
				<h2>Parámetros del comparador</h2>
				<p class="vacio">Son valores de referencia: el comparador los muestra como estimación.</p>
				{#each parametros as parametro (parametro.clave)}
					<label class="campo">
						<span>{parametro.nombre}</span>
						<input
							type="number"
							min="0"
							step="0.01"
							value={Number(parametro.valor)}
							onchange={(e) => guardarParametro(parametro, e.currentTarget.value)}
						/>
						<small class="ayuda">{parametro.ayuda}</small>
					</label>
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
		padding: 0.4rem 0.85rem;
		border: 1px solid var(--linea-control);
		border-radius: 999px;
		background: var(--superficie);
		font: inherit;
		font-size: var(--texto-sm);
		cursor: pointer;
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
		gap: var(--e-3);
	}

	.form h2 {
		margin: 0;
		font-size: 1.1rem;
	}

	.campo {
		display: grid;
		gap: var(--e-1);
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.ayuda,
	.vacio {
		color: var(--tinta-tenue);
		font-size: var(--texto-sm);
		font-weight: 400;
	}

	.error {
		color: var(--texto-peligro);
		font-weight: 400;
	}

	@media (max-width: 900px) {
		.columnas {
			grid-template-columns: 1fr;
		}
	}
</style>
