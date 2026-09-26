# Kanban — PoolShop

## Hecho

- **Fase 0 — Setup:** repo, Docker Postgres 17, venv + `requirements.txt`, Django `config` + apps `users`/`pools`, `User` custom, SvelteKit SPA, README.
- **Fase 1 — Usuarios:** API `/api/v1/auth/{register,login,refresh,me}` con JWT + tests; frontend registro/login/perfil/home; casos PS-H1-CP3/CP4.
- **Fase 2 — Núcleo de Pools:** modelos `Category`/`Pool`/`PoolImage`/`Membership` + migraciones + seed de categorías; API CRUD + filtros + unirse/salir/cantidad + transiciones de estado + imágenes; frontend pools (lista, detalle, crear, editar, mis pools, unidos, home); casos PS-H2-CP1..CP5.

## En curso

- (nada)

## Pendiente

- **Fase 3 — Features posteriores:** chat (polling REST), radio/Leaflet, calificaciones y reseñas, notificaciones, baja de perfil, expiración automática de pools, solicitud de eliminación con miembros.

## Desvíos aceptados

- `POST /auth/me/foto` → se implementa como `PATCH /auth/me/` multipart. Sin endpoint separado de foto.
