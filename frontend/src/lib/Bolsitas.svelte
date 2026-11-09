<script>
	// Las bolsitas del logo para pantallas vacías.
	// - 'durmiendo': nada pendiente ("Estás al día", todavía no hay nada). Respiran y salen "z".
	// - 'buscando': una búsqueda sin resultados. Miran de un lado al otro.
	// Es decorativo: el texto de la pantalla vacía ya dice lo que pasa.
	let { variante = 'durmiendo' } = $props();
</script>

<span class="bolsitas bolsitas--{variante}" aria-hidden="true">
	<svg viewBox="-4 -14 71 55">
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
		</g>

		{#if variante === 'durmiendo'}
			<g fill="none" stroke="#4a0e0e" stroke-width="1.2" stroke-linecap="round">
				<path d="M21 18q2 1.6 4 0" />
				<path d="M36.5 18q2 1.6 4 0" />
				<path d="M26 27q4.5 3 9 0" />
			</g>
			<g class="zetas" fill="#c2410c" font-weight="800">
				<text class="zeta" x="50" y="0" font-size="7">z</text>
				<text class="zeta zeta--2" x="55" y="-6" font-size="5.5">z</text>
				<text class="zeta zeta--3" x="59" y="-11" font-size="4.5">z</text>
			</g>
		{:else}
			<g class="ojos" fill="#4a0e0e">
				<ellipse cx="23" cy="17.5" rx="1.6" ry="2.6" />
				<ellipse cx="38.5" cy="17.5" rx="1.6" ry="2.6" />
			</g>
			<path
				d="M24 28q6.5 -2 13 0"
				fill="none"
				stroke="#4a0e0e"
				stroke-width="1.2"
				stroke-linecap="round"
			/>
		{/if}
	</svg>
</span>

<style>
	.bolsitas {
		display: block;
		width: 6.5rem;
		height: 5rem;
	}

	.bolsitas svg {
		width: 100%;
		height: 100%;
		overflow: visible;
	}

	.bolsa {
		transform-box: fill-box;
		transform-origin: 50% 100%;
	}

	/* Durmiendo: respiran despacio y las "z" suben y se desvanecen. */
	.bolsitas--durmiendo .bolsa {
		animation: respirar 3.6s ease-in-out infinite;
	}

	.bolsitas--durmiendo .bolsa--der {
		animation-delay: -1.8s;
	}

	.zetas {
		font-family: var(--fuente-display);
	}

	.zeta {
		opacity: 0;
		animation: zeta 3.6s ease-out infinite;
	}

	.zeta--2 {
		animation-delay: 0.6s;
	}

	.zeta--3 {
		animation-delay: 1.2s;
	}

	@keyframes respirar {
		0%,
		100% {
			transform: scale(1, 1);
		}
		50% {
			transform: scale(1.03, 0.96);
		}
	}

	@keyframes zeta {
		0% {
			opacity: 0;
			transform: translate(0, 3px);
		}
		25%,
		60% {
			opacity: 1;
		}
		100% {
			opacity: 0;
			transform: translate(3px, -4px);
		}
	}

	/* Buscando: los ojos van de un lado al otro y las bolsitas se inclinan detrás. */
	.ojos {
		animation: mirar 3.2s ease-in-out infinite;
	}

	.bolsitas--buscando .bolsa {
		animation: inclinar 3.2s ease-in-out infinite;
	}

	@keyframes mirar {
		0%,
		15%,
		100% {
			transform: translateX(0);
		}
		30%,
		45% {
			transform: translateX(-2.5px);
		}
		60%,
		80% {
			transform: translateX(2.5px);
		}
	}

	@keyframes inclinar {
		0%,
		15%,
		100% {
			transform: rotate(0);
		}
		30%,
		45% {
			transform: rotate(-3deg);
		}
		60%,
		80% {
			transform: rotate(3deg);
		}
	}

	/* Con "reducir movimiento" quedan quietas, con las "z" visibles. */
	@media (prefers-reduced-motion: reduce) {
		.zeta {
			opacity: 1;
		}
	}
</style>
