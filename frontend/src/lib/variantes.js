/**
 * Variantes de un pool (Iteración 3: "Ropa > Remera > Talle, Color").
 *
 * Módulo puro (sin runes ni fetch) para testearlo con `node --test`.
 * - `/categories/` trae `{id, nombre, padre, atributos: [{nombre, opciones}]}`.
 * - El pool trae `variantes: [{nombre, opciones}]` (lo que ofrece el creador, en el
 *   orden de la categoría) y cada miembro `detalle: [{atributos, cantidad}]`.
 */

/** Categorías principales (sin padre), en el orden que vienen. */
export function raices(categorias) {
	return (categorias ?? []).filter((c) => !c.padre);
}

/** Subcategorías de `padreId`. */
export function hijas(categorias, padreId) {
	if (!padreId) return [];
	return (categorias ?? []).filter((c) => String(c.padre) === String(padreId));
}

/** Para precargar los selects: `{raiz, sub}` a partir de la categoría del pool. */
export function separarCategoria(categorias, categoriaId) {
	const categoria = (categorias ?? []).find((c) => String(c.id) === String(categoriaId));
	if (!categoria) return { raiz: '', sub: '' };
	return categoria.padre
		? { raiz: String(categoria.padre), sub: String(categoria.id) }
		: { raiz: String(categoria.id), sub: '' };
}

/** Atributos (con todas sus opciones) de la categoría elegida. */
export function atributosDe(categorias, categoriaId) {
	return (categorias ?? []).find((c) => String(c.id) === String(categoriaId))?.atributos ?? [];
}

/**
 * Lo que se manda como `atributos` del pool: solo las opciones elegidas que siguen
 * existiendo en la categoría, sin atributos vacíos.
 */
export function atributosElegidos(atributosCategoria, elegidos) {
	const resultado = {};
	for (const { nombre, opciones } of atributosCategoria ?? []) {
		const marcadas = opciones.filter((o) => elegidos?.[nombre]?.includes(o));
		if (marcadas.length) resultado[nombre] = marcadas;
	}
	return resultado;
}

/** Fila nueva con la primera opción de cada variante. */
export function filaVacia(variantes, cantidad = 1) {
	const atributos = {};
	for (const { nombre, opciones } of variantes ?? []) atributos[nombre] = opciones[0] ?? '';
	return { atributos, cantidad };
}

/** Filas para editar: las del miembro o una vacía con el mínimo del pool. */
export function filasIniciales(variantes, detalle, minimo = 1) {
	if (!variantes?.length) return [];
	if (detalle?.length) {
		return detalle.map((fila) => ({ atributos: { ...fila.atributos }, cantidad: fila.cantidad }));
	}
	return [filaVacia(variantes, minimo)];
}

export function sumaFilas(filas) {
	return (filas ?? []).reduce((total, fila) => total + (Number(fila.cantidad) || 0), 0);
}

/** Payload `detalle` para la API (cantidades numéricas, sin filas en 0). */
export function detalleDesdeFilas(filas) {
	return (filas ?? [])
		.map((fila) => ({ atributos: { ...fila.atributos }, cantidad: Number(fila.cantidad) || 0 }))
		.filter((fila) => fila.cantidad > 0);
}

/** "M · Negro" en el orden de las variantes del pool. */
export function etiquetaVariante(atributos, variantes) {
	const orden = (variantes ?? []).map((v) => v.nombre);
	const claves = orden.length ? orden : Object.keys(atributos ?? {});
	return claves
		.map((nombre) => atributos?.[nombre])
		.filter(Boolean)
		.join(' · ');
}

/**
 * Resumen para el pedido al proveedor: suma por variante de todos los miembros,
 * de más a menos. `[{atributos, etiqueta, cantidad}]`.
 */
export function resumenVariantes(miembros, variantes) {
	const totales = new Map();
	for (const miembro of miembros ?? []) {
		for (const fila of miembro.detalle ?? []) {
			const etiqueta = etiquetaVariante(fila.atributos, variantes);
			const previo = totales.get(etiqueta) ?? { atributos: fila.atributos, etiqueta, cantidad: 0 };
			previo.cantidad += Number(fila.cantidad) || 0;
			totales.set(etiqueta, previo);
		}
	}
	return [...totales.values()].sort(
		(a, b) => b.cantidad - a.cantidad || a.etiqueta.localeCompare(b.etiqueta, 'es')
	);
}

function celdaCsv(valor) {
	const texto = String(valor ?? '');
	return /[",;\n]/.test(texto) ? `"${texto.replace(/"/g, '""')}"` : texto;
}

/** CSV del resumen (una columna por variante + Cantidad), listo para Excel. */
export function csvVariantes(resumen, variantes) {
	const columnas = (variantes ?? []).map((v) => v.nombre);
	const filas = [
		[...columnas, 'Cantidad'],
		...(resumen ?? []).map((fila) => [
			...columnas.map((nombre) => fila.atributos?.[nombre] ?? ''),
			fila.cantidad
		])
	];
	return filas.map((fila) => fila.map(celdaCsv).join(',')).join('\n');
}
