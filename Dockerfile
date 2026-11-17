FROM node:22-slim AS front
WORKDIR /app/frontend
COPY frontend/package*.json frontend/.npmrc ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 DEBUG=false
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=front /app/frontend/build /app/frontend/build
RUN SECRET_KEY=build python manage.py collectstatic --noinput
# El check crea MEDIA_ROOT/PRIVATE_MEDIA_ROOT si faltan y avisa en el log si no se
# pueden escribir (sin frenar el arranque: el resto de la app funciona igual).
# migrate, check --deploy, la carga opcional de la demo (POBLAR_DEMO=true) y gunicorn.
CMD ["sh", "arranque.sh"]
