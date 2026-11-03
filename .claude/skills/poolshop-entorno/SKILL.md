---
name: poolshop-entorno
description: Levanta y verifica el entorno de PoolShop (Postgres + Django/DRF + SvelteKit) en un contenedor o sesión cloud, y corre ruff, pytest, node --test y el build. Usala siempre antes de tocar código del repo, antes de correr tests, antes de un push o cuando algo falla por "no hay base", "SECRET_KEY", "node_modules" o migraciones, aunque el pedido no diga "entorno".
---

# Entorno de PoolShop

El backend (`backend/`, Django 6 + DRF) necesita Postgres y un `.env` en la raíz
del repo con `SECRET_KEY`; sin eso ni `pytest` arranca. El front (`frontend/`,
SvelteKit SPA) necesita Node ≥ 20.19 (Vite 8, `engine-strict`).

## Preparar (idempotente)

```bash
.claude/skills/poolshop-entorno/scripts/preparar.sh
```

Arranca el Postgres del sistema, crea usuario y base `poolshop`, escribe un `.env`
de desarrollo si falta, crea `backend/.venv`, instala dependencias, migra y hace
`npm ci`. En una máquina con Docker y sin Postgres local, la alternativa es
`docker compose up -d db` con el `.env` copiado de `.env.example`.

## Verificar antes de commitear

```bash
.claude/skills/poolshop-entorno/scripts/verificar.sh          # todo (pytest tarda ~3 min)
.claude/skills/poolshop-entorno/scripts/verificar.sh rapido   # ruff + tests del front + build
```

Durante el trabajo conviene correr solo lo tocado:
`cd backend && . .venv/bin/activate && pytest -q -p no:cacheprovider pools/tests.py -k <palabra>`.

`EXE001` (shebang de `manage.py` sin permiso de ejecución) aparece en checkouts
donde git no conserva el modo del archivo: no es un error del código y el script
lo ignora.

## Levantar la app para mirarla

```bash
cd backend && . .venv/bin/activate && python manage.py runserver 0.0.0.0:8000   # en background
cd frontend && npx vite dev --host 0.0.0.0 --port 5173                           # en background
```

El dev server de Vite proxea `/api` y `/media` al 8000. Para probar como "otro
dispositivo de la red" usá la IP del contenedor (`hostname -I`) en vez de
localhost: así aparecen los problemas de host y de URLs de media.

Usuarios de prueba (el login exige email verificado):

```bash
cd backend && . .venv/bin/activate && python manage.py shell -c "
from users.models import User
for email, staff in (('admin@poolshop.test', True), ('ana@poolshop.test', False)):
    u, _ = User.objects.get_or_create(email=email, defaults={'username': email.split('@')[0], 'dni': str(abs(hash(email)))[:8]})
    u.set_password('Clave-segura-123'); u.email_verificado = True; u.is_staff = u.is_superuser = staff; u.save()
"
```

## Referencias del repo

- Convenciones de código: skill `poolshop-convenciones` y `docs/code-standards.md`.
- Recorridos en navegador: skill `poolshop-e2e`.
- Tests del front: `node --test` sobre módulos puros de `src/lib/*.js` (sin DOM);
  la lógica nueva va en un `.js` puro para poder testearla.
