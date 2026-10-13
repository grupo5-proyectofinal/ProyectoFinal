<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { alPerderAcceso } from '$lib/admin.svelte.js';
	import {
		esStaff,
		filtrosDeListado,
		nombreUsuario,
		queryDeListado,
		rutaListado,
		rutaPagina
	} from '$lib/admin.js';
	import { api } from '$lib/api.js';
	import { session } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let datos = $state(null);
	let cargando = $state(true);
	let error = $state('');
	let filtros = $state({ q: '', is_active: '' });
	let pedido = 0;

	$effect(() => {
		const f = filtrosDeListado(page.url.search);
		filtros.q = f.q;
		filtros.is_active = f.is_active;
		if (esStaff(session.user)) cargar(f);
	});

	async function cargar(f) {
		const actual = ++pedido;
		cargando = true;
		error = '';
		try {
			const r = await api('/admin/usuarios/', { query: queryDeListado(f) });
			if (actual === pedido) datos = r;
		} catch (e) {
			if (actual !== pedido) return;
			datos = null;
			if (e.status === 403) {
				alPerderAcceso();
				return;
			}
			if (e.status === 404) {
				// Página fuera de rango (DRF): volver a la primera con los filtros.
				notificar('Esa página no existe.', 'aviso');
				goto(rutaPagina(page.url.search, 1));
				return;
			}
			error = 'No se pudieron cargar los usuarios. Recargá la página para volver a intentar.';
		} finally {
			if (actual === pedido) cargando = false;
		}
	}

	function aplicar(event) {
		event.preventDefault();
		goto(rutaListado(filtros));
	}

	const paginaActual = $derived(filtrosDeListado(page.url.search).pagina);
	const hayFiltros = $derived(Boolean(filtros.q || filtros.is_active));

	function irAPagina(n) {
		goto(rutaPagina(page.url.search, n));
	}
</script>

<svelte:head>
	<title>Usuarios — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Usuarios</h1>
		<p>Administrá las cuentas: buscá, editá y activá o desactivá usuarios.</p>
	</div>
	<div class="cabecera-pagina__acciones">
		<Boton variante="primario" href={resolve('/admin/usuarios/nuevo')}>Nuevo usuario</Boton>
	</div>
</div>

{#if !session.user}
	{#if session.loading}
		<div class="cargando" role="status"><span class="spinner"></span> Cargando tu sesión…</div>
	{:else}
		<Aviso variante="error">
			No se pudieron cargar tus datos. Recargá la página para volver a intentar.
		</Aviso>
	{/if}
{:else}
	<Tarjeta class="filtros">
		<form onsubmit={aplicar}>
			<div class="filtros__grilla">
				<Campo id="q" etiqueta="Buscar">
					{#snippet children(props)}
						<input
							id="q"
							name="q"
							type="search"
							bind:value={filtros.q}
							placeholder="Email, usuario o nombre"
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo id="is_active" etiqueta="Estado">
					{#snippet children(props)}
						<select id="is_active" name="is_active" bind:value={filtros.is_active} {...props}>
							<option value="">Todos</option>
							<option value="true">Activos</option>
							<option value="false">Inactivos</option>
						</select>
					{/snippet}
				</Campo>
			</div>
			<div class="filtros__acciones">
				<Boton variante="primario" tipo="submit">Filtrar</Boton>
				<Boton variante="ghost" href={resolve('/admin/usuarios')}>Limpiar filtros</Boton>
			</div>
		</form>
	</Tarjeta>

	{#if cargando}
		<div class="cargando" role="status"><span class="spinner"></span> Cargando usuarios…</div>
	{:else if error}
		<Aviso variante="error">{error}</Aviso>
	{:else if datos?.results?.length}
		<p class="resultado-cuenta" role="status">
			{datos.count}
			{datos.count === 1 ? 'usuario' : 'usuarios'}
		</p>
		<Tarjeta class="tabla-envoltura">
			<table class="tabla">
				<thead>
					<tr>
						<th scope="col">Usuario</th>
						<th scope="col">Email</th>
						<th scope="col">Estado</th>
						<th scope="col"><span class="sr-only">Acciones</span></th>
					</tr>
				</thead>
				<tbody>
					{#each datos.results as usuario (usuario.id)}
						<tr>
							<td>
								<a class="tabla__nombre" href={resolve(`/admin/usuarios/${usuario.id}`)}>
									{nombreUsuario(usuario)}
								</a>
								<span class="tabla__usuario">@{usuario.username}</span>
								{#if usuario.is_staff}
									<Badge variante="staff" class="tabla__badge">Admin</Badge>
								{/if}
							</td>
							<td>{usuario.email}</td>
							<td>
								<Badge variante={usuario.is_active ? 'activo' : 'inactivo'}>
									{usuario.is_active ? 'Activo' : 'Inactivo'}
								</Badge>
							</td>
							<td class="tabla__acciones">
								<Boton
									variante="secundario"
									tamano="sm"
									href={resolve(`/admin/usuarios/${usuario.id}`)}>Ver</Boton
								>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</Tarjeta>

		<nav class="paginacion" aria-label="Paginación de usuarios">
			<Boton
				variante="secundario"
				tipo="button"
				disabled={paginaActual <= 1}
				onclick={() => irAPagina(paginaActual - 1)}
			>
				Anterior
			</Boton>
			<span class="paginacion__estado">Página {paginaActual}</span>
			<Boton
				variante="secundario"
				tipo="button"
				disabled={!datos.next}
				onclick={() => irAPagina(paginaActual + 1)}
			>
				Siguiente
			</Boton>
		</nav>
	{:else}
		<div class="vacio">
			<h3>{hayFiltros ? 'No se encontraron usuarios' : 'Todavía no hay usuarios'}</h3>
			<p>
				{#if hayFiltros}
					Probá quitar algún filtro o buscar con otras palabras.
				{:else}
					Creá la primera cuenta desde este panel.
				{/if}
			</p>
			<div class="vacio__acciones">
				{#if hayFiltros}
					<Boton variante="secundario" href={resolve('/admin/usuarios')}>Limpiar filtros</Boton>
				{/if}
				<Boton variante="primario" href={resolve('/admin/usuarios/nuevo')}>Nuevo usuario</Boton>
			</div>
		</div>
	{/if}
{/if}

<style>
	/* Las clases viajan a la primitiva Tarjeta (sin el scope de la página): el
	   selector :global va completo, como en las fases 3-5. */
	:global(.filtros.ui-tarjeta) {
		padding: clamp(1.25rem, 2.5vw, 1.75rem);
		margin-bottom: var(--e-6);
	}

	.filtros__grilla {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 0 var(--e-4);
	}

	.filtros__grilla :global(.ui-campo) {
		margin-bottom: 0;
	}

	.filtros__grilla input[type='search'] {
		min-height: 44px;
		font-size: var(--texto-base);
	}

	.filtros__acciones {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3);
		margin-top: var(--e-3);
		padding-top: var(--e-4);
		border-top: 1px solid var(--linea);
	}

	.resultado-cuenta {
		margin-bottom: var(--e-4);
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}

	:global(.tabla-envoltura.ui-tarjeta) {
		overflow-x: auto;
		/* El `.sr-only` del encabezado es absoluto: sin un ancestro posicionado su
		   bloque contenedor es la página y su posición (dentro de la tabla, que
		   desborda) estira el documento en móvil. Con `relative` lo recorta el
		   propio contenedor de scroll. */
		position: relative;
	}

	.tabla {
		width: 100%;
		border-collapse: collapse;
		font-size: var(--texto-sm);
	}

	.tabla th {
		padding: var(--e-3) var(--e-4);
		border-bottom: 1px solid var(--linea);
		color: var(--tinta-tenue);
		font-size: var(--texto-xs);
		font-weight: 600;
		letter-spacing: 0.04em;
		text-align: left;
		text-transform: uppercase;
	}

	.tabla td {
		padding: var(--e-4);
		border-bottom: 1px solid var(--linea);
		vertical-align: middle;
	}

	.tabla tbody tr:last-child td {
		border-bottom: none;
	}

	.tabla__nombre {
		font-weight: 600;
		color: var(--tinta);
	}

	.tabla__usuario {
		display: block;
		color: var(--tinta-suave);
		font-size: var(--texto-xs);
	}

	:global(.tabla__badge.ui-badge) {
		margin-left: var(--e-2);
	}

	.tabla__acciones {
		text-align: right;
	}

	.vacio__acciones {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: var(--e-3);
	}

	.paginacion {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--e-4);
		margin-top: var(--e-7);
		padding-top: var(--e-5);
		border-top: 1px solid var(--linea);
	}

	.paginacion__estado {
		font-size: var(--texto-sm);
		color: var(--tinta-suave);
	}
</style>
