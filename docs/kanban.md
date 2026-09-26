# Kanban — PoolShop

## Hecho

- **Fase 0 — Setup:** repo, Docker Postgres 17, venv + `requirements.txt`, Django `config` + apps `users`/`pools`, `User` custom, SvelteKit SPA, README.
- **Fase 1 — Usuarios:** API `/api/v1/auth/{register,login,refresh,me}` con JWT + tests; frontend registro/login/perfil/home; casos PS-H1-CP3/CP4.
- **Fase 2 — Núcleo de Pools:** modelos `Category`/`Pool`/`PoolImage`/`Membership` + migraciones + seed de categorías; API CRUD + filtros + unirse/salir/cantidad + transiciones de estado + imágenes; frontend pools (lista, detalle, crear, editar, mis pools, unidos, home). Casos: PS-H2-CP3/CP4 (alta), PS-H3-CP2 (detalle), PS-H4-CP1/CP2 (edición), PS-H5-CP2/CP3 (unirse), PS-H7-CP1 (buscar).
- **Rediseño UI completo — dirección: claro editorial sobrio:** sistema de diseño con tokens en `src/app.css` (paleta, tipografía, espaciado, radios, sombras, foco y movimiento reducido), tipografías Fraunces + Instrument Sans, shell nuevo (header pegajoso con menú móvil accesible y footer), todas las páginas rehechas (`/`, `/login`, `/registro`, `/perfil`, `/pools`, `/pools/[id]`, `/pools/nuevo`, `/pools/[id]/editar`, `/mis-pools`, `/unidos`) con estados de carga/vacío/error y avisos. Sin cambios de lógica ni de contratos de API.
- **Iteración UI — más color y detalle de pool:** paleta de apoyo (azul/verde/ámbar/coral/violeta/teal) con tonos estables por categoría y por nombre para avatares; chips e íconos de categoría, pasos a color y franja tintada en home; detalle de pool con galería de miniaturas, timeline de estados, tiles con íconos, avatares de integrantes y botón "Copiar enlace". Sin cambios de lógica.

## En curso

- (nada)

## Pendiente

- **Fase 3 — Features posteriores:** chat (polling REST), radio/Leaflet, calificaciones y reseñas, notificaciones, baja de perfil, expiración automática de pools, solicitud de eliminación con miembros.

## Permisos

- Lectura de `pools` y `categories` pública (`IsAuthenticatedOrReadOnly` / `AllowAny`); escritura y acciones requieren sesión.
- `mios`/`unidos` requieren sesión.
- Perfiles públicos: `id`, `username`, `first_name`, `last_name`, `foto` (sin email).

## Desvíos y límites aceptados

- `POST /auth/me/foto` → se implementa como `PATCH /auth/me/` multipart. Sin endpoint separado de foto.
- `mis-pools` y `unidos` muestran la primera página (12) sin controles de paginación.
- Validación de imágenes (máx. 10, JPEG/PNG) en la vista/serializer, no como constraint de DB.
- El estado `abierto`/`listo` se recalcula en create/patch/unirse/salir/mi-membresía; no aplica a `en_curso`/`finalizado`/`cancelado`.
- PATCH de pool y transiciones sin `select_for_update` (ventana de carrera estrecha; fix = 4 líneas).
