<script>
	import { resolve } from '$app/paths';
</script>

<svelte:head>
	<title>Ayuda — PoolShop</title>
	<meta
		name="description"
		content="Cómo crear un pool, unirte, pagar, comparar costos y resolver los problemas más comunes."
	/>
</svelte:head>

<div class="ayuda">
	<header class="ayuda__cabecera">
		<h1>Ayuda</h1>
		<p>
			Todo lo necesario para armar una compra colectiva, sumarte a una y coordinar el pago y la
			entrega.
		</p>
	</header>

	<nav class="ayuda__toc" aria-label="Contenido de la ayuda">
		<a href="#que-es">Qué es un pool</a>
		<a href="#crear">Crear un pool</a>
		<a href="#unirse">Unirse y pagar</a>
		<a href="#comparador">Comparar costos</a>
		<a href="#cancelar">Cancelar o eliminar</a>
		<a href="#problemas">Problemas frecuentes</a>
	</nav>

	<section id="que-es" aria-labelledby="que-es-titulo">
		<h2 id="que-es-titulo">Qué es un pool</h2>
		<p>
			Un pool es una compra en grupo. Varias personas juntan la cantidad mínima que pide un
			mayorista, cada una reserva solo lo que necesita y el organizador hace una sola compra.
		</p>
		<ul>
			<li>El pool tiene una cantidad total y un mínimo por persona.</li>
			<li>Se puede sumar gente hasta la fecha de caducidad o hasta completar el cupo.</li>
			<li>Cuando se alcanza el mínimo, el pool pasa a <strong>Mínimo alcanzado</strong>: es el momento de pagar.</li>
			<li>Después se confirma el pedido, se recibe y cada persona confirma su entrega.</li>
		</ul>
	</section>

	<section id="crear" aria-labelledby="crear-titulo">
		<h2 id="crear-titulo">Crear un pool</h2>
		<ol>
			<li>
				<strong>Producto:</strong> si tenés el enlace de la tienda, pegalo y completamos nombre,
				precio e imagen. Revisá lo que se cargó antes de seguir.
			</li>
			<li>
				<strong>Cantidades y plazo:</strong> definí cuántas unidades necesita el pool, cuántas
				reservás vos, el mínimo por persona y la fecha límite.
			</li>
			<li>
				<strong>Entrega y pago:</strong> cargá la dirección, la ciudad y, si cobrás por
				transferencia, el alias o CBU y el titular.
			</li>
			<li>
				<strong>Fotos y descripción:</strong> una portada clara y los detalles que ayuden a
				decidir (marca, medidas, punto de entrega).
			</li>
		</ol>
		<p>
			Una vez que hay otros integrantes, el título, el producto, el precio, la cantidad total y el
			domicilio ya no se pueden cambiar. La descripción, la caducidad y el mínimo sí.
		</p>
		<p><a href={resolve('/pools/nuevo')}>Crear un pool</a></p>
	</section>

	<section id="unirse" aria-labelledby="unirse-titulo">
		<h2 id="unirse-titulo">Unirse y pagar</h2>
		<p>
			Elegí la cantidad (y las variantes, si el pool las ofrece), dejá tu teléfono y confirmá. La
			reserva queda registrada con el total a pagar.
		</p>
		<ul>
			<li>Si el pago es por transferencia, el organizador carga el alias o CBU en el pool.</li>
			<li>Subí el comprobante desde <strong>Pagos y entrega</strong>; el organizador lo confirma o lo rechaza.</li>
			<li>Cuando recibas el producto, confirmá la recepción para que el pool pueda finalizar.</li>
			<li>Podés salir del pool mientras esté abierto o con el mínimo alcanzado; se libera tu reserva.</li>
		</ul>
	</section>

	<section id="comparador" aria-labelledby="comparador-titulo">
		<h2 id="comparador-titulo">Comparar costos</h2>
		<p>
			El comparador no ordena por precio publicado: suma envío, impuestos y, si importás, una
			estimación de aduana. El resultado es el <strong>costo total</strong> para la cantidad que
			necesitás y el costo por unidad.
		</p>
		<p>
			Los valores de aduana, impuestos y tipo de cambio son estimaciones de referencia que carga
			el equipo. El monto real depende del producto y del régimen de importación.
		</p>
		<p><a href={resolve('/comparar')}>Abrir el comparador</a></p>
	</section>

	<section id="cancelar" aria-labelledby="cancelar-titulo">
		<h2 id="cancelar-titulo">Cancelar o eliminar</h2>
		<ul>
			<li>
				<strong>Cancelar el pool:</strong> lo puede hacer el organizador mientras esté abierto o
				con el mínimo alcanzado. Se liberan todas las reservas y el pool deja de aceptar uniones.
			</li>
			<li>
				<strong>Eliminar el pool:</strong> borra la publicación. Si ya hay integrantes, la
				eliminación se vota entre todos.
			</li>
			<li>
				<strong>Salir:</strong> cada integrante puede liberar su reserva mientras el pool no esté
				en curso.
			</li>
		</ul>
	</section>

	<section id="problemas" aria-labelledby="problemas-titulo">
		<h2 id="problemas-titulo">Problemas frecuentes</h2>
		<h3>No puedo ingresar porque mi email no está confirmado</h3>
		<p>
			Abrí el enlace del mail de verificación. Si venció, pedí uno nuevo desde el aviso de ingreso
			o desde <a href={resolve('/verificar-email')}>confirmar email</a>.
		</p>
		<h3>El enlace de recuperación no funciona</h3>
		<p>
			Los enlaces se usan una sola vez y vencen. Pedí uno nuevo desde
			<a href={resolve('/recuperar')}>recuperar contraseña</a>.
		</p>
		<h3>Quiero dejar de recibir correos</h3>
		<p>
			Usá el enlace del pie de cualquier correo o entrá a
			<a href={resolve('/notificaciones')}>Notificaciones</a> y desactivá “Por email”. Los correos
			de acceso (verificación y contraseña) siguen llegando.
		</p>
		<h3>La foto de perfil no se ve</h3>
		<p>
			Aceptamos JPG, PNG, HEIC y WEBP. Las fotos HEIC se convierten al guardar; si la vista previa
			no aparece, la imagen igual se sube.
		</p>
		<h3>El precio del comparador no coincide con la tienda</h3>
		<p>
			El comparador usa el último precio leído del enlace. Podés actualizarlo desde la comparación
			con “Actualizar precios”. Las estimaciones de envío, impuestos y aduana no son cotizaciones.
		</p>
	</section>

	<footer class="ayuda__pie">
		<p>
			PoolShop es un proyecto académico. No hay soporte comercial ni SLA; si algo falla, probá
			recargar la página y volver a intentar.
		</p>
	</footer>
</div>

<style>
	.ayuda {
		max-width: 72ch;
		margin-inline: auto;
	}

	.ayuda__cabecera {
		margin-bottom: var(--e-6);
	}

	.ayuda__cabecera p {
		margin-top: var(--e-3);
		color: var(--tinta-suave);
		font-size: var(--texto-md);
		max-width: 62ch;
	}

	.ayuda__toc {
		display: flex;
		flex-wrap: wrap;
		gap: var(--e-2) var(--e-4);
		margin-bottom: var(--e-7);
		padding: var(--e-3) 0;
		border-top: 1px solid var(--linea);
		border-bottom: 1px solid var(--linea);
	}

	.ayuda__toc a {
		font-size: var(--texto-sm);
		font-weight: 600;
	}

	.ayuda section {
		margin-bottom: var(--e-6);
		scroll-margin-top: calc(var(--alto-cabecera) + var(--e-4));
	}

	.ayuda h2 {
		margin-bottom: var(--e-3);
		font-size: var(--texto-xl);
	}

	.ayuda h3 {
		margin-top: var(--e-4);
		font-size: var(--texto-md);
	}

	.ayuda p,
	.ayuda li {
		color: var(--tinta-suave);
	}

	.ayuda ul,
	.ayuda ol {
		margin: 0 0 var(--e-4);
		padding-left: 1.25rem;
	}

	.ayuda li + li {
		margin-top: var(--e-2);
	}

	.ayuda__pie {
		margin-top: var(--e-7);
		padding-top: var(--e-4);
		border-top: 1px solid var(--linea);
		font-size: var(--texto-sm);
	}
</style>
