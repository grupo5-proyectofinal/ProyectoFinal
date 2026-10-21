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

## Correos

La app manda dos tipos de correo, todos en HTML con el diseño de PoolShop y una versión en texto plano:

- **De cuenta (siempre se envían):** confirmación de email al registrarse, bienvenida al confirmar, restablecer contraseña y aviso de contraseña cambiada. Sin confirmar el email no se puede iniciar sesión.
- **Notificaciones (según la configuración de cada usuario en `/notificaciones`):** cambios de estado, mensajes del chat, nuevos miembros y la confirmación al unirse a un pool. Vienen activadas por defecto y cada correo trae un enlace para darse de baja sin iniciar sesión.

Sin configuración, los mails se imprimen en la consola de `runserver` (ahí podés copiar los links de confirmación). Para enviarlos de verdad desde la cuenta de PoolShop en Gmail, completá en `.env`:

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=<cuenta>@gmail.com
EMAIL_HOST_PASSWORD=<contraseña de aplicación de 16 letras>
DEFAULT_FROM_EMAIL=PoolShop <<cuenta>@gmail.com>
FRONTEND_URL=http://localhost:5173
```

Gmail no acepta la contraseña normal por SMTP: activá la verificación en 2 pasos en la cuenta y generá una *contraseña de aplicación* en https://myaccount.google.com/apppasswords. Gmail tampoco admite `_` en las direcciones (por ejemplo `poolshop.notificaciones@gmail.com` sí, `poolshop_notificaciones@gmail.com` no). `FRONTEND_URL` es la dirección que va en los links de los correos: cambiala si la app corre en otro host. Si el envío falla, la acción igual se completa y el error queda en el log.
