# Casos de prueba — PoolShop

Formato: ID, título, tipo (caja negra), descripción, datos, precondiciones y pasos con resultado esperado.

## PS-H1-CP3 — Alta de usuario exitosa

- **Tipo:** Caja negra
- **Descripción:** Un visitante completa el formulario de registro con datos válidos y queda con sesión iniciada.
- **Datos:**
  - Email: `ana@example.com`
  - Nombre de usuario: `ana`
  - Nombre: `Ana`
  - Apellido: `Pérez`
  - DNI: `30111222`
  - Teléfono: `3511234567`
  - Género: `Femenino`
  - Dirección: `Av. Siempre Viva 742`
  - Ciudad: `Córdoba`
  - Foto: (sin archivo)
  - Contraseña: `Zq7!mN2pLxD`
  - Repetir contraseña: `Zq7!mN2pLxD`
- **Precondiciones:** El email, el nombre de usuario y el DNI no existen en el sistema. Backend y frontend en ejecución.
- **Pasos:**
  1. Ir a `/registro`.
  2. Completar todos los campos obligatorios con los datos indicados.
  3. Presionar "Crear cuenta".
- **Resultado esperado:**
  - El backend responde `201` con el usuario y los tokens `access`/`refresh`.
  - La app guarda la sesión y redirige a `/` (home).
  - El header muestra "Mi perfil" y "Cerrar sesión".
  - `/perfil` muestra los datos cargados (email, usuario, DNI).

## PS-H1-CP4 — Alta con email inválido

- **Tipo:** Caja negra
- **Descripción:** Un visitante intenta registrarse con un email con formato inválido y el sistema rechaza el alta mostrando el error en el campo.
- **Datos:**
  - Email: `ana-arroba-example.com`
  - Resto de los campos: válidos y únicos (igual que PS-H1-CP3).
- **Precondiciones:** Backend y frontend en ejecución. Se usa un DNI y un usuario que no existan.
- **Pasos:**
  1. Ir a `/registro`.
  2. Escribir el email inválido indicado y completar el resto con datos válidos.
  3. Presionar "Crear cuenta".
- **Resultado esperado:**
  - El backend responde `400` con el error en `email`.
  - No se crea ningún usuario.
  - La pantalla muestra el mensaje de error debajo del campo Email y no redirige.

## PS-H2-CP3 — Alta de pool exitosa

- **Tipo:** Caja negra
- **Descripción:** Un usuario con sesión crea un pool con datos válidos.
- **Datos:**
  - Título: `Yerba grupal`
  - Producto: `Yerba 1kg`
  - Categoría: `Alimentos`
  - Precio unitario: `1500.00`
  - Cantidad total: `10`
  - Cantidad del creador: `2`
  - Mínimo por integrante: `1`
  - Caducidad: hoy + 5 días
  - Tipo de pago: `Efectivo`
  - Dirección: `Av. Siempre Viva 742`, Ciudad: `Córdoba`
- **Precondiciones:** Sesión iniciada.
- **Pasos:**
  1. Ir a `/pools/nuevo`.
  2. Completar el formulario con los datos indicados.
  3. Presionar "Crear pool".
- **Resultado esperado:**
  - El backend responde `201`.
  - Redirige al detalle del pool creado.
  - El detalle muestra disponible `8`, estado `Abierto` y creador = usuario actual.
  - El pool aparece en `/mis-pools`.

## PS-H2-CP4 — Alta fallida por título vacío

- **Tipo:** Caja negra
- **Descripción:** Un usuario intenta crear un pool sin título y el sistema rechaza el alta.
- **Datos:** Resto de los campos válidos; Título vacío.
- **Precondiciones:** Sesión iniciada.
- **Pasos:**
  1. Ir a `/pools/nuevo`.
  2. Dejar el título vacío y completar el resto.
  3. Presionar "Crear pool".
- **Resultado esperado:**
  - El formulario no se envía por la validación `required` del campo Título, o bien el backend responde `400` con el error en `titulo`.
  - No se crea ningún pool y no se redirige.

## PS-H5-CP2 — Unión exitosa a un pool

- **Tipo:** Caja negra
- **Descripción:** Un usuario distinto del creador se une a un pool abierto con una cantidad válida.
- **Datos:** Cantidad a unirse: `3`. Pool abierto con disponible `8` y mínimo por integrante `1`.
- **Precondiciones:** Sesión iniciada con un usuario que no es el creador ni miembro. El pool está en estado `abierto`.
- **Pasos:**
  1. Ir al detalle del pool.
  2. Ingresar `3` en el campo de cantidad.
  3. Presionar "Unirse".
- **Resultado esperado:**
  - El backend responde `201`.
  - El disponible baja de `8` a `5`.
  - El usuario aparece en la lista de miembros con cantidad `3`.
  - El pool aparece en `/unidos`.

## PS-H5-CP3 — Unión rechazada por superar el disponible

- **Tipo:** Caja negra
- **Descripción:** Un usuario intenta unirse con una cantidad mayor al disponible.
- **Datos:** Cantidad a unirse: `99`. Pool con disponible `8`.
- **Precondiciones:** Sesión iniciada con un usuario que no es el creador ni miembro.
- **Pasos:**
  1. Ir al detalle del pool.
  2. Ingresar `99` en el campo de cantidad.
  3. Presionar "Unirse".
- **Resultado esperado:**
  - El backend responde `400` con el error en `cantidad`.
  - El disponible no cambia y el usuario no queda como miembro.

## PS-H3-CP2 — Visualización del detalle del pool

- **Tipo:** Caja negra
- **Descripción:** Un usuario con sesión abre el detalle de un pool y ve toda su información.
- **Datos:** Pool creado y, opcionalmente, con miembros e imágenes.
- **Precondiciones:** Sesión iniciada. El pool existe.
- **Pasos:**
  1. Ir a `/pools`.
  2. Presionar "VER" en la tarjeta del pool.
- **Resultado esperado:**
  - Se muestra: producto, categoría, descripción, enlace (si hay), precio unitario, cantidades, disponible, mínimo, caducidad, tipo de pago, dirección, ciudad, estado, creador, vistas e imágenes.
  - La lista de miembros muestra el nombre de usuario y la cantidad.
  - El contador de vistas del pool aumenta en 1.
  - Si el usuario es el creador, ve las acciones Editar/Eliminar/Confirmar/Finalizar/Cancelar según el estado; si no, ve Unirse o Salir según corresponda.

## PS-H4-CP1 — Editar pool

- **Tipo:** Caja negra
- **Descripción:** El creador edita un pool abierto y sin miembros.
- **Datos:** Título: `Yerba premium`; Producto: `Yerba 1kg`; Precio unitario: `1800.00`; Cantidad total: `12`; Dirección: `Calle 2`; Ciudad: `Rosario`; Categoría, caducidad, mínimo y tipo de pago válidos.
- **Precondiciones:** Sesión iniciada como creador. El pool está en estado `abierto` y no tiene miembros.
- **Pasos:**
  1. Ir al detalle del pool.
  2. Presionar "Editar".
  3. Cambiar los campos indicados.
  4. Presionar "Guardar cambios".
- **Resultado esperado:**
  - El backend responde `200` con los campos actualizados.
  - El detalle refleja los nuevos valores.
  - Si hay otros miembros, cambiar un campo inmutable responde `400` con el error en ese campo.

## PS-H4-CP2 — Editar la cantidad de mi propia membresía

- **Tipo:** Caja negra
- **Descripción:** Un miembro cambia la cantidad con la que participa en un pool abierto o listo.
- **Datos:** Nueva cantidad: `4`.
- **Precondiciones:** Sesión iniciada como miembro (no creador). El pool está en estado `abierto` o `listo`.
- **Pasos:**
  1. Ir al detalle del pool.
  2. Cambiar el número en el campo de cantidad.
  3. Presionar "Guardar cantidad".
- **Resultado esperado:**
  - El backend responde `200` con el pool actualizado.
  - La cantidad del miembro cambia a `4` y `disponible` se recalcula.
  - Si la cantidad supera lo disponible o baja del mínimo, responde `400` con el error en `cantidad`.

## PS-H7-CP1 — Buscar pools

- **Tipo:** Caja negra
- **Descripción:** Un visitante busca pools por texto y combina filtros.
- **Datos:** Texto: `yerba`; Categoría: `Alimentos`; Ciudad: `Córdoba`.
- **Precondiciones:** Existen pools que coinciden y otros que no. La lectura de pools es pública.
- **Pasos:**
  1. Ir a `/pools`.
  2. Escribir `yerba` y aplicar los filtros.
  3. Presionar "Filtrar".
- **Resultado esperado:**
  - Se listan solo los pools cuyo título, producto o descripción contienen `yerba` y cumplen los filtros.
  - La URL refleja los filtros y la paginación usa "Anterior"/"Siguiente".
  - Si no hay coincidencias, muestra "No se encontraron resultados."

## Release 4 — Iteración 3 (feedback "Funcionalidades pendientes")

Casos ejecutados con los recorridos end-to-end de `.claude/skills/poolshop-e2e` (Chromium entrando por la IP de la red). Los mismos casos, con capturas, están en `docs/Release4-PoolShop.docx`.

## PS-H15-CP1 — La sesión se renueva al recargar

- **Tipo:** Caja negra
- **Descripción:** Verificar que, con la sesión corta vencida pero la renovación vigente, recargar la página no cierra la sesión.
- **Datos:**
  - Usuario: ana@poolshop.test
- **Precondiciones:** El usuario tiene la sesión iniciada. La sesión corta (access) está vencida.
- **Pasos:**
  1. Ingresar a "Crear pool" y recargar la página.
  2. Abrir el selector de categoría.
- **Resultado esperado:**
  - La página se recarga sin pedir login.
  - Se listan las categorías.

## PS-H15-CP2 — Sesión expirada con aviso y borrador recuperado

- **Tipo:** Caja negra
- **Descripción:** Verificar que, cuando la sesión ya no se puede renovar, se avisa, se vuelve a la página anterior y no se pierde lo cargado.
- **Datos:**
  - Título del pool: "Compra de perfumes (borrador e2e)"
- **Precondiciones:** El usuario tiene la sesión iniciada. Su sesión completa (access y renovación) está vencida.
- **Pasos:**
  1. Escribir el título en "Crear pool".
  2. Recargar la página.
  3. Ingresar con el email y la contraseña.
- **Resultado esperado:**
  - El título queda cargado.
  - Aparece "Tu sesión expiró" y se abre el login con ?next=.
  - Vuelve a "Crear pool" con el título recuperado.

## PS-H16-CP1 — Foto de perfil HEIC desde la IP de la red

- **Tipo:** Caja negra
- **Descripción:** Verificar que una foto HEIC de iPhone se sube como foto de perfil y se ve entrando por la IP de la red.
- **Datos:**
  - Archivo: IMG_0001.HEIC
  - Dirección: http://<ip-de-la-red>:5173
- **Precondiciones:** El usuario tiene la sesión iniciada.
- **Pasos:**
  1. Ir a "Mi perfil" y elegir la foto.
  2. Presionar "Guardar cambios".
  3. Recargar la página.
- **Resultado esperado:**
  - Se acepta el archivo.
  - Aparece "Datos actualizados."
  - La foto de perfil se ve.

## PS-H16-CP2 — Pool con imagen de WhatsApp

- **Tipo:** Caja negra
- **Descripción:** Verificar que se puede crear un pool con una imagen WEBP y que se ve en el detalle.
- **Datos:**
  - Título: "Pool e2e con foto de WhatsApp"
  - Producto: "Perfume 100 ml"
  - Precio unitario: 12000
  - Cantidad total: 20
  - Imagen: imagen_de_whatsapp.webp
- **Precondiciones:** El usuario tiene la sesión iniciada.
- **Pasos:**
  1. Completar "Crear pool" con los datos y la imagen.
  2. Presionar "Crear pool".
  3. Mirar la imagen del detalle.
- **Resultado esperado:**
  - El formulario acepta la imagen.
  - Se abre el detalle del pool.
  - La imagen se ve.

## PS-H17-CP1 — Ropa en el selector de categorías

- **Tipo:** Caja negra
- **Descripción:** Verificar que la categoría Ropa se puede elegir al crear un pool.
- **Precondiciones:** El usuario tiene la sesión iniciada.
- **Pasos:**
  1. Ir a "Crear pool" y abrir el selector de categoría.
- **Resultado esperado:**
  - Aparece "Ropa".

## PS-H18-CP1 — Total calculado y no editable

- **Tipo:** Caja negra
- **Descripción:** Verificar que el total se calcula solo y no se puede escribir.
- **Datos:**
  - Precio unitario: 1234.5
  - Cantidad total: 3
- **Precondiciones:** El usuario tiene la sesión iniciada.
- **Pasos:**
  1. Ir a "Crear pool" e intentar escribir en el precio total.
  2. Cargar el precio unitario y la cantidad.
- **Resultado esperado:**
  - El total no es editable.
  - El total muestra $ 3.703,50.

## PS-H19-CP1 — Comprobante enviado y aviso al organizador

- **Tipo:** Caja negra
- **Descripción:** Verificar que el integrante ve los datos para transferir, envía el comprobante y el organizador recibe el aviso.
- **Datos:**
  - Pool: "Pool e2e de pagos" (organiza admin, ana reservó 2)
  - Comprobante: foto.png
- **Precondiciones:** Ana es integrante del pool y tiene la sesión iniciada. El organizador cargó alias y titular.
- **Pasos:**
  1. Abrir la sección Pagos y entrega del pool.
  2. Adjuntar el comprobante y presionar "Enviar comprobante".
  3. Ingresar como organizador y abrir Notificaciones.
  4. Abrir Pagos y entrega del pool.
- **Resultado esperado:**
  - Se ven alias y titular para transferir.
  - El pago queda esperando revisión.
  - Hay un aviso de comprobante enviado.
  - Se ve el resumen Recaudado.

## PS-H21-CP1 — Enlace que no se puede abrir

- **Tipo:** Caja negra
- **Descripción:** Verificar que un enlace inaccesible explica el motivo y se limpia de parámetros de seguimiento.
- **Datos:**
  - Enlace: https://no-existe-poolshop-e2e.invalid/producto?utm_source=wa#x
- **Precondiciones:** El usuario tiene la sesión iniciada.
- **Pasos:**
  1. Pegar el enlace en "Crear pool".
  2. Presionar "Autocompletar".
  3. Mirar el campo del enlace.
- **Resultado esperado:**
  - El enlace queda cargado.
  - Se informa que no se pudo abrir el enlace.
  - Ya no tiene utm_source ni #x.

## PS-H22-CP1 — Unirse con dos variantes

- **Tipo:** Caja negra
- **Descripción:** Verificar que un integrante se une con dos variantes y el organizador ve el pedido por variante.
- **Datos:**
  - Pool: "Remeras e2e con talles" (Ropa > Remera)
  - Talles ofrecidos: S, M
  - Colores ofrecidos: Negro, Blanco
  - Variantes: M/Negro × 2, S/Blanco × 1
- **Precondiciones:** Organizador (admin) e integrante (ana) con sesión iniciada.
- **Pasos:**
  1. Crear el pool eligiendo Ropa > Remera y marcando S, M, Negro y Blanco.
  2. Como integrante, cargar las dos variantes y unirse.
  3. Como organizador, abrir Participantes.
- **Resultado esperado:**
  - Se crea el pool.
  - Aparece "Te uniste".
  - El pedido por variante muestra M · Negro = 2 y S · Blanco = 1.

## PS-H23-CP1 — Ver los atributos de una subcategoría

- **Tipo:** Caja negra
- **Descripción:** Verificar que el administrador ve la jerarquía y los atributos de Remera.
- **Datos:**
  - Usuario: admin@poolshop.test
- **Precondiciones:** El usuario es administrador y tiene la sesión iniciada.
- **Pasos:**
  1. Ir a Admin > Categorías.
  2. Elegir "Remera".
- **Resultado esperado:**
  - Se ve el árbol de categorías.
  - Se ven los atributos de Remera con los talles XS a XXL.

## PS-H24-CP1 — Sugerir, aprobar y usar un mayorista

- **Tipo:** Caja negra
- **Descripción:** Verificar que una sugerencia aprobada aparece en el directorio y permite crear un pool con su enlace.
- **Datos:**
  - Nombre: "Mayorista e2e <marca de tiempo>"
  - Sitio: https://mayorista-e2e-<marca>.com.ar
- **Precondiciones:** Usuario común y administrador con sesión iniciada.
- **Pasos:**
  1. En Mayoristas, "Sugerir un sitio" y enviar.
  2. Como admin, en Admin > Mayoristas presionar "Aprobar".
  3. Abrir la ficha del mayorista.
  4. Presionar "Crear pool con este sitio".
- **Resultado esperado:**
  - Se informa que lo van a revisar.
  - El mayorista queda publicado.
  - Se ve la confianza del enlace.
  - Crear pool abre con el enlace cargado.

## PS-H25-CP1 — Orden por costo total con una importación

- **Tipo:** Caja negra
- **Descripción:** Verificar que tres ofertas (una importada en USD) se ordenan por costo total para 10 unidades.
- **Datos:**
  - Cantidad: 10
  - Tienda Local: $ 45.000 c/u, envío $ 0
  - Mayorista Barato: $ 38.000 c/u, envío $ 60.000
  - Importado: USD 25 c/u, envío USD 40, derechos 20 % (tipo de cambio cargado: 1000)
- **Precondiciones:** El usuario tiene la sesión iniciada. El staff cargó el tipo de cambio USD.
- **Pasos:**
  1. En Comparar costos, crear la comparación. (valor: 10)
  2. Agregar las tres ofertas.
  3. Mirar el orden de la tabla.
  4. Ver el desglose del importado.
- **Resultado esperado:**
  - Se abre la comparación vacía.
  - Se agregan las tres.
  - Importado < Mayorista Barato < Tienda Local.
  - Se ve la aduana estimada.

## PS-H26-CP1 — Eliminar la cuenta propia

- **Tipo:** Caja negra
- **Descripción:** Verificar que el usuario puede darse de baja solo sin pools activos, y que después no puede volver a ingresar.
- **Datos:**
  - Contraseña incorrecta: "otra"
  - Contraseña correcta: la del usuario
- **Precondiciones:** El usuario tiene la sesión iniciada y organiza un pool abierto.
- **Pasos:**
  1. En Mi perfil, presionar "Eliminar mi cuenta" e ingresar la contraseña incorrecta.
  2. Ingresar la contraseña correcta y presionar "Eliminar definitivamente".
  3. Cancelar el pool abierto y volver a presionar "Eliminar definitivamente".
  4. Intentar ingresar con el mismo email y contraseña.
- **Resultado esperado:**
  - Se informa "La contraseña no es correcta.".
  - Se informa que primero tiene que cerrar o salir de sus pools activos, con la lista de esos pools.
  - Se cierra la sesión, se vuelve al inicio y se informa "Tu cuenta fue eliminada.".
  - El ingreso es rechazado. Sus mensajes en pools terminados figuran como "Usuario eliminado".
