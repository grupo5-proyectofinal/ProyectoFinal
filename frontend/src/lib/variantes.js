/**
 * Variantes de un pool (Iteración 3: "Ropa > Remera > Talle, Color").
 *
 * Módulo puro (sin runes ni fetch) para testearlo con `node --test`.
 * - `/categories/` trae `{id, nombre, padre, atributos: [{nombre, opciones}]}`.
 * - El pool trae `variantes: [{nombre, opciones}]` (lo que ofrece el creador, en el
 *   orden de la categoría) y cada miembro `detalle: [{atributos, cantidad}]`.
 */

/** ¿Es la categoría comodín ("Otros", "Otras")? Va siempre al final de las listas. */
function esComodin(categoria) {
	return /^otr[oa]s?$/i.test((categoria?.nombre ?? '').trim());
}

/** Mismo orden que vienen, pero con "Otros" al final (el API ordena por nombre). */
export function conOtrosAlFinal(categorias) {
	const lista = categorias ?? [];
	return [...lista.filter((c) => !esComodin(c)), ...lista.filter(esComodin)];
}

/** Categorías principales (sin padre), en el orden que vienen y "Otros" al final. */
export function raices(categorias) {
	return conOtrosAlFinal((categorias ?? []).filter((c) => !c.padre));
}

/** Subcategorías de `padreId`, con "Otros" al final. */
export function hijas(categorias, padreId) {
	if (!padreId) return [];
	return conOtrosAlFinal((categorias ?? []).filter((c) => String(c.padre) === String(padreId)));
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

/** Clave estable de una combinación (mismo criterio que el backend). */
export function claveAtributos(atributos) {
	return JSON.stringify(
		Object.entries(atributos ?? {})
			.map(([nombre, valor]) => [String(nombre), String(valor)])
			.sort(([a], [b]) => a.localeCompare(b))
	);
}

/** Todas las combinaciones posibles de las variantes ofrecidas. */
export function combinaciones(variantes) {
	let resultado = [{}];
	for (const { nombre, opciones } of variantes ?? []) {
		resultado = resultado.flatMap((base) =>
			(opciones ?? []).map((opcion) => ({ ...base, [nombre]: opcion }))
		);
	}
	return resultado.map((atributos) => ({
		atributos,
		clave: claveAtributos(atributos),
		etiqueta: etiquetaVariante(atributos, variantes)
	}));
}

/** Mapa `clave -> cantidad` a partir del array `reparto` de la API. */
export function mapaDesdeReparto(reparto) {
	return Object.fromEntries(
		(reparto ?? []).map((fila) => [claveAtributos(fila.atributos), fila.cantidad])
	);
}

/** Array `reparto` para la API: solo combinaciones con cantidad > 0. */
export function repartoDesdeMapa(mapa, variantes) {
	return combinaciones(variantes)
		.map((combo) => ({
			atributos: { ...combo.atributos },
			cantidad: Number(mapa?.[combo.clave]) || 0
		}))
		.filter((fila) => fila.cantidad > 0);
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
