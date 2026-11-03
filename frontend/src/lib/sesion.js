// Lógica pura de la sesión (sin runes): se testea con node --test.

/** Renovar el access cuando le falta menos que esto para vencer. */
export const MARGEN_RENOVACION_MS = 2 * 60 * 1000;

/** Instante (ms epoch) en que vence un JWT, o null si no se puede leer. */
export function expiraEn(token) {
	if (typeof token !== 'string') return null;
	const partes = token.split('.');
	if (partes.length !== 3) return null;
	try {
		const base64 = partes[1].replace(/-/g, '+').replace(/_/g, '/');
		const payload = JSON.parse(atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, '=')));
		return typeof payload.exp === 'number' ? payload.exp * 1000 : null;
	} catch {
		return null;
	}
}

/** true si el access ya venció o está por vencer (y conviene renovarlo antes de usarlo). */
export function necesitaRenovar(token, ahora = Date.now(), margen = MARGEN_RENOVACION_MS) {
	const vence = expiraEn(token);
	return vence !== null && vence - ahora < margen;
}

/**
 * Devuelve una versión de `fn` que comparte la promesa en curso: si diez pedidos
 * reciben 401 a la vez, se hace un solo refresh y todos esperan ese resultado.
 */
export function unaVez(fn) {
	let enCurso = null;
	return () => {
		if (!enCurso) {
			enCurso = Promise.resolve()
				.then(fn)
				.finally(() => {
					enCurso = null;
				});
		}
		return enCurso;
	};
}

/**
 * Destino seguro después del login: solo rutas internas (evita open redirect con
 * `//otro.sitio` o `https://...`) y nunca de vuelta a /login.
 */
export function rutaSegura(next) {
	if (typeof next !== 'string' || !next.startsWith('/') || next.startsWith('//')) return '/';
	// Barras invertidas y caracteres de control (tab, salto de línea): el parser de URL
	// los descarta y `/\t/otro.sitio` terminaría siendo `//otro.sitio`.
	if (next.includes('\\') || /[\u0000-\u001f\u007f]/.test(next)) return '/';
	if (next === '/login' || next.startsWith('/login?') || next.startsWith('/login/')) return '/';
	return next;
}

/** URL de login que vuelve a la página actual después de iniciar sesión. */
export function urlLogin(pathname, search = '') {
	const destino = rutaSegura(`${pathname}${search}`);
	return destino === '/' ? '/login' : `/login?next=${encodeURIComponent(destino)}`;
}

export const MENSAJE_SESION_EXPIRADA = 'Tu sesión expiró. Iniciá sesión de nuevo para continuar.';
