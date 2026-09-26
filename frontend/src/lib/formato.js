const NUMERO = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 2 });

/** Precio en pesos: 1500 -> "$ 1.500". Devuelve "—" si no es numérico. */
export function moneda(valor) {
	if (valor === null || valor === undefined || valor === '') return '—';
	const n = Number(valor);
	return Number.isFinite(n) ? `$ ${NUMERO.format(n)}` : '—';
}

const FECHA = new Intl.DateTimeFormat('es-AR', { day: 'numeric', month: 'short', year: 'numeric' });

/** Fecha ISO (YYYY-MM-DD) en formato local: "5 oct 2026". */
export function fecha(valor) {
	if (!valor) return '—';
	const d = new Date(`${valor}T00:00:00`);
	return Number.isNaN(d.getTime()) ? valor : FECHA.format(d);
}

/** Iniciales para monogramas: "ana perez" -> "AP". */
export function iniciales(texto) {
	return (
		(texto ?? '')
			.trim()
			.split(/\s+/)
			.slice(0, 2)
			.map((parte) => parte[0]?.toUpperCase() ?? '')
			.join('') || '?'
	);
}
