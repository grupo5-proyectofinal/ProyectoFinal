// Sección del menú a la que pertenece la pantalla actual cuando no se deduce de la ruta: el
// detalle de un pool cuelga de "Mis pools" (si lo organizo) o "Mis reservas" (si reservé).
// Lo fija la página del pool al cargarlo y lo limpia al salir.
export const seccion = $state({ desde: null });
