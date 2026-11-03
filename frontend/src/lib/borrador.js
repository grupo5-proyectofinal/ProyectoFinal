// Borradores de formularios en sessionStorage: si la sesión vence en medio de
// "Crear pool", el usuario inicia sesión de nuevo y encuentra sus datos.
// Módulo puro (storage inyectable) para testearlo con node --test.

const PREFIJO = 'poolshop.borrador.';

function almacen(storage) {
	if (storage) return storage;
	try {
		return typeof sessionStorage === 'undefined' ? null : sessionStorage;
	} catch {
		return null;
	}
}

/** Guarda los campos de texto del form (los archivos no se pueden guardar). */
export function guardarBorrador(clave, campos, storage) {
	const destino = almacen(storage);
	if (!destino) return;
	const limpio = {};
	for (const [nombre, valor] of Object.entries(campos ?? {})) {
		if (typeof valor === 'string') limpio[nombre] = valor;
	}
	const conDatos = Object.values(limpio).some((v) => v.trim() !== '');
	try {
		if (conDatos) destino.setItem(PREFIJO + clave, JSON.stringify(limpio));
		else destino.removeItem(PREFIJO + clave);
	} catch {
		// Storage lleno o bloqueado: el borrador es una ayuda, no un requisito.
	}
}

export function leerBorrador(clave, storage) {
	const origen = almacen(storage);
	if (!origen) return null;
	try {
		const valor = JSON.parse(origen.getItem(PREFIJO + clave));
		return valor && typeof valor === 'object' && !Array.isArray(valor) ? valor : null;
	} catch {
		return null;
	}
}

export function borrarBorrador(clave, storage) {
	try {
		almacen(storage)?.removeItem(PREFIJO + clave);
	} catch {
		// ignorado
	}
}

/** Borra todos los borradores (al cerrar sesión: no pasan al próximo usuario). */
export function borrarBorradores(storage) {
	const origen = almacen(storage);
	if (!origen) return;
	try {
		const claves = [];
		for (let i = 0; i < origen.length; i += 1) {
			const clave = origen.key(i);
			if (clave?.startsWith(PREFIJO)) claves.push(clave);
		}
		for (const clave of claves) origen.removeItem(clave);
	} catch {
		// ignorado
	}
}

/**
 * Vuelca un borrador en los controles de un form. Devuelve cuántos campos
 * restauró. Ignora archivos y campos que ya no existen.
 */
export function aplicarBorrador(elementos, borrador) {
	let restaurados = 0;
	for (const [nombre, valor] of Object.entries(borrador ?? {})) {
		const control = elementos?.namedItem ? elementos.namedItem(nombre) : elementos?.[nombre];
		if (!control || control.type === 'file' || typeof valor !== 'string') continue;
		if (control.type === 'checkbox') control.checked = valor === 'on';
		else control.value = valor;
		restaurados += 1;
	}
	return restaurados;
}
