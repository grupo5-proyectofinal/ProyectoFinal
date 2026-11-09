<script>
	// Marca: las dos bolsitas sonrientes de docs/LogoPS.png redibujadas en SVG para
	// animarlas por partes (se balancean, parpadean). Wordmark "Pool" (tinta) + "Shop"
	// (naranja). El contexto solo cambia el tamaño.
	let { conNombre = true, class: clase = '', ...rest } = $props();
</script>

<span class="marca {clase}" {...rest}>
	<span
		class="marca__isotipo"
		role={conNombre ? undefined : 'img'}
		aria-hidden={conNombre ? 'true' : undefined}
		aria-label={conNombre ? undefined : 'PoolShop'}
	>
		<svg viewBox="0 0 63 41" aria-hidden="true">
			<g class="bolsa bolsa--izq">
				<path
					d="M10 10.5V6.5a4.5 4.5 0 0 1 4.5-4.5h3a4.5 4.5 0 0 1 4.5 4.5v4"
					fill="none"
					stroke="#f5423a"
					stroke-width="2.2"
				/>
				<path
					d="M5 10.5h22l3 27.5H1z"
					fill="#f5423a"
					stroke="#f5423a"
					stroke-width="2"
					stroke-linejoin="round"
				/>
				<ellipse class="ojo" cx="23" cy="17.5" rx="1.6" ry="2.6" fill="#4a0e0e" />
			</g>
			<g class="bolsa bolsa--der">
				<path
					d="M41 10.5V6.5a4.5 4.5 0 0 1 4.5-4.5h2a4.5 4.5 0 0 1 4.5 4.5v4"
					fill="none"
					stroke="#ff9248"
					stroke-width="2.2"
				/>
				<path
					d="M35 10.5h22l4.5 27.5H32.5z"
					fill="#ff9248"
					stroke="#ff9248"
					stroke-width="2"
					stroke-linejoin="round"
				/>
				<ellipse class="ojo" cx="38.5" cy="17.5" rx="1.6" ry="2.6" fill="#4a0e0e" />
			</g>
			<path
				class="sonrisa"
				d="M15 24Q30.5 50 46 24"
				fill="none"
				stroke="#4a0e0e"
				stroke-width="1"
				stroke-linecap="round"
			/>
		</svg>
	</span>
	{#if conNombre}<span class="marca__nombre">Pool<span class="marca__shop">Shop</span></span>{/if}
</span>

<style>
	.marca {
		display: inline-flex;
		align-items: center;
		gap: 0.4em;
		font-family: var(--fuente-display);
		font-weight: 800;
		font-size: 1.5rem;
		letter-spacing: -0.02em;
		line-height: 1;
		color: var(--tinta);
	}

	.marca__isotipo {
		flex: none;
		display: flex;
		width: 1.85em;
		height: 1.2em;
	}

	.marca__isotipo svg {
		width: 100%;
		height: 100%;
		overflow: visible;
	}

	/* Animación: las bolsitas se balancean a destiempo, como charlando,
	   y parpadean de vez en cuando. La regla global de reduced-motion la apaga. */
	.bolsa {
		transform-box: fill-box;
		transform-origin: 50% 100%;
		animation: balanceo 3.2s ease-in-out infinite;
	}

	.bolsa--der {
		animation-delay: -1.6s;
	}

	.ojo {
		transform-box: fill-box;
		transform-origin: center;
		animation: parpadeo 4.5s ease-in-out infinite;
	}

	.bolsa--der .ojo {
		animation-delay: 0.12s;
	}

	.sonrisa {
		transform-box: fill-box;
		transform-origin: 50% 0;
		animation: sonrisa 3.2s ease-in-out infinite;
	}

	/* Al pasar el mouse por el link de la marca, dan un saltito. */
	:global(a:hover) > .marca .bolsa,
	:global(a:focus-visible) > .marca .bolsa {
		animation: saltito 0.55s ease-out;
	}

	:global(a:hover) > .marca .bolsa--der,
	:global(a:focus-visible) > .marca .bolsa--der {
		animation-delay: 0.08s;
	}

	@keyframes balanceo {
		0%,
		100% {
			transform: rotate(-4deg);
		}
		50% {
			transform: rotate(4deg) translateY(-1px);
		}
	}

	@keyframes parpadeo {
		0%,
		92%,
		100% {
			transform: scaleY(1);
		}
		95% {
			transform: scaleY(0.1);
		}
	}

	@keyframes sonrisa {
		0%,
		100% {
			transform: scaleY(1);
		}
		50% {
			transform: scaleY(1.12);
		}
	}

	@keyframes saltito {
		0%,
		100% {
			transform: translateY(0);
		}
		40% {
			transform: translateY(-18%) rotate(-6deg);
		}
		70% {
			transform: translateY(2%) rotate(3deg);
		}
	}

	.marca__shop {
		color: var(--acento-naranja);
	}

	/* Variantes por contexto (el consumidor pasa la clase). */
	.marca--cabecera {
		font-size: 1.5rem;
	}

	.marca--pie {
		font-size: 1.2rem;
	}

	.auth__logo {
		margin-bottom: var(--e-5);
		font-size: 2.75rem;
	}
</style>
