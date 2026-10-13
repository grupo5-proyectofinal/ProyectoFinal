<script>
	// Primitiva Avatar: monograma (iniciales) o foto. Expone `nombre` como nombre
	// accesible; el caller puede silenciarlo con `aria-hidden` si el nombre ya está visible.
	import { iniciales } from '../formato.js';

	let { nombre = '', foto, tamano = 'md', class: clase = '', ...rest } = $props();

	const siglas = $derived(iniciales(nombre));
</script>

{#if foto}
	<span class="ui-avatar ui-avatar--{tamano} {clase}" role="img" aria-label={nombre || undefined} {...rest}>
		<img src={foto} alt="" />
	</span>
{:else}
	<span class="ui-avatar ui-avatar--{tamano} {clase}" role="img" aria-label={nombre || undefined} {...rest}>
		{siglas}
	</span>
{/if}

<style>
	.ui-avatar {
		display: grid;
		place-items: center;
		flex: none;
		width: 2.25rem;
		height: 2.25rem;
		overflow: hidden;
		border-radius: 50%;
		background: var(--melocoton-avatar);
		color: var(--naranja-oscuro);
		font-family: var(--fuente-display);
		font-size: var(--texto-sm);
		font-weight: 700;
	}

	.ui-avatar img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.ui-avatar--sm {
		width: 1.75rem;
		height: 1.75rem;
		font-size: var(--texto-xs);
	}

	.ui-avatar--lg {
		width: 4.5rem;
		height: 4.5rem;
		font-size: 1.6rem;
	}
</style>
