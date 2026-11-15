/**
 * Mejoras previstas (fuera de esta versión): directorio de mayoristas y comparador de
 * costo final. Siguen implementadas pero apagadas; se activan con
 * `VITE_MEJORAS_HABILITADAS=true` (y `MEJORAS_HABILITADAS=true` en el backend).
 *
 * Módulo puro: sin runes ni imports, se testea con `node --test`.
 */

export const MEJORAS_HABILITADAS = import.meta.env?.VITE_MEJORAS_HABILITADAS === 'true';

const RUTAS_DE_MEJORAS = [/^\/mayoristas(\/|$)/, /^\/comparar(\/|$)/, /^\/admin\/mayoristas(\/|$)/];

/** ¿Esta ruta es de una mejora prevista? */
export function esRutaDeMejoras(pathname) {
	return RUTAS_DE_MEJORAS.some((patron) => patron.test(pathname));
}

/** ¿Hay que sacar al usuario de esta ruta? Solo si es de una mejora apagada. */
export function debeRedirigirPorMejoras(pathname, habilitadas = MEJORAS_HABILITADAS) {
	return !habilitadas && esRutaDeMejoras(pathname);
}
