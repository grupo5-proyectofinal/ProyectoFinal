// Festejo cuando el pool pasa a "en curso" (el creador confirmó la compra).
// Se muestra una sola vez por pool y por usuario: lo ya festejado se recuerda en
// el navegador. Si el almacenamiento no está disponible, igual anda (sin recordar).

const CLAVE = 'poolshop:festejos';
const MAXIMO = 200;

export const COLORES_CONFETI = ['#f5423a', '#ff9248', '#ffc93c', '#1b6b45', '#de3535'];

/** ¿Hay que festejar? Pool en curso, el usuario participa y todavía no lo vio. */
export function debeFestejar(pool, usuarioId, vistos) {
	if (!pool || pool.estado !== 'en_curso' || usuarioId == null) return false;
	const participa =
		pool.creador?.id === usuarioId ||
		(pool.miembros ?? []).some((m) => m.usuario?.id === usuarioId);
	return participa && !vistos.includes(clave(pool.id, usuarioId));
}

export function clave(poolId, usuarioId) {
	return `${usuarioId}:${poolId}`;
}

export function leerVistos(almacen) {
	try {
		const datos = JSON.parse(almacen?.getItem(CLAVE) ?? '[]');
		return Array.isArray(datos) ? datos.filter((v) => typeof v === 'string') : [];
	} catch {
		return [];
	}
}

/** Agrega el pool a los festejados; conserva los últimos MAXIMO para no crecer sin límite. */
export function marcarVisto(almacen, poolId, usuarioId) {
	const nueva = clave(poolId, usuarioId);
	const vistos = leerVistos(almacen).filter((v) => v !== nueva);
	vistos.push(nueva);
	try {
		almacen?.setItem(CLAVE, JSON.stringify(vistos.slice(-MAXIMO)));
	} catch {
		// Modo privado o cuota llena: el festejo se podría repetir, nada más.
	}
	return vistos.slice(-MAXIMO);
}

/**
 * Piezas de confeti con posición, color, giro y tiempos al azar.
 * `azar` se inyecta para poder testear con una secuencia fija.
 */
export function piezasConfeti(cantidad, azar = Math.random) {
	return Array.from({ length: cantidad }, (_, i) => ({
		id: i,
		x: Math.round(azar() * 100),
		deriva: Math.round((azar() - 0.5) * 30),
		giro: Math.round(360 + azar() * 720) * (azar() < 0.5 ? -1 : 1),
		retraso: Math.round(azar() * 400),
		duracion: Math.round(1400 + azar() * 900),
		color: COLORES_CONFETI[i % COLORES_CONFETI.length],
		forma: i % 3 === 0 ? 'tira' : 'cuadro'
	}));
}

/** Porcentaje relleno de la línea de pasos (0 a 100) según el índice del paso actual. */
export function avanceLinea(indice, totalPasos) {
	if (totalPasos < 2 || indice < 0) return 0;
	return Math.min(100, Math.round((indice / (totalPasos - 1)) * 100));
}
