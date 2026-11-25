// Explicación de cada campo de "Crear pool" / "Editar pool" que abre el ícono (?).
// El texto de ayuda corto queda debajo del campo; acá va el "para qué sirve" con
// un ejemplo. Son textos para usuarios finales: nada técnico ni de cómo está hecho.
export const AYUDAS = {
	enlace:
		'Es el link de la página del producto en la tienda online (por ejemplo, Mercado Libre). Con el link completamos el nombre, el precio y la foto, y después podés corregirlos. También sirve para que quienes se suman vean exactamente qué se va a comprar.',
	titulo:
		'Es lo primero que se ve en el listado y en el buscador. Conviene que diga qué es y algo que lo distinga, por ejemplo «Lavandina 5 L, caja de 4 bidones».',
	nombre_producto:
		'El nombre del producto con marca y modelo, como figura en la tienda. Así todos saben qué se compra, aunque el título sea más corto.',
	precio_unitario:
		'Lo que cuesta cada unidad comprando por mayor, sin contar el envío. Con este precio se calcula cuánto paga cada persona según las unidades que reserva.',
	precio_envio:
		'Lo que cobra la tienda por enviar toda la compra. Se reparte entre todos según las unidades que reserva cada uno: quien reserva más, paga una parte mayor. Si el envío es gratis o lo pagás vos, dejalo en 0.',
	categoria:
		'Sirve para que el pool aparezca cuando alguien busca o filtra por categoría en Explorar.',
	subcategoria:
		'Es opcional. Si elegís el tipo de producto, podés indicar la variante que se compra (talle, color, contenido…).',
	variante:
		'Todas las personas que se suman reciben la misma variante. Si necesitás otro talle o color, creá otro pool para esa variante.',
	cantidad_total:
		'Cuántas unidades hay que juntar entre todos para hacer la compra, por ejemplo la cantidad mínima que pide el mayorista. Cuando se reservan todas, el pool queda listo para comprar.',
	cantidad_creador:
		'Las unidades que te quedás vos. Cuentan dentro de la cantidad total: el resto es lo que reservan los demás.',
	min_por_integrante:
		'La menor cantidad que puede reservar cada persona que se suma. Sirve, por ejemplo, si el producto se vende de a pares o por caja.',
	precio_total:
		'Lo que cuesta toda la compra sin el envío: el precio por unidad multiplicado por la cantidad total. No hace falta completarlo.',
	direccion:
		'Dónde se retiran o se entregan los productos. La ven las personas que se suman y sirve para mostrarles el pool a quienes están cerca.',
	ciudad:
		'La ciudad o localidad de la dirección. Se completa sola al elegir una sugerencia y ayuda a que te encuentren quienes buscan por zona.',
	tipo_pago:
		'Cómo te pagan su parte las personas que se suman: en efectivo al momento de la entrega o por transferencia a tu cuenta.',
	alias_cbu:
		'Los datos de tu cuenta para que te transfieran. Solo los ven las personas que se suman al pool.',
	titular_cuenta:
		'El nombre de quien es dueño de la cuenta, para que quien transfiere confirme que los datos son correctos antes de pagar.',
	imagenes:
		'Fotos del producto o de la compra. La primera es la portada que se ve en el listado. Las fotos reales generan más confianza.',
	descripcion:
		'Todo lo que ayude a decidir: detalles del producto, cuándo pensás hacer la compra y cómo se entrega.'
};
