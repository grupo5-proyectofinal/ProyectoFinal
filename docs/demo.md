# Demo de PoolShop

Datos cargados en **https://poolshop-ozy0.onrender.com** para recorrer la app completa:
20 usuarios, una cuenta de administración y 46 pools en todos los estados, con
pagos, chat, bajas, devoluciones, reseñas y notificaciones. Los carga el comando
`poblar_demo` (ver [Cómo se carga](#cómo-se-carga)).

> El plan free de Render apaga el servicio tras 15 minutos sin uso: el primer
> ingreso puede tardar ~1 minuto en responder. Conviene abrir la página un rato antes.

## Cuentas

Todas tienen la contraseña **`PoolShop.Demo2026`**. Se ingresa con el usuario o con el
email (`<usuario>@poolshop.demo`, direcciones ficticias: estas cuentas no reciben mails).

| Usuario | Ciudad | Para mostrar |
|---|---|---|
| `admin.demo` | Corrientes | Panel de administración: usuarios, categorías y atributos |
| `lucia.fernandez` | Corrientes | Organizadora con más pools: pagos por revisar, en curso, finalizado con reseñas |
| `martin.gomez` | Corrientes | Organizador; se unió a muchos pools; baja rechazada en *Power bank* |
| `sofia.benitez` | Resistencia | Pedido de baja **pendiente** en *Toallas* (aprobar o rechazar en vivo) |
| `diego.romero` | Resistencia | Perfil con reseñas regulares (2 y 3 ★); devolución por confirmar en *Smartwatches* |
| `valentina.acosta` | Corrientes | Pidió la baja en *Toallas*; organiza *Shampoo* (volvió a abierto tras una baja) |
| `nicolas.ojeda` | Corrientes | Pago **rechazado** en *Detergente*; organiza *Guantes* (en reconfirmación) |
| `camila.ramirez` | Posadas | *Fernet*: todos los pagos confirmados, listo para **confirmar el pedido** |
| `joaquin.sosa` | Posadas | *Vasos*: **caducado**, para extender el plazo o cancelar en vivo |
| `florencia.medina` | Resistencia | *Pasta dental* en curso: falta una recepción para poder finalizar |
| `agustin.vera` | Corrientes | Pidió la baja en un pool en curso y se la rechazaron |
| `micaela.duarte` | Córdoba | Buzos de egresados (variantes de talle) |
| `tomas.aguirre` | Córdoba | *Remeras lisas* con talles y colores; en *Remeras dry-fit* tiene que revisar un comprobante reenviado |
| `julieta.cabrera` | Rosario | Dejó una reseña de 3 ★; notificaciones de chat desactivadas |
| `matias.pereyra` | Rosario | *Auriculares*: caducado |
| `carla.ledesma` | Buenos Aires | *Útiles escolares* en reconfirmación |
| `franco.molina` | Buenos Aires | *Fundas* con variante de color |
| `rocio.gimenez` | Corrientes | Pago pendiente en *Detergente*; *Almohadas*, cancelado por falta de respuesta |
| `santiago.rios` | Resistencia | *Smartwatches*: cancelado con devoluciones a medias |
| `paula.villalba` | Corrientes | Tiene que responder la **reconfirmación** de *Guantes* |
| `emiliano.ayala` | Posadas | *Filamento PLA*: recién publicado, todavía sin integrantes |

## Qué hay cargado

| Estado | Pools | Ejemplos |
|---|---|---|
| Abierto | 19 | *Papel higiénico* (casi completo: faltan 3), *Lavandina 5 L*, *Remeras lisas* (variantes), *Perfumes árabes* (cupo por variante), *Jabón Dove* (mínimo 12 por persona), *Filamento PLA* (sin integrantes) |
| Listo | 6 | *Detergente* (pagos en los 4 estados), *Toallas* (baja pendiente), *Fernet* (todo pagado), *MicroSD* (recién completo) |
| Caducado | 2 | *Vasos Rigolleau*, *Auriculares* |
| Esperando confirmación | 2 | *Guantes de nitrilo* (uno sigue, uno salió, dos sin responder), *Útiles escolares* |
| En curso | 5 | *Trapos de microfibra* (recepciones parciales, recordatorio), *Power bank* (baja rechazada), *Pasta dental* |
| Finalizado | 8 | *Lavandina Ayudín*, *Cargadores* (reseñas bajas), *Remeras básicas*, *Perfumes Kaiak* |
| Cancelado | 4 | *Ollas* (venció sin nadie), *Cerveza IPA* (cancelado por el organizador), *Smartwatches* (con devoluciones), *Almohadas* (sin respuesta del organizador en 7 días) |

También: pagos pendientes, enviados, confirmados y rechazados con motivo;
bajas en los cinco estados (pendiente, rechazada, esperando devolución, devuelta y
recibida); ~60 mensajes de chat; ~65 reseñas; historial completo de cada pool;
notificaciones leídas y sin leer; enlaces con confianza alta, media y baja; pools en
Corrientes, Resistencia, Posadas, Córdoba, Rosario y Buenos Aires (con mapa). Algunos
usuarios demo se sumaron a pools reales que seguían abiertos.

## Guion sugerido (≈15 minutos)

1. **Sin sesión:** inicio (destacados, "cerca de completarse", categorías) → Explorar,
   con filtros por categoría (Ropa → Remera), ciudad, precio y estado. Sin sesión no se
   ve la dirección ni los integrantes.
2. **`lucia.fernandez`:** campanita con avisos sin leer → *Mis pools*.
   - *Detergente* (listo): **Pagos y entrega**. Ver un comprobante, **confirmar** el de
     Valentina y **rechazar** otro con motivo. Mostrar el chat y el historial.
   - *Trapos de microfibra* (en curso): quiénes ya retiraron y quiénes faltan.
   - *Lavandina Ayudín* (finalizado): reseñas y calificación.
3. **`tomas.aguirre`:** *Remeras lisas*, pool con talle y color; qué pidió cada
   integrante. Desde otra cuenta, unirse eligiendo talles y colores.
4. **`sofia.benitez`:** *Toallas*, pedido de baja de Valentina (ya había pagado):
   aprobar o rechazar.
5. **`joaquin.sosa`:** *Vasos* (caducado): **extender el plazo**; el pool pasa a
   "Esperando confirmación".
6. **`paula.villalba`:** *Guantes*: responder la reconfirmación ("Sigo" / "Salgo").
7. **`camila.ramirez`:** *Fernet*: **Confirmar pedido** (listo → en curso). Después,
   como `joaquin.sosa`, confirmar la recepción.
8. **`diego.romero`:** en *Smartwatches* (cancelado) confirmar que recibió la
   devolución. Abrir su perfil público: promedio y reseñas recibidas.
9. **Crear un pool** con cualquier cuenta: pegar un link de MercadoLibre (autocompleta
   nombre, precio e imagen) y ver el análisis de seguridad del enlace.
10. **`admin.demo`:** panel de administración, con usuarios (filtros, activar o
    desactivar, enviar restablecimiento) y categorías con sus atributos.

## Cómo se carga

- `python manage.py poblar_demo` carga todo; si ya está cargado no hace nada.
- `python manage.py poblar_demo --borrar` borra los usuarios `@poolshop.demo` y todo
  lo que crearon (pools, uniones a pools reales, archivos). Los datos reales quedan.
- En Render no hay Shell en el plan free: con la variable `POBLAR_DEMO=true` el
  arranque del servicio (`backend/arranque.sh`) corre el comando en segundo plano.
  Para que las imágenes sobrevivan a los reinicios hace falta `ARCHIVOS_EN_DB=true`.
- Cada acción pasa por los endpoints reales (unirse, pagar, confirmar, chatear,
  calificar…), así que respeta las reglas de la app y deja historial y notificaciones
  como un uso real. Durante la carga no sale ningún mail.
- Las fechas se calculan desde el día de la carga: los pools abiertos vencen entre 12
  y 28 días después, y la historia se reparte en las semanas anteriores.
- Datos en `backend/pools/demo/datos.py`; imágenes generadas con Pillow en
  `backend/pools/demo/imagenes.py`.
