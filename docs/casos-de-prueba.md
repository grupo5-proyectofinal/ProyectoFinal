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

## PS-H2-CP1 — Alta de pool exitosa

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

## PS-H2-CP2 — Alta fallida por título vacío

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

## PS-H2-CP3 — Unión exitosa a un pool

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

## PS-H2-CP4 — Unión rechazada por superar el disponible

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

## PS-H2-CP5 — Visualización del detalle del pool

- **Tipo:** Caja negra
- **Descripción:** Un usuario con sesión abre el detalle de un pool y ve toda su información.
- **Datos:** Pool creado y, opcionalmente, con miembros e imágenes.
- **Precondiciones:** Sesión iniciada. El pool existe.
- **Pasos:**
  1. Ir a `/pools`.
  2. Presionar "VER" en la tarjeta del pool.
- **Resultado esperado:**
  - Se muestra: producto, categoría, descripción, enlace (si hay), precio unitario, cantidades, disponible, mínimo, caducidad, tipo de pago, dirección, ciudad, estado, creador, vistas e imágenes.
  - La lista de miembros muestra email y cantidad.
  - El contador de vistas del pool aumenta en 1.
  - Si el usuario es el creador, ve las acciones Editar/Eliminar/Confirmar/Finalizar/Cancelar según el estado; si no, ve Unirse o Salir según corresponda.

