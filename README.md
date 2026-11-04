# PoolShop

Compras grupales por pool. Backend Django 6 + DRF, frontend SvelteKit (SPA), PostgreSQL 17 en Docker.

## Requisitos

- Python 3.13 o superior (las imágenes de Docker usan 3.13), Docker
- Node 20.19 o superior (recomendado 22.12+/24). El front lo exige Vite 8: `frontend/package.json` declara `engines.node` y `frontend/.npmrc` usa `engine-strict`, así que `npm install` con un Node más viejo falla con el mensaje de engines. Con nvm: `nvm use` dentro de `frontend/` (lee `.nvmrc`).

## Puesta en marcha

### Todo con un solo comando (Docker)

```powershell
copy .env.example .env   # completar SECRET_KEY y POSTGRES_PASSWORD
docker compose up --build
```

Levanta la base, el backend (aplica las migraciones solo) y el frontend: app en `http://localhost:5173`, API en `http://localhost:8000/api/v1/`. Los cambios en el código se recargan solos. Para el mail real, completá las variables `EMAIL_*` en `.env` (ver "Correos").

### Sin Docker para backend y frontend

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

## Tests

```powershell
cd backend
pytest            # necesita Postgres levantado y SECRET_KEY en .env
ruff check .
cd ..\frontend
npm test          # node --test sobre src/lib
npm run build
```

Lo mismo corre en GitHub Actions (`.github/workflows/ci.yml`) en cada PR y en cada push a `main`, más `makemigrations --check` para que no se escape un cambio de modelo sin su migración.

## Tareas periódicas

`python manage.py tareas_periodicas` corre la caducidad de pools, el recordatorio de recepción (cada 3 días a quien no confirmó que recibió el producto) y la limpieza de sesiones vencidas. En Docker lo hace el servicio `scheduler` cada hora; en Render, el cron job `poolshop-tareas` de `render.yaml`. Sin eso, los pools vencidos igual se cancelan al consultar la API, pero no llegan los avisos por mail.

## Sesión

El login dura 30 minutos por pedido y se renueva solo mientras la app esté abierta (hasta 14 días sin volver a ingresar). Se ajusta con `JWT_ACCESS_MINUTOS` y `JWT_REFRESH_DIAS`. Si la sesión vence, la app avisa "Tu sesión expiró", lleva al login y vuelve a la misma página; lo cargado en "Crear pool" queda guardado como borrador.

## Imágenes

Se aceptan JPG, PNG, HEIC (iPhone) y WEBP; lo que no es JPG/PNG se convierte a JPG. Las URLs de `/media/` son relativas, así que las imágenes cargan igual entrando por `localhost`, por la IP de la red (`http://192.168.x.x:5173`) o por el dominio. Al arrancar, `manage.py check` avisa si `MEDIA_ROOT` no se puede escribir (no hace falta `chmod 777`: alcanza con que la carpeta sea del usuario que corre Django). En Render las imágenes viven en el disco persistente (`/data`): sin disco se borran en cada deploy.

## Mayoristas y comparador

- El directorio de `/mayoristas` no trae datos: el equipo lo carga desde `/admin/mayoristas` o con un CSV (`nombre, sitio_url, rubros, provincia, ciudad, compra_minima, envio, medios_pago, verificado`):

  ```powershell
  python manage.py importar_mayoristas mayoristas.csv
  ```

- El comparador convierte monedas con el **tipo de cambio** que se carga en `/admin/mayoristas` → "Parámetros del comparador" (arranca en 0 = no cargado: las ofertas en dólares quedan sin total hasta cargarlo). Las alícuotas de importación son valores de referencia y la app muestra la aduana como estimación.

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

Para verificar la cuenta: `python manage.py probar_correo tu@email.com` (muestra el error completo si algo falla). En Render las variables `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD` se cargan en el panel del servicio.

Gmail no acepta la contraseña normal por SMTP: activá la verificación en 2 pasos en la cuenta y generá una *contraseña de aplicación* en https://myaccount.google.com/apppasswords. Gmail tampoco admite `_` en las direcciones (por ejemplo `poolshop_notificaciones@gmail.com` no es válida). `FRONTEND_URL` es la dirección que va en los links de los correos: cambiala si la app corre en otro host. Si el envío falla, la acción igual se completa y el error queda en el log.

## Documentación

En `docs/` están el ERS, la planificación, la arquitectura y la documentación de cada release (`ReleaseN-PoolShop.docx` y su presentación en PDF). El Release 4 cubre la Iteración 3 (feedback "Funcionalidades pendientes"). Los casos de prueba en texto están en `docs/casos-de-prueba.md` y el estado del trabajo en `docs/kanban.md`.
