<script>
	// Categoría en dos niveles (Ropa > Remera) y la variante del pool: una sola
	// opción por atributo (Talle S, Color Negro). Expone `categoria` y `atributos` (JSON) como inputs ocultos:
	// los formularios que leen FormData los mandan sin código extra.
	import {
		atributosDe,
		atributosElegidos,
		hijas,
		raices,
		separarCategoria
	} from '$lib/variantes.js';
	import { AYUDAS } from '$lib/ayudasPool.js';
	import InfoAyuda from '$lib/InfoAyuda.svelte';
	import Campo from '$lib/ui/Campo.svelte';

	let {
		categorias = [],
		categoriaId = $bindable(''),
		atributos = $bindable({}),
		errores = {},
		bloqueado = false
	} = $props();

	let raiz = $state('');
	let sub = $state('');

	// Si la categoría cambia desde afuera (pool cargado, borrador), se reflejan los selects.
	$effect(() => {
		if (String(categoriaId ?? '') === (sub || raiz)) return;
		const separada = separarCategoria(categorias, categoriaId);
		raiz = separada.raiz;
		sub = separada.sub;
	});

	const opcionesRaiz = $derived(raices(categorias));
	const opcionesSub = $derived(hijas(categorias, raiz));
	const atributosCategoria = $derived(atributosDe(categorias, categoriaId));
	const elegidos = $derived(atributosElegidos(atributosCategoria, atributos));

	function elegirRaiz(evento) {
		raiz = evento.currentTarget.value;
		sub = '';
		categoriaId = raiz;
	}

	function elegirSub(evento) {
		sub = evento.currentTarget.value;
		categoriaId = sub || raiz;
	}

	function elegir(nombre, opcion) {
		atributos = { ...atributos, [nombre]: opcion ? [opcion] : [] };
	}
</script>

<input type="hidden" name="categoria" value={categoriaId ?? ''} />
<input type="hidden" name="atributos" value={JSON.stringify(elegidos)} />

<Campo id="categoria" etiqueta="Categoría" info={AYUDAS.categoria} requerido error={errores.categoria}>
	{#snippet children(props)}
		<select id="categoria" required value={raiz} onchange={elegirRaiz} disabled={bloqueado} {...props}>
			<option value="">Elegí una</option>
			{#each opcionesRaiz as categoria (categoria.id)}
				<option value={String(categoria.id)}>{categoria.nombre}</option>
			{/each}
		</select>
	{/snippet}
</Campo>

{#if opcionesSub.length}
	<Campo
		id="subcategoria"
		etiqueta="Tipo de producto"
		info={AYUDAS.subcategoria}
		ayuda="Opcional. Con el tipo podés indicar talle, color, etc."
	>
		{#snippet children(props)}
			<select id="subcategoria" value={sub} onchange={elegirSub} disabled={bloqueado} {...props}>
				<option value="">Sin especificar</option>
				{#each opcionesSub as categoria (categoria.id)}
					<option value={String(categoria.id)}>{categoria.nombre}</option>
				{/each}
			</select>
		{/snippet}
	</Campo>
{/if}

{#if atributosCategoria.length}
	<fieldset class="variantes" disabled={bloqueado}>
		<legend class="variantes__titulo">
			Variante <span>(opcional)</span>
			<InfoAyuda titulo="Variante" etiqueta="Qué es «Variante»">{AYUDAS.variante}</InfoAyuda>
		</legend>
		<p class="variantes__ayuda">
			El pool es de una sola variante: todos piden la misma. Dejá en «Sin especificar» lo que no
			aplique.
		</p>
		{#each atributosCategoria as atributo (atributo.nombre)}
			{@const marcadas = elegidos[atributo.nombre] ?? []}
			<Campo id={`atributo-${atributo.nombre}`} etiqueta={atributo.nombre}>
				{#snippet children(props)}
					<select
						id={`atributo-${atributo.nombre}`}
						value={marcadas.length === 1 ? marcadas[0] : ''}
						onchange={(e) => elegir(atributo.nombre, e.currentTarget.value)}
						{...props}
					>
						<option value="">{marcadas.length > 1 ? marcadas.join(', ') : 'Sin especificar'}</option>
						{#each atributo.opciones as opcion (opcion)}
							<option value={opcion}>{opcion}</option>
						{/each}
					</select>
				{/snippet}
			</Campo>
		{/each}
		{#if errores.atributos}
			<p class="variantes__error" role="alert">{errores.atributos}</p>
		{/if}
		{#if bloqueado}
			<p class="variantes__ayuda">Ya hay integrantes: la categoría y la variante no se pueden cambiar.</p>
		{/if}
	</fieldset>
{/if}

<style>
	.variantes {
		display: grid;
		gap: var(--e-3);
		margin: 0;
		padding: var(--e-4);
		border: 1px solid var(--linea);
		border-radius: var(--radio-sm);
		background: var(--crema);
	}

	.variantes__titulo {
		display: flex;
		align-items: center;
		gap: var(--e-1);
		padding: 0 var(--e-1);
		font-weight: 700;
	}

	.variantes__titulo :global(.info__boton) {
		width: 1.75rem;
		height: 1.75rem;
		margin-block: -0.4rem;
	}

	.variantes__titulo span,
	.variantes__ayuda {
		font-weight: 400;
		font-size: var(--texto-sm);
		color: var(--tinta-tenue);
	}

	.variantes__ayuda {
		margin: 0;
	}

	.variantes__error {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--texto-peligro);
	}
</style>
