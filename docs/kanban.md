# Kanban — PoolShop

## Hecho

- **Fase 0 — Setup:** repo, Docker Postgres 17, venv + `requirements.txt`, Django `config` + apps `users`/`pools`, `User` custom, SvelteKit SPA, README.
- **Fase 1 — Usuarios:** API `/api/v1/auth/{register,login,refresh,me}` con JWT + tests; frontend registro/login/perfil/home; casos PS-H1-CP3/CP4.
- **Fase 2 — Núcleo de Pools:** modelos `Category`/`Pool`/`PoolImage`/`Membership` + migraciones + seed de categorías; API CRUD + filtros + unirse/salir/cantidad + transiciones de estado + imágenes; frontend pools (lista, detalle, crear, editar, mis pools, unidos, home). Casos: PS-H2-CP3/CP4 (alta), PS-H3-CP2 (detalle), PS-H4-CP1/CP2 (edición), PS-H5-CP2/CP3 (unirse), PS-H7-CP1 (buscar).
- **Rediseño UI completo — dirección: claro editorial sobrio:** sistema de diseño con tokens en `src/app.css` (paleta, tipografía, espaciado, radios, sombras, foco y movimiento reducido), tipografías Fraunces + Instrument Sans (luego reemplazadas por Bricolage Grotesque + DM Sans en el rediseño Plan A), shell nuevo (header pegajoso con menú móvil accesible y footer), todas las páginas rehechas (`/`, `/login`, `/registro`, `/perfil`, `/pools`, `/pools/[id]`, `/pools/nuevo`, `/pools/[id]/editar`, `/mis-pools`, `/unidos`) con estados de carga/vacío/error y avisos. Sin cambios de lógica ni de contratos de API.
- **Iteración UI — más color y detalle de pool:** paleta de apoyo (azul/verde/ámbar/coral/violeta/teal) con tonos estables por categoría y por nombre para avatares; chips e íconos de categoría, pasos a color y franja tintada en home; detalle de pool con galería de miniaturas, timeline de estados, tiles con íconos, avatares de integrantes y botón "Copiar enlace". Sin cambios de lógica.

- **Iteración 2:** mail de recuperación desde la cuenta de PoolShop (SMTP Gmail por `.env`); perfil público `/usuarios/[id]` (pools creados, antigüedad, puntaje y reseñas); calificaciones entre participantes al finalizar un pool; búsqueda de perfiles desde la barra del header; popup con check al unirse; autocompletado de nombre, precio unitario/total e imagen desde el enlace del producto (`POST /pools/previsualizar-enlace/`, anti-SSRF); la imagen de la card abre el detalle; sección `/notificaciones` (cambios de estado, mensajes nuevos del chat, nuevos miembros) con campana en el header y preferencias por tipo + mail; correos HTML: verificación de email obligatoria al registrarse, bienvenida, contraseña cambiada, confirmación al unirse y baja con un click.

- **Release 3:** chat por pool (polling), mapa Leaflet + Nominatim, caducidad automática, eliminación con aprobación, pagos con comprobante y confirmación de recepción, rediseño del detalle.

## En curso — Iteración 3 (feedback `Funcionalidades_pendientes`)

- **Fase 0 — bugs bloqueantes (hecho):** sesión de 30 min con refresh automático y rotativo (antes vencía a los 5 min y al refrescar se cerraba), aviso "Tu sesión expiró" con vuelta a la página (`?next=`) y borrador de "Crear pool"; fotos HEIC/WEBP/GIF convertidas a JPEG, URLs de media relativas, `ALLOWED_HOSTS` abierto en dev (acceso por IP de la red), check de carpetas de media; categorías sin paginar; `tareas_periodicas` (cron de Render + `scheduler` de compose); `probar_correo` y variables de correo en Render.
- **Fase 1 (hecho):** categoría Ropa; precio total calculado (solo lectura, también `precio_total` en la API); avisos de comprobante enviado, pago confirmado/rechazado y recepción (preferencia "Pagos y entregas"); datos para transferir (alias/CBU y titular, solo para integrantes); resumen "Recaudado $X de $Y"; transiciones con lock; `recordar_recepcion` cada 3 días en las tareas periódicas; "Unidos" en el menú; confianza del organizador en el detalle; ubicación con link a Google Maps aunque falle el geocoding; análisis del enlace al crear el pool; backoffice: mail para restablecer contraseña y permisos de admin (solo superusuario); `User` en el admin de Django; montos con centavos siempre de dos dígitos.
- **Fase 2:** autocompletado robusto (MercadoLibre, VTEX, Tiendanube, URLs largas) y atributos por categoría (Ropa > Remera > Talle/Color).
- **Fase 3:** directorio de mayoristas y comparador de costo final.

## Pendiente

- Baja de perfil por el propio usuario.

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
