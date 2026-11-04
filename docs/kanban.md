# Kanban — PoolShop

## Hecho

- **Fase 0 — Setup:** repo, Docker Postgres 17, venv + `requirements.txt`, Django `config` + apps `users`/`pools`, `User` custom, SvelteKit SPA, README.
- **Fase 1 — Usuarios:** API `/api/v1/auth/{register,login,refresh,me}` con JWT + tests; frontend registro/login/perfil/home; casos PS-H1-CP3/CP4.
- **Fase 2 — Núcleo de Pools:** modelos `Category`/`Pool`/`PoolImage`/`Membership` + migraciones + seed de categorías; API CRUD + filtros + unirse/salir/cantidad + transiciones de estado + imágenes; frontend pools (lista, detalle, crear, editar, mis pools, unidos, home). Casos: PS-H2-CP3/CP4 (alta), PS-H3-CP2 (detalle), PS-H4-CP1/CP2 (edición), PS-H5-CP2/CP3 (unirse), PS-H7-CP1 (buscar).
- **Rediseño UI completo — dirección: claro editorial sobrio:** sistema de diseño con tokens en `src/app.css` (paleta, tipografía, espaciado, radios, sombras, foco y movimiento reducido), tipografías Fraunces + Instrument Sans (luego reemplazadas por Bricolage Grotesque + DM Sans en el rediseño Plan A), shell nuevo (header pegajoso con menú móvil accesible y footer), todas las páginas rehechas (`/`, `/login`, `/registro`, `/perfil`, `/pools`, `/pools/[id]`, `/pools/nuevo`, `/pools/[id]/editar`, `/mis-pools`, `/unidos`) con estados de carga/vacío/error y avisos. Sin cambios de lógica ni de contratos de API.
- **Iteración UI — más color y detalle de pool:** paleta de apoyo (azul/verde/ámbar/coral/violeta/teal) con tonos estables por categoría y por nombre para avatares; chips e íconos de categoría, pasos a color y franja tintada en home; detalle de pool con galería de miniaturas, timeline de estados, tiles con íconos, avatares de integrantes y botón "Copiar enlace". Sin cambios de lógica.

- **Iteración 2:** mail de recuperación desde la cuenta de PoolShop (SMTP Gmail por `.env`); perfil público `/usuarios/[id]` (pools creados, antigüedad, puntaje y reseñas); calificaciones entre participantes al finalizar un pool; búsqueda de perfiles desde la barra del header; popup con check al unirse; autocompletado de nombre, precio unitario/total e imagen desde el enlace del producto (`POST /pools/previsualizar-enlace/`, anti-SSRF); la imagen de la card abre el detalle; sección `/notificaciones` (cambios de estado, mensajes nuevos del chat, nuevos miembros) con campana en el header y preferencias por tipo + mail; correos HTML: verificación de email obligatoria al registrarse, bienvenida, contraseña cambiada, confirmación al unirse y baja con un click.

- **Release 3:** chat por pool (polling), mapa Leaflet + Nominatim, caducidad automática, eliminación con aprobación, pagos con comprobante y confirmación de recepción, rediseño del detalle.

- **Release 4 — Iteración 3 (feedback `Funcionalidades_pendientes`):** documentada en `docs/Release4-PoolShop.docx` y `docs/Release4-Presentación.pdf` (sprints 7 y 8, HU 15 a 25, casos PS-H15 a PS-H25).
  - **Fase 0 — bugs bloqueantes:** sesión de 30 min con refresh automático y rotativo (antes vencía a los 5 min y al refrescar se cerraba), aviso "Tu sesión expiró" con vuelta a la página (`?next=`) y borrador de "Crear pool"; fotos HEIC/WEBP/GIF convertidas a JPEG, URLs de media relativas, `ALLOWED_HOSTS` abierto en dev (acceso por IP de la red), check de carpetas de media; categorías sin paginar; `tareas_periodicas` (cron de Render + `scheduler` de compose); `probar_correo` y variables de correo en Render.
  - **Fase 1:** categoría Ropa; precio total calculado (solo lectura, también `precio_total` en la API); avisos de comprobante enviado, pago confirmado/rechazado y recepción (preferencia "Pagos y entregas"); datos para transferir (alias/CBU y titular, solo para integrantes); resumen "Recaudado $X de $Y"; transiciones con lock; `recordar_recepcion` cada 3 días en las tareas periódicas; "Unidos" en el menú; confianza del organizador en el detalle; ubicación con link a Google Maps aunque falle el geocoding; análisis del enlace al crear el pool; backoffice: mail para restablecer contraseña y permisos de admin (solo superusuario); `User` en el admin de Django; montos con centavos siempre de dos dígitos.
  - **Fase 2:** autocompletado robusto: links de hasta 2000 caracteres sin tracking; MercadoLibre por API pública (incluye links de catálogo con `item_id`); VTEX, Tiendanube, microdatos y Amazon; headers de navegador, HTML truncado en vez de rechazado, charset de `<meta>`, 5 redirects, precio en otra moneda no se completa y se avisa; motivo es-AR (bloqueado, no disponible, sin datos…); anti-SSRF también contra DNS rebinding; tests offline con fixtures. Atributos por categoría: subcategorías (Ropa > Remera, Buzo, Pantalón, Calzado; Higiene personal > Perfume; Electrónica > Accesorios) que heredan atributos; el creador marca qué talles/colores ofrece; al unirse cada integrante reparte su cantidad entre variantes; resumen por variante con CSV para el organizador; filtrar por "Ropa" incluye sus subcategorías.
  - **Fase 3:** app `proveedores`. Directorio de mayoristas curado (`/mayoristas`): filtros por rubro (incluye subcategorías), provincia y verificados; ficha con análisis de confianza del sitio y pools que lo usaron; los usuarios sugieren sitios que el staff aprueba en `/admin/mayoristas`; carga masiva con `importar_mayoristas archivo.csv`. Comparador de costo final (`/comparar` y pestaña "Comparador" del pool para sus integrantes): ofertas ordenadas por costo total (precio × max(cantidad, mínimo) + envío + impuestos + aduana estimada para importaciones), tiles de resumen, desglose, tendencia de precio, "Actualizar precios" desde el enlace y "Crear pool con esta oferta". Tipo de cambio y alícuotas como parámetros editables (valores de referencia, rotulados como estimación). Backoffice con pestañas y `/admin/categorias` (subcategorías y atributos).
  - **Fase 4:** documentación del Release 4 (docx y presentación con capturas de los recorridos e2e), casos de prueba PS-H15 a PS-H25 y README.
- **Integración continua:** `.github/workflows/ci.yml` corre en cada PR y en `main` ruff, `makemigrations --check`, pytest (con Postgres 17), `node --test` y el build del front.

## Pendiente

- Baja de perfil por el propio usuario.
- Puesta en marcha: cargar la cuenta de Gmail en Render (`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`, `FRONTEND_URL`), el tipo de cambio en `/admin/mayoristas` y el directorio inicial de mayoristas.

## Permisos

- Lectura de `pools` y `categories` pública (`IsAuthenticatedOrReadOnly` / `AllowAny`); escritura y acciones requieren sesión.
- `mios`/`unidos` requieren sesión.
- Perfiles públicos: `id`, `username`, `first_name`, `last_name`, `foto` (sin email).

## Desvíos y límites aceptados

- `POST /auth/me/foto` → se implementa como `PATCH /auth/me/` multipart. Sin endpoint separado de foto.
- `mis-pools` y `unidos` muestran la primera página (12) sin controles de paginación.
- Validación de imágenes (máx. 10, JPEG/PNG) en la vista/serializer, no como constraint de DB.
- El estado `abierto`/`listo` se recalcula en create/patch/unirse/salir/mi-membresía; no aplica a `en_curso`/`finalizado`/`cancelado`.
- PATCH de pool sin `select_for_update` (ventana de carrera estrecha; las transiciones, unirse/salir y pagos sí usan `_bloqueado`).
