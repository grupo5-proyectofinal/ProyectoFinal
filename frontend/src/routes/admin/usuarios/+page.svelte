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
		<a class="btn btn--primario" href={resolve('/admin/usuarios/nuevo')}>Nuevo usuario</a>
	</div>
</div>

{#if !session.user}
	{#if session.loading}
		<div class="cargando" role="status"><span class="spinner"></span> Cargando tu sesión…</div>
	{:else}
		<div class="alerta alerta--error" role="alert">
			No se pudieron cargar tus datos. Recargá la página para volver a intentar.
		</div>
	{/if}
{:else}
	<form class="panel filtros" onsubmit={aplicar}>
		<div class="filtros__grilla">
			<div class="campo filtros__busqueda">
				<label for="q">Buscar</label>
				<input
					id="q"
					name="q"
					type="search"
					bind:value={filtros.q}
					placeholder="Email, usuario o nombre"
				/>
			</div>
			<div class="campo">
				<label for="is_active">Estado</label>
				<select id="is_active" name="is_active" bind:value={filtros.is_active}>
					<option value="">Todos</option>
					<option value="true">Activos</option>
					<option value="false">Inactivos</option>
				</select>
			</div>
		</div>
		<div class="filtros__acciones">
			<button class="btn btn--primario" type="submit">Filtrar</button>
			<a class="btn btn--ghost" href={resolve('/admin/usuarios')}>Limpiar filtros</a>
		</div>
	</form>

	{#if cargando}
		<div class="cargando" role="status"><span class="spinner"></span> Cargando usuarios…</div>
	{:else if error}
		<div class="alerta alerta--error" role="alert">{error}</div>
	{:else if datos?.results?.length}
		<p class="resultado-cuenta" role="status">
			{datos.count}
			{datos.count === 1 ? 'usuario' : 'usuarios'}
		</p>
		<div class="panel tabla-envoltura">
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
								{#if usuario.is_staff}<span class="badge badge--staff">Admin</span>{/if}
							</td>
							<td>{usuario.email}</td>
							<td>
								<span class="badge {usuario.is_active ? 'badge--activo' : 'badge--inactivo'}">
									{usuario.is_active ? 'Activo' : 'Inactivo'}
								</span>
							</td>
							<td class="tabla__acciones">
								<a
									class="btn btn--secundario btn--sm"
									href={resolve(`/admin/usuarios/${usuario.id}`)}>Ver</a
								>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<nav class="paginacion" aria-label="Paginación de usuarios">
			<button
				class="btn btn--secundario"
				type="button"
				disabled={paginaActual <= 1}
				onclick={() => irAPagina(paginaActual - 1)}
			>
				Anterior
			</button>
			<span class="paginacion__estado">Página {paginaActual}</span>
			<button
				class="btn btn--secundario"
				type="button"
				disabled={!datos.next}
				onclick={() => irAPagina(paginaActual + 1)}
			>
				Siguiente
			</button>
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
					<a class="btn btn--secundario" href={resolve('/admin/usuarios')}>Limpiar filtros</a>
				{/if}
				<a class="btn btn--primario" href={resolve('/admin/usuarios/nuevo')}>Nuevo usuario</a>
			</div>
		</div>
	{/if}
{/if}

<style>
	.filtros {
		padding: clamp(1.25rem, 2.5vw, 1.75rem);
		margin-bottom: var(--e-6);
	}

	.filtros__busqueda input {
		min-height: 44px;
		font-size: var(--texto-base);
	}

	.filtros__grilla {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 0 var(--e-4);
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

	.tabla-envoltura {
		overflow-x: auto;
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

	.tabla__acciones {
		text-align: right;
	}

	.badge--activo {
		background: var(--exito-suave);
		color: var(--exito);
		border-color: #c6ddcf;
	}

	.badge--inactivo {
		background: var(--superficie-alt);
		color: var(--tinta-suave);
		border-color: var(--linea);
	}

	.badge--staff {
		margin-left: var(--e-2);
		background: var(--acento-suave);
		color: var(--acento);
		border-color: #ccd5f0;
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
