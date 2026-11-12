<script>
	// Backoffice de categorías: subcategorías (Ropa > Remera) y sus atributos
	// (Talle, Color…). Las opciones se escriben separadas por coma.
	import { api, fieldErrors } from '$lib/api.js';
	import { esStaff } from '$lib/admin.js';
	import { confirmar } from '$lib/confirmacion.svelte.js';
	import { session } from '$lib/session.svelte.js';
	import { notificar } from '$lib/toast.svelte.js';
	import { hijas, raices } from '$lib/variantes.js';
	import Aviso from '$lib/ui/Aviso.svelte';
	import Boton from '$lib/ui/Boton.svelte';
	import Campo from '$lib/ui/Campo.svelte';
	import Tarjeta from '$lib/ui/Tarjeta.svelte';

	let categorias = $state([]);
	let elegida = $state(null);
	let filas = $state([]);
	let errorAtributos = $state('');
	let nueva = $state({ nombre: '', padre: '' });
	let erroresNueva = $state({});
	let cargando = $state(true);
	let errorCarga = $state('');

	$effect(() => {
		if (esStaff(session.user)) cargar();
	});

	async function cargar() {
		cargando = true;
		errorCarga = '';
		try {
			categorias = await api('/categories/').then((r) => r.results ?? r);
			if (elegida) elegir(categorias.find((c) => c.id === elegida.id) ?? null);
		} catch {
			errorCarga = 'No se pudieron cargar las categorías.';
		} finally {
			cargando = false;
		}
	}

	function elegir(categoria) {
		elegida = categoria;
		errorAtributos = '';
		filas = (categoria?.propios ?? []).map((a) => ({ nombre: a.nombre, opciones: a.opciones.join(', ') }));
	}

	async function guardarAtributos() {
		errorAtributos = '';
		const atributos = filas
			.filter((f) => f.nombre.trim())
			.map((f) => ({ nombre: f.nombre, opciones: f.opciones.split(',').map((o) => o.trim()).filter(Boolean) }));
		try {
			await api(`/categories/${elegida.id}/atributos/`, { method: 'PUT', body: { atributos } });
			notificar(`Atributos de ${elegida.nombre} guardados.`);
			await cargar();
		} catch (e) {
			const errores = fieldErrors(e.data);
			errorAtributos = errores.atributos || errores.detail || 'No se pudo guardar.';
		}
	}

	async function crear(evento) {
		evento.preventDefault();
		erroresNueva = {};
		try {
			await api('/categories/', {
				method: 'POST',
				body: { nombre: nueva.nombre, padre: nueva.padre ? Number(nueva.padre) : null }
			});
			notificar(`Categoría ${nueva.nombre} creada.`);
			nueva = { nombre: '', padre: '' };
			await cargar();
		} catch (e) {
			erroresNueva = fieldErrors(e.data);
			if (!Object.keys(erroresNueva).length) erroresNueva = { detail: 'No se pudo crear.' };
		}
	}

	async function borrar(categoria) {
		const subcategorias = hijas(categorias, categoria.id).length;
		const consecuencia = subcategorias
			? `Tiene ${subcategorias} ${subcategorias === 1 ? 'subcategoría' : 'subcategorías'}. Primero hay que moverlas o borrarlas.`
			: 'Se borran sus atributos. Solo se puede borrar si ningún pool la está usando.';
		const aceptada = await confirmar({
			titulo: `¿Borrar ${categoria.nombre}?`,
			descripcion: `${consecuencia} No se puede deshacer.`,
			confirmar: 'Borrar'
		});
		if (!aceptada) return;
		try {
			await api(`/categories/${categoria.id}/`, { method: 'DELETE' });
			if (elegida?.id === categoria.id) elegir(null);
			await cargar();
		} catch (e) {
			notificar(fieldErrors(e.data).detail ?? 'No se pudo borrar.', 'error');
		}
	}

	function heredados(categoria) {
		const propios = new Set((categoria?.propios ?? []).map((a) => a.nombre));
		return (categoria?.atributos ?? []).filter((a) => !propios.has(a.nombre));
	}
</script>

<svelte:head>
	<title>Categorías (admin) — PoolShop</title>
</svelte:head>

<div class="cabecera-pagina">
	<div>
		<h1>Categorías</h1>
		<p>
			Las subcategorías heredan los atributos de su categoría principal. Si sacás una opción, los
			pools que la ofrecían dejan de ofrecerla.
		</p>
	</div>
</div>

{#if cargando}
	<p class="muted" role="status">Cargando categorías…</p>
{:else if errorCarga}
	<Aviso variante="error">
		{errorCarga}
		<Boton variante="ghost" tamano="sm" onclick={cargar}>Reintentar</Boton>
	</Aviso>
{/if}

<div class="columnas">
	<section class="arbol-seccion">
		<ul class="arbol">
			{#each raices(categorias) as raiz (raiz.id)}
				<li>
					<div class="nodo" class:activo={elegida?.id === raiz.id}>
						<button
							type="button"
							class="nodo__nombre"
							aria-label={`Editar atributos de ${raiz.nombre}`}
							aria-current={elegida?.id === raiz.id ? 'true' : undefined}
							onclick={() => elegir(raiz)}>{raiz.nombre}</button
						>
						<button type="button" class="nodo__borrar" aria-label={`Borrar ${raiz.nombre}`} onclick={() => borrar(raiz)}>✕</button>
					</div>
					{#if hijas(categorias, raiz.id).length}
						<ul>
							{#each hijas(categorias, raiz.id) as hija (hija.id)}
								<li>
									<div class="nodo" class:activo={elegida?.id === hija.id}>
										<button
											type="button"
											class="nodo__nombre"
											aria-label={`Editar atributos de ${hija.nombre}`}
											aria-current={elegida?.id === hija.id ? 'true' : undefined}
											onclick={() => elegir(hija)}>{hija.nombre}</button
										>
										<button type="button" class="nodo__borrar" aria-label={`Borrar ${hija.nombre}`} onclick={() => borrar(hija)}>✕</button>
									</div>
								</li>
							{/each}
						</ul>
					{/if}
				</li>
			{/each}
		</ul>
		{#if !cargando && !errorCarga && !categorias.length}
			<p class="ayuda">Todavía no hay categorías. Creá la primera con el formulario.</p>
		{/if}
	</section>

	<Tarjeta class="relleno nueva-card">
		<form class="form" onsubmit={crear}>
				<h2>Nueva categoría</h2>
				<Campo
					id="nueva-nombre"
					etiqueta="Nombre"
					requerido
					error={erroresNueva.nombre}
				>
					{#snippet children(props)}
						<input
							id="nueva-nombre"
							bind:value={nueva.nombre}
							required
							maxlength="100"
							{...props}
						/>
					{/snippet}
				</Campo>
				<Campo id="nueva-padre" etiqueta="Dentro de" error={erroresNueva.padre}>
					{#snippet children(props)}
						<select id="nueva-padre" bind:value={nueva.padre} {...props}>
							<option value="">Ninguna (categoría principal)</option>
							{#each raices(categorias) as raiz (raiz.id)}
								<option value={String(raiz.id)}>{raiz.nombre}</option>
							{/each}
						</select>
					{/snippet}
				</Campo>
				{#if erroresNueva.detail}<Aviso variante="error">{erroresNueva.detail}</Aviso>{/if}
				<Boton type="submit" variante="primario">Crear</Boton>
		</form>
	</Tarjeta>

	<Tarjeta class="relleno atributos-card">
		{#if elegida}
			<div class="form">
				<h2>Atributos de {elegida.nombre}</h2>
				{#if heredados(elegida).length}
					<p class="ayuda">Hereda: {heredados(elegida).map((a) => a.nombre).join(', ')}.</p>
				{/if}
				{#each filas as fila, i (i)}
					<div class="fila">
						<Campo id={`atributo-nombre-${i}`} etiqueta="Nombre">
							{#snippet children(props)}
								<input
									id={`atributo-nombre-${i}`}
									bind:value={fila.nombre}
									maxlength="40"
									placeholder="Talle"
									{...props}
								/>
							{/snippet}
						</Campo>
						<Campo id={`atributo-opciones-${i}`} etiqueta="Opciones (separadas por coma)">
							{#snippet children(props)}
								<input
									id={`atributo-opciones-${i}`}
									bind:value={fila.opciones}
									placeholder="S, M, L, XL"
									{...props}
								/>
							{/snippet}
						</Campo>
						<button
							type="button"
							class="nodo__borrar"
							aria-label="Quitar atributo"
							onclick={() => (filas = filas.filter((_, j) => j !== i))}>✕</button
						>
					</div>
				{/each}
				<button type="button" class="agregar" onclick={() => (filas = [...filas, { nombre: '', opciones: '' }])}>
					+ Agregar atributo
				</button>
				{#if errorAtributos}<Aviso variante="error">{errorAtributos}</Aviso>{/if}
				<Boton variante="primario" onclick={guardarAtributos}>Guardar atributos</Boton>
			</div>
		{:else}
			<p class="ayuda">Elegí una categoría para ver y editar sus atributos.</p>
		{/if}
	</Tarjeta>
</div>

<style>
	.columnas {
		display: grid;
		grid-template-columns: minmax(0, 2fr) minmax(0, 3fr);
		grid-template-rows: auto 1fr;
		gap: var(--e-6);
		align-items: start;
	}

	.arbol-seccion {
		grid-column: 1;
		grid-row: 1;
	}

	/* Las clases viajan a la primitiva Tarjeta: el selector necesita :global. */
	:global(.nueva-card.ui-tarjeta) {
		grid-column: 1;
		grid-row: 2;
	}

	:global(.atributos-card.ui-tarjeta) {
		grid-column: 2;
		grid-row: 1 / span 2;
	}

	section {
		display: grid;
		gap: var(--e-5);
	}

	.arbol,
	.arbol ul {
		display: grid;
		gap: var(--e-1);
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.arbol ul {
		margin: var(--e-1) 0 0 var(--e-5);
	}

	.nodo {
		display: flex;
		justify-content: space-between;
		align-items: center;
		border-radius: var(--radio-sm);
	}

	.nodo.activo {
		background: var(--melocoton);
	}

	.nodo:hover {
		background: var(--crema);
	}

	.nodo__nombre {
		flex: 1;
		min-height: var(--alto-tap);
		padding: 0.45rem 0.6rem;
		border: 0;
		background: none;
		font: inherit;
		text-align: left;
		cursor: pointer;
	}

	.nodo__nombre:hover {
		text-decoration: underline;
	}

	.nodo__borrar {
		display: grid;
		place-items: center;
		width: var(--alto-tap);
		height: var(--alto-tap);
		border: 0;
		background: none;
		padding: 0;
		color: var(--tinta-tenue);
		cursor: pointer;
	}

	.nodo__borrar:hover {
		color: var(--peligro);
	}

	.form {
		display: grid;
		gap: var(--e-3);
	}

	.form h2 {
		margin: 0;
		font-size: 1.1rem;
	}

	.fila {
		display: flex;
		gap: var(--e-2);
		align-items: end;
	}

	.fila :global(.ui-campo) {
		flex: 1;
		margin-bottom: 0;
	}

	.fila :global(.ui-campo:nth-child(2)) {
		flex: 1.6;
	}

	.agregar {
		justify-self: start;
		border: 0;
		background: none;
		padding: 0;
		font: inherit;
		font-weight: 600;
		color: var(--marca-fuerte);
		cursor: pointer;
	}

	.ayuda {
		margin: 0;
		color: var(--tinta-tenue);
		font-size: var(--texto-sm);
	}

	@media (max-width: 900px) {
		.columnas {
			grid-template-columns: 1fr;
			grid-template-rows: auto;
		}

		/* El editor queda pegado al árbol, antes de "Nueva categoría". */
		.arbol-seccion,
		:global(.atributos-card.ui-tarjeta),
		:global(.nueva-card.ui-tarjeta) {
			grid-column: 1;
			grid-row: auto;
		}

		.arbol-seccion {
			order: 1;
		}

		:global(.atributos-card.ui-tarjeta) {
			order: 2;
		}

		:global(.nueva-card.ui-tarjeta) {
			order: 3;
		}
	}
</style>
