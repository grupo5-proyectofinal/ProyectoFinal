/**
 * Comparador de costo final y directorio de mayoristas (módulo puro, testeable).
 *
 * La API ya manda cada oferta con `costo` calculado y ordenada por total; acá
 * solo se decide cómo se muestra: textos, desglose y la línea de tendencia.
 */

import { moneda } from './formato.js';

/** Precio en la moneda de la oferta ("US$ 45,99" o "$ 1.500"). */
export function precioEnMoneda(valor, codigo) {
	const pesos = moneda(valor);
	if (!codigo || codigo === 'ARS' || pesos === '—') return pesos;
	return `${codigo} ${pesos.replace(/^\$ /, '')}`;
}

/** Filas del desglose de una oferta (solo lo que suma algo). */
export function desglose(costo) {
	if (!costo || costo.total === null || costo.total === undefined) return [];
	const filas = [
		{ rotulo: `Productos (${costo.unidades} u.)`, valor: costo.subtotal },
		{ rotulo: 'Envío', valor: costo.envio },
		{ rotulo: 'Impuestos', valor: costo.impuestos }
	];
	if (costo.aduana) {
		filas.push(
			{ rotulo: 'Derechos de importación', valor: costo.aduana.derechos, estimado: true },
			{ rotulo: 'Tasa estadística', valor: costo.aduana.tasa_estadistica, estimado: true },
			{ rotulo: 'IVA de importación', valor: costo.aduana.iva, estimado: true },
			{ rotulo: 'Percepciones', valor: costo.aduana.percepciones, estimado: true }
		);
	}
	return filas.filter((fila) => Number(fila.valor) > 0);
}

/** Por qué una oferta no tiene total (o null si lo tiene). */
export function faltante(costo) {
	if (costo?.falta === 'tipo_cambio') {
		return `Falta el tipo de cambio de ${costo.moneda}: pedíselo a un administrador.`;
	}
	return null;
}

/** "Comprás 12 por el mínimo de la tienda" cuando el mínimo obliga a llevar más. */
export function avisoMinimo(costo, cantidad) {
	if (!costo || costo.unidades <= Number(cantidad)) return null;
	return `El mínimo de la tienda es ${costo.unidades}: pagás ${costo.unidades} aunque necesites ${cantidad}.`;
}

/**
 * Puntos de una línea de tendencia (sparkline) en un viewBox `ancho × alto`.
 * Con un solo precio devuelve una línea plana; sin datos, [].
 */
export function puntosTendencia(historial, ancho = 80, alto = 24, margen = 4) {
	const precios = (historial ?? []).map((p) => Number(p.precio)).filter(Number.isFinite);
	if (!precios.length) return [];
	const min = Math.min(...precios);
	const max = Math.max(...precios);
	const rango = max - min || 1;
	const paso = precios.length > 1 ? (ancho - margen * 2) / (precios.length - 1) : 0;
	return precios.map((precio, i) => ({
		x: Math.round((margen + paso * i) * 10) / 10,
		y:
			max === min
				? alto / 2
				: Math.round((alto - margen - ((precio - min) / rango) * (alto - margen * 2)) * 10) / 10,
		precio,
		fecha: historial[i].fecha
	}));
}

/** "Bajó 5 %", "Subió 2 %", "Sin cambios" entre el primer y el último precio. */
export function variacion(historial) {
	const precios = (historial ?? []).map((p) => Number(p.precio));
	if (precios.length < 2 || !precios[0]) return 'Sin cambios';
	const cambio = ((precios.at(-1) - precios[0]) / precios[0]) * 100;
	if (Math.abs(cambio) < 0.5) return 'Sin cambios';
	return `${cambio < 0 ? 'Bajó' : 'Subió'} ${Math.round(Math.abs(cambio))} %`;
}

/** Link a "Crear pool" con la oferta elegida precargada. */
export function enlaceCrearPool(oferta, comparacion) {
	const params = new URLSearchParams();
	if (oferta.url) params.set('enlace', oferta.url);
	if (comparacion?.producto || comparacion?.titulo) {
		params.set('producto', comparacion.producto || comparacion.titulo);
	}
	if (oferta.moneda === 'ARS') params.set('precio', String(oferta.precio_unitario));
	if (comparacion?.cantidad) params.set('cantidad', String(comparacion.cantidad));
	return `/pools/nuevo?${params}`;
}

export const ESTADOS_PROVEEDOR = {
	pendiente: { texto: 'Pendiente', variante: 'en_curso' },
	aprobado: { texto: 'Aprobado', variante: 'abierto' },
	rechazado: { texto: 'Rechazado', variante: 'cancelado' }
};
