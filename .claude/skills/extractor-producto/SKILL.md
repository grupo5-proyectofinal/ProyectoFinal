---
name: extractor-producto
description: Cómo mantener y extender el autocompletado de productos desde un enlace de tienda en PoolShop (backend/pools/producto.py) — agregar soporte para una tienda nueva (MercadoLibre, Amazon, VTEX, Tiendanube, Shopify…), arreglar un link que "no autocompleta", leer precios en es-AR, y no romper las protecciones anti-SSRF. Usala siempre que alguien diga que el autocompletado o la vista previa del link falla, o pida soportar una tienda, aunque no mencione el archivo.
---

# Autocompletado de producto desde el enlace

`POST /api/v1/pools/previsualizar-enlace/` recibe el link que pega el creador
y devuelve nombre, precio por unidad, imagen y descripción para autocompletar
"Crear pool". Todo vive en `backend/pools/producto.py`. La vista es
`PoolViewSet.previsualizar_enlace` en `pools/views.py`, y el front lo usa
desde `frontend/src/routes/pools/nuevo/+page.svelte` y `lib/producto.js`.

## Cómo funciona

1. `limpiar_enlace(url)` saca el tracking (`utm_*`, `tracking_id`, `fbclid`,
   fragmento…). La misma función limpia `Pool.enlace` al guardar, así que hay
   un solo criterio.
2. `leer_enlace(url)` devuelve `{"datos": {...} | None, "motivo": str | None,
   "aviso": str | None}` y nunca lanza.
   - **Extractores por API**, antes de bajar HTML: hoy MercadoLibre
     (`/items/MLA…` de la API pública). Si la API responde 401/403 se sigue con
     el HTML.
   - **Extractores sobre el HTML**, en `extraer_datos`, en este orden: JSON-LD
     `Product`, microdatos `itemprop`, Open Graph y `product:price:amount`, los
     datos embebidos de VTEX y Tiendanube, el precio y título de Amazon y, por
     último, `<title>`. Se toma el primero que trae cada dato.
3. `motivo` explica por qué no hay datos. El front muestra el texto de
   `MENSAJES_MOTIVO`, en es-AR:

   | Motivo | Cuándo |
   |---|---|
   | `bloqueado` | La tienda devolvió 403, 429 o 503, o una página de captcha |
   | `no_disponible` | Timeout, error de red o 5xx |
   | `no_permitido` | El destino no pasa el anti-SSRF |
   | `no_html` | El enlace no es una página HTML |
   | `sin_datos` | La página no publica los datos |

4. `aviso`: hay datos pero algo no cierra. Por ejemplo, el precio está en otra
   moneda: no se completa y se avisa que hay que cargarlo en pesos.

## Agregar una tienda

1. Guardá un HTML real (o recortado a lo relevante) en
   `backend/pools/fixtures_producto/<tienda>.html`. Los tests no salen a
   internet: CI y los contenedores no tienen red garantizada, y las tiendas
   cambian el HTML.
2. Si la tienda publica JSON-LD u Open Graph, probablemente ya funcione:
   escribí primero el test con el fixture.
3. Si no, sumá la lectura en `_Metadatos` (para datos que van en atributos o
   texto de un tag) o una función `_datos_<tienda>(html)` (para JSON embebido
   en un `<script>`). Enchufala en `extraer_datos` respetando el orden: lo más
   específico y confiable primero.
4. Precios: pasalos siempre por `normalizar_precio`. Entiende `1.234,56`,
   `1,234.56`, `$ 12.500` y `12500`, y devuelve `Decimal` o `None`. Si la tienda
   publica la moneda, devolvela en `moneda`: lo que no es `ARS` no se autocompleta.
5. Test en `backend/pools/tests.py`, cerca de `test_extraer_datos_*`, leyendo
   el fixture con `Path(__file__).parent / "fixtures_producto" / ...`.

## Anti-SSRF: lo que no se toca

La URL la elige el usuario: sin estas protecciones, el servidor podría
pegarle a servicios internos (metadata de la nube en `169.254.169.254`,
Postgres, el admin).

- Solo `http`/`https` a los puertos 80/443 (`_validar_destino`). Cada
  redirección se revalida (`_RedireccionSegura`), con un máximo de
  `MAX_REDIRECCIONES`.
- **IP pública** antes de conectar, y otra vez sobre la IP a la que realmente
  se conectó (`_ConexionVerificada`). Esto cierra el DNS rebinding: un dominio
  que resuelve a una IP pública al validar y a `127.0.0.1` al conectar. Detrás
  de un proxy HTTP el chequeo lo hace el proxy, y la conexión directa no se usa.
- Timeout corto y tope de bytes. El HTML se trunca en `MAX_HTML`, porque los
  metadatos están al principio. Las imágenes se rechazan si superan `MAX_IMAGEN`.
- Fail-soft: cualquier error termina en `motivo` y nunca en un 500.

Cualquier cambio en `_descargar`, en los handlers o en `_validar_destino` lleva
un pase de seguridad: probá `test_destinos_no_permitidos` y sumá el caso nuevo.

## Probarlo a mano

```bash
cd backend && . .venv/bin/activate && python manage.py shell -c "
from pools.producto import leer_enlace; import pprint
pprint.pp(leer_enlace('https://articulo.mercadolibre.com.ar/MLA-123-x-_JM'))"
```

Desde un contenedor sin salida a internet, o detrás de un proxy que no deja
pasar la tienda, esperá `motivo: no_disponible`. Eso es lo correcto.
