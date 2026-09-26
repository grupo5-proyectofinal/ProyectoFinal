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
