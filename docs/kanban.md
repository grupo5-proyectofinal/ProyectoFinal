# Kanban — PoolShop

## Hecho

- **Fase 0 — Setup:** repo, Docker Postgres 17, venv + `requirements.txt`, Django `config` + apps `users`/`pools`, `User` custom, SvelteKit SPA, README.
- **Fase 1 — Usuarios:** API `/api/v1/auth/{register,login,refresh,me}` con JWT + tests; frontend registro/login/perfil/home; casos PS-H1-CP3/CP4 en `casos-de-prueba.md`.

## En curso

- (nada)

## Pendiente

- **Fase 2 — Núcleo de Pools:** modelos `Category`/`Pool`/`PoolImage`/`Membership`, CRUD + filtros + unirse/salir, imágenes, pantallas.

## Desvíos aceptados

- `POST /auth/me/foto` → se implementa como `PATCH /auth/me/` multipart. Sin endpoint separado de foto.
