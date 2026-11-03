/**
 * Bandeja de notificaciones (Iteración 2).
 *
 * Módulo puro (sin runes ni fetch) para testearlo con `node --test`: textos,
 * fechas relativas y preferencias. El servidor ya manda `titulo` y `texto`
 * armados en es-AR; acá solo se decide cómo se presentan.
 */

import { etiquetaEstado } from './estados.js';

/** Preferencias editables desde `/notificaciones` (campos de `/auth/me/`). */
export const PREFERENCIAS = [
	{
		clave: 'notificar_estados',
		texto: 'Cambios de estado de mis pools',
		ayuda: 'Listo para comprar, en curso, finalizado o cancelado'
	},
	{
		clave: 'notificar_mensajes',
		texto: 'Comentarios nuevos en el chat',
		ayuda: 'Cuando alguien escribe en un pool en el que participás'
	},
	{
		clave: 'notificar_miembros',
		texto: 'Se une un miembro',
		ayuda: 'Solo en los pools que organizás'
	}
];

export const PREFERENCIA_EMAIL = {
	clave: 'notificar_por_email',
	texto: 'Por email',
	ayuda: 'Además del aviso en la app, te llega un mail'
};

const TIPOS = { mensaje: 'Mensaje nuevo', union: 'Nuevo miembro' };

/** Texto del badge de la notificación: el estado nuevo o el tipo de aviso. */
export function etiquetaTipo(notificacion) {
	if (notificacion?.tipo === 'estado' && notificacion.datos?.estado) {
		return etiquetaEstado(notificacion.datos.estado);
	}
	return TIPOS[notificacion?.tipo] ?? 'Aviso';
}

const MINUTO = 60 * 1000;
const HORA = 60 * MINUTO;

/** "Recién", "Hace 5 min", "Hace 2 h", "Ayer" o la fecha "dd/mm/aaaa". */
export function tiempoRelativo(iso, ahora = new Date()) {
	const fecha = new Date(iso);
	if (Number.isNaN(fecha.getTime())) return '';
	const diferencia = ahora - fecha;
	if (diferencia < MINUTO) return 'Recién';
	if (diferencia < HORA) return `Hace ${Math.floor(diferencia / MINUTO)} min`;
	const inicioHoy = new Date(ahora);
	inicioHoy.setHours(0, 0, 0, 0);
	if (fecha >= inicioHoy) return `Hace ${Math.floor(diferencia / HORA)} h`;
	const inicioAyer = new Date(inicioHoy);
	inicioAyer.setDate(inicioAyer.getDate() - 1);
	if (fecha >= inicioAyer) return 'Ayer';
	const dd = String(fecha.getDate()).padStart(2, '0');
	const mm = String(fecha.getMonth() + 1).padStart(2, '0');
	return `${dd}/${mm}/${fecha.getFullYear()}`;
}

/** Subtítulo de la bandeja según cuántas quedan sin leer. */
export function textoNoLeidas(n) {
	if (!n) return 'No tenés notificaciones sin leer.';
	return n === 1 ? 'Tenés 1 notificación sin leer.' : `Tenés ${n} notificaciones sin leer.`;
}

/** Número del globito de la campana: nada en 0, tope "9+". */
export function contadorCampana(n) {
	const total = Number(n) || 0;
	if (total <= 0) return '';
	return total > 9 ? '9+' : String(total);
}

/** Nombre accesible de la campana, con la cantidad sin leer. */
export function etiquetaCampana(n) {
	const total = Number(n) || 0;
	if (!total) return 'Notificaciones';
	return `Notificaciones (${total} sin leer)`;
}
