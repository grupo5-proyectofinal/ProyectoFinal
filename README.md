# PoolShop

Compras grupales por pool. Backend Django 6 + DRF, frontend SvelteKit (SPA), PostgreSQL 17 en Docker.

## Requisitos

- Python 3.14, Docker
- Node 20.19 o superior (recomendado 22.12+/24). El front lo exige Vite 8: `frontend/package.json` declara `engines.node` y `frontend/.npmrc` usa `engine-strict`, así que `npm install` con un Node más viejo falla con el mensaje de engines.

## Puesta en marcha

### 1. Base de datos

```powershell
copy .env.example .env   # completar POSTGRES_PASSWORD
docker compose up -d
```

Si ya hay un Postgres local en `5432`, poné `POSTGRES_PORT=5433` en `.env` (compose y Django usan esa misma variable).

### 2. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

API en `http://localhost:8000/api/v1/` (disponible a partir de Fase 1). Media en `backend/media/`.

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

App en `http://localhost:5173`. El dev server proxea `/api` y `/media` a `http://localhost:8000`.
