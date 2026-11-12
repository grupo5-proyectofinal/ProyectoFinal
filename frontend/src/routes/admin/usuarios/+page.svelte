<script>
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { alPerderAcceso } from '$lib/admin.svelte.js';
	import {
		esStaff,
		filtrosDeListado,
		nombreUsuario,
		ordenDeColumna,
		queryDeListado,
		rutaListado,
		rutaOrden,
		rutaPagina
	} from '$lib/admin.js';
	import { api } from '$lib/api.js';
	import { confirmar } from '$lib/confirmacion.svelte.js';
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
	let filtros = $state({ q: '', is_active: '', orden: '' });
	let pedido = 0;
	let seleccionados = $state([]);
	let accionMasiva = $state(false);
	let checkboxTodos = $state();

	$effect(() => {
		const f = filtrosDeListado(page.url.search);
		filtros.q = f.q;
		filtros.is_active = f.is_active;
		filtros.orden = f.orden;
		seleccionados = [];
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
	// PAGE_SIZE del API (config/settings.py).
	const totalPaginas = $derived(Math.max(1, Math.ceil((datos?.count ?? 0) / 12)));
	const seleccionables = $derived(
		(datos?.results ?? []).filter((usuario) => usuario.id !== session.user?.id)
	);
	const todosSeleccionados = $derived(
		seleccionables.length > 0 && seleccionados.length === seleccionables.length
	);

	// El checkbox del encabezado muestra el estado intermedio cuando hay algunos.
	$effect(() => {
		if (checkboxTodos) {
			checkboxTodos.indeterminate = seleccionados.length > 0 && !todosSeleccionados;
		}
	});

	function irAPagina(n) {
		goto(rutaPagina(page.url.search, n));
	}

	function flecha(campo) {
		const orden = ordenDeColumna(page.url.search, campo);
		return orden === 'ascending' ? ' ↑' : orden === 'descending' ? ' ↓' : '';
	}

	function alternarSeleccion(id) {
		seleccionados = seleccionados.includes(id)
			? seleccionados.filter((actual) => actual !== id)
			: [...seleccionados, id];
	}

	function alternarTodos() {
		seleccionados = todosSeleccionados ? [] : seleccionables.map((usuario) => usuario.id);
	}

	async function cambiarSeleccionados(activo) {
		const ids = seleccionados.filter((id) => id !== session.user?.id);
		if (!ids.length || accionMasiva) return;
		const aceptada = await confirmar({
			titulo: activo ? '¿Activar las cuentas seleccionadas?' : '¿Desactivar las cuentas seleccionadas?',
			descripcion: activo
				? `${ids.length} ${ids.length === 1 ? 'cuenta va a poder' : 'cuentas van a poder'} iniciar sesión de nuevo.`
				: `${ids.length} ${ids.length === 1 ? 'cuenta no va a poder' : 'cuentas no van a poder'} iniciar sesión hasta que las actives.`,
			confirmar: activo ? 'Activar' : 'Desactivar'
		});
		if (!aceptada) return;
		accionMasiva = true;
		try {
			await Promise.all(
				ids.map((id) =>
					api(`/admin/usuarios/${id}/`, { method: 'PATCH', body: { is_active: activo } })
				)
			);
			notificar(
				`${ids.length} ${ids.length === 1 ? 'cuenta actualizada' : 'cuentas actualizadas'}.`
			);
			seleccionados = [];
			await cargar(filtrosDeListado(page.url.search));
		} catch {
			notificar('No se pudieron actualizar todas las cuentas.', 'error');
		} finally {
			accionMasiva = false;
		}
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
		{#if seleccionados.length}
			<div class="masivo">
				<span>{seleccionados.length} seleccionados</span>
				<Boton
					tamano="sm"
					variante="secundario"
					disabled={accionMasiva}
					onclick={() => cambiarSeleccionados(true)}
				>
					Activar
				</Boton>
				<Boton
					tamano="sm"
					variante="peligro-suave"
					disabled={accionMasiva}
					onclick={() => cambiarSeleccionados(false)}
				>
					Desactivar
				</Boton>
			</div>
		{/if}
		<Tarjeta class="tabla-envoltura">
			<table class="tabla">
				<thead>
					<tr>
						<th scope="col" class="tabla__check">
							<input
								type="checkbox"
								bind:this={checkboxTodos}
								checked={todosSeleccionados}
								onchange={alternarTodos}
								aria-label="Seleccionar todos los usuarios de esta página"
							/>
						</th>
						<th scope="col" aria-sort={ordenDeColumna(page.url.search, 'nombre')}>
							<a class="tabla__orden" href={rutaOrden(page.url.search, 'nombre')}>
								Usuario{flecha('nombre')}
							</a>
						</th>
						<th scope="col" aria-sort={ordenDeColumna(page.url.search, 'email')}>
							<a class="tabla__orden" href={rutaOrden(page.url.search, 'email')}>
								Email{flecha('email')}
							</a>
						</th>
						<th scope="col" aria-sort={ordenDeColumna(page.url.search, 'estado')}>
							<a class="tabla__orden" href={rutaOrden(page.url.search, 'estado')}>
								Estado{flecha('estado')}
							</a>
						</th>
						<th scope="col"><span class="sr-only">Acciones</span></th>
					</tr>
				</thead>
				<tbody>
					{#each datos.results as usuario (usuario.id)}
						<tr>
							<td class="tabla__check">
								<input
									type="checkbox"
									checked={seleccionados.includes(usuario.id)}
									onchange={() => alternarSeleccion(usuario.id)}
									disabled={usuario.id === session.user?.id}
									title={usuario.id === session.user?.id
										? 'No podés desactivar tu propia cuenta'
										: undefined}
									aria-label={`Seleccionar ${nombreUsuario(usuario)}`}
								/>
							</td>
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
									href={resolve(`/admin/usuarios/${usuario.id}`)}
									aria-label={`Ver ${nombreUsuario(usuario)}`}>Ver</Boton
								>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</Tarjeta>

		<ul class="tarjetas-movil">
			{#each datos.results as usuario (usuario.id)}
				<li class="tarjeta-movil">
					<label class="tarjeta-movil__seleccion">
						<input
							type="checkbox"
							checked={seleccionados.includes(usuario.id)}
							onchange={() => alternarSeleccion(usuario.id)}
							disabled={usuario.id === session.user?.id}
							title={usuario.id === session.user?.id
								? 'No podés desactivar tu propia cuenta'
								: undefined}
						/>
						Seleccionar
					</label>
					<a class="tarjeta-movil__nombre" href={resolve(`/admin/usuarios/${usuario.id}`)}>
						{nombreUsuario(usuario)}
					</a>
					<span class="tarjeta-movil__dato">@{usuario.username}</span>
					<span class="tarjeta-movil__dato">{usuario.email}</span>
					<div class="tarjeta-movil__pie">
						<Badge variante={usuario.is_active ? 'activo' : 'inactivo'}>
							{usuario.is_active ? 'Activo' : 'Inactivo'}
						</Badge>
						<Boton
							variante="secundario"
							tamano="sm"
							href={resolve(`/admin/usuarios/${usuario.id}`)}
							aria-label={`Ver ${nombreUsuario(usuario)}`}
						>
							Ver
						</Boton>
					</div>
				</li>
			{/each}
		</ul>

		<nav class="paginacion" aria-label="Paginación de usuarios">
			<Boton
				variante="secundario"
				tipo="button"
				disabled={paginaActual <= 1}
				onclick={() => irAPagina(paginaActual - 1)}
			>
				Anterior
			</Boton>
			<span class="paginacion__estado">Página {paginaActual} de {totalPaginas}</span>
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

	.masivo {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--e-3);
		margin-bottom: var(--e-3);
		padding: var(--e-2) var(--e-3);
		border: 1px solid var(--borde-info);
		border-radius: var(--radio-sm);
		background: var(--info-suave);
		color: var(--texto-info);
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.tabla__check {
		width: 3rem;
		text-align: center;
	}

	.tabla__check input,
	.tarjeta-movil__seleccion input {
		width: 20px;
		height: 20px;
		min-height: 0;
	}

	.tabla__orden {
		color: inherit;
		font: inherit;
		font-weight: 600;
		letter-spacing: inherit;
		text-transform: inherit;
	}

	.tabla__orden:hover {
		color: var(--marca-fuerte);
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

	.tarjetas-movil {
		display: none;
	}

	@media (max-width: 640px) {
		:global(.tabla-envoltura.ui-tarjeta) {
			display: none;
		}

		.tarjetas-movil {
			display: grid;
			gap: var(--e-3);
			margin: 0;
			padding: 0;
			list-style: none;
		}

		.tarjeta-movil {
			display: grid;
			gap: var(--e-1);
			padding: var(--e-4);
			border: 1px solid var(--linea);
			border-radius: var(--radio);
			background: var(--superficie);
		}

		.tarjeta-movil__seleccion {
			display: flex;
			align-items: center;
			gap: var(--e-2);
			min-height: var(--alto-tap);
			color: var(--tinta-suave);
			font-size: var(--texto-xs);
			font-weight: 600;
			cursor: pointer;
		}

		.tarjeta-movil__nombre {
			font-weight: 700;
			color: var(--tinta);
		}

		.tarjeta-movil__dato {
			color: var(--tinta-suave);
			font-size: var(--texto-sm);
			overflow-wrap: anywhere;
		}

		.tarjeta-movil__pie {
			display: flex;
			flex-wrap: wrap;
			align-items: center;
			justify-content: space-between;
			gap: var(--e-3);
			margin-top: var(--e-2);
		}
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
