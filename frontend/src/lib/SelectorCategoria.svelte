<script>
	// Categoría en dos niveles (Ropa > Remera) y variantes que ofrece el pool
	// (Talle, Color…). Expone `categoria` y `atributos` (JSON) como inputs ocultos:
	// los formularios que leen FormData los mandan sin código extra.
	import {
		atributosDe,
		atributosElegidos,
		hijas,
		raices,
		separarCategoria
	} from '$lib/variantes.js';
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

	function alternar(nombre, opcion, marcada) {
		const actuales = atributos?.[nombre] ?? [];
		atributos = {
			...atributos,
			[nombre]: marcada ? [...actuales, opcion] : actuales.filter((o) => o !== opcion)
		};
	}
</script>

<input type="hidden" name="categoria" value={categoriaId ?? ''} />
<input type="hidden" name="atributos" value={JSON.stringify(elegidos)} />

<Campo id="categoria" etiqueta="Categoría" requerido error={errores.categoria}>
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
		ayuda="Opcional. Con el tipo, los integrantes eligen talle, color, etc."
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
		<legend class="variantes__titulo">Variantes que ofrecés <span>(opcional)</span></legend>
		<p class="variantes__ayuda">
			Marcá las opciones que puede elegir cada integrante al unirse. Sin marcar nada, el pool no
			tiene variantes.
		</p>
		{#each atributosCategoria as atributo (atributo.nombre)}
			<div class="variantes__grupo" role="group" aria-label={atributo.nombre}>
				<p class="variantes__nombre">{atributo.nombre}</p>
				<div class="variantes__opciones">
					{#each atributo.opciones as opcion (opcion)}
						<label class="opcion" class:opcion--marcada={elegidos[atributo.nombre]?.includes(opcion)}>
							<input
								type="checkbox"
								checked={elegidos[atributo.nombre]?.includes(opcion) ?? false}
								onchange={(e) => alternar(atributo.nombre, opcion, e.currentTarget.checked)}
							/>
							{opcion}
						</label>
					{/each}
				</div>
			</div>
		{/each}
		{#if errores.atributos}
			<p class="variantes__error" role="alert">{errores.atributos}</p>
		{/if}
		{#if bloqueado}
			<p class="variantes__ayuda">Ya hay integrantes: la categoría y las variantes no se pueden cambiar.</p>
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
		padding: 0 var(--e-1);
		font-weight: 700;
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

	.variantes__grupo {
		display: grid;
		gap: var(--e-2);
	}

	.variantes__nombre {
		margin: 0;
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.variantes__opciones {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2);
	}

	.opcion {
		display: inline-flex;
		align-items: center;
		gap: var(--e-1);
		padding: 0.35rem 0.7rem;
		border: 1px solid var(--linea-control);
		border-radius: 999px;
		background: var(--superficie);
		font-size: var(--texto-sm);
		cursor: pointer;
	}

	.opcion input {
		margin: 0;
		accent-color: var(--marca);
	}

	.opcion--marcada {
		border-color: var(--marca-fuerte);
		background: var(--melocoton);
		color: var(--marca-fuerte);
		font-weight: 600;
	}

	.opcion:focus-within {
		outline: 2px solid var(--marca-fuerte);
		outline-offset: 2px;
	}

	.variantes__error {
		margin: 0;
		font-size: var(--texto-sm);
		color: var(--texto-peligro);
	}
</style>
