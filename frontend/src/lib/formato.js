const ENTERO = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });
const CON_CENTAVOS = new Intl.NumberFormat('es-AR', {
	minimumFractionDigits: 2,
	maximumFractionDigits: 2
});

/**
 * Precio en pesos: 1500 -> "$ 1.500", 3703.5 -> "$ 3.703,50" (los centavos van
 * siempre con dos dígitos, igual que en los mails). "—" si no es numérico.
 */
export function moneda(valor) {
	if (valor === null || valor === undefined || valor === '') return '—';
	const n = Number(valor);
	if (!Number.isFinite(n)) return '—';
	const centavos = Math.round(n * 100);
	return `$ ${centavos % 100 === 0 ? ENTERO.format(centavos / 100) : CON_CENTAVOS.format(n)}`;
}

const FECHA = new Intl.DateTimeFormat('es-AR', { day: 'numeric', month: 'short', year: 'numeric' });

/** Fecha ISO (YYYY-MM-DD) en formato local: "5 oct 2026". */
export function fecha(valor) {
	if (!valor) return '—';
	const d = new Date(`${valor}T00:00:00`);
	return Number.isNaN(d.getTime()) ? valor : FECHA.format(d);
}

/** "1 vista" / "N vistas". */
export function vistas(n) {
	const total = Number(n) || 0;
	return total === 1 ? '1 vista' : `${total} vistas`;
}

/** Días enteros hasta una fecha ISO (negativo si ya pasó). */
export function diasHasta(fechaISO) {
	const objetivo = new Date(`${fechaISO}T00:00:00`);
	const hoy = new Date();
	hoy.setHours(0, 0, 0, 0);
	return Math.round((objetivo - hoy) / 86400000);
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
