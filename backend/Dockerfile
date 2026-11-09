FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Espera a la base (con reintentos y tiempo máximo), migra y levanta el servidor.
# Ver entrypoint.sh: evita caerse si el DNS de `db` todavía no está listo.
CMD ["sh", "/app/entrypoint.sh"]
