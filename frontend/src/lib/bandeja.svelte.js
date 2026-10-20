import { api } from './api.js';

// Contador de la campana del header. Lo refresca el polling del layout y las
// páginas que marcan avisos como leídos, para que el globito no quede viejo.
export const bandeja = $state({ noLeidas: 0 });

export async function refrescarBandeja() {
	try {
		const { no_leidas } = await api('/notificaciones/resumen/');
		bandeja.noLeidas = no_leidas;
	} catch {
		// Sin red o sin sesión: el contador queda como estaba; el 401 lo maneja la sesión.
	}
}
