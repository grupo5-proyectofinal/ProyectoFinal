<!-- base-commit: cca8686fa11cef980b3a65f4536a45e166608765 -->
<!-- generated: 2026-10-12 -->

# Code Standards

Convenciones reales de PoolShop (Django 6 + DRF / SvelteKit Svelte 5). Extraídas del código, no inventadas.

## Forbidden Patterns

**Nunca texto visible al usuario ni mensajes de error en inglés** — todo va en es-AR, incluso los que DRF genera solo (el throttle 429 responde en inglés: el front lo reemplaza).

```python
# BAD — rompe el idioma del producto y los tests que comparan mensajes
raise ValidationError("Pool is not open.")

# GOOD — desde backend/pools/views.py:235; los tests y el front dependen de esto
raise ValidationError({"cantidad": f"El mínimo por integrante es {pool.min_por_integrante}."})
```

```js
// GOOD — frontend/src/lib/recuperacion.js:37; el 429 de DRF no trae es-AR: se traduce
if (error?.status === 429) return 'Demasiados intentos. Esperá unos minutos y volvé a probar.';
```

**Nunca `fetch` directo en páginas o componentes** — se pierde `ApiError`, el header `Authorization` y el armado de query.

```js
// BAD — token duplicado, errores sin mapear, query armada a mano
const r = await fetch(`/api/v1/pools/${id}/mensajes/`, { headers: auth() });

// GOOD — desde frontend/src/lib/PanelChat.svelte:66; `api` centraliza auth, query y errores
const datos = await api(`/pools/${id}/mensajes/`, { query: { desde: 0, limit: LIMITE_INICIAL } });
```

**Nunca exponer PII del miembro fuera del detalle al creador** — `telefono`/`mensaje` de una membresía solo salen con `exponer_datos_miembros=True` y para el creador del pool; en los eventos del historial, `datos` nunca lleva PII.

```python
# GOOD — backend/pools/serializers.py:64; la regla vive en el serializer, no en cada caller
def to_representation(self, instance):
    data = super().to_representation(instance)
    if not self._datos_visibles(instance):
        data.pop("telefono", None)
        data.pop("mensaje", None)
    return data
```

**Nunca mutar un pool sin lock** — toda acción que cambia cantidad/estado usa `transaction.atomic()` + `_bloqueado(pk)` (`select_for_update`); el queryset anotado no entra en el lock.

```python
# GOOD — backend/pools/views.py:264; unirse: lock + validaciones + update en una transacción
with transaction.atomic():
    pool = self._bloqueado(pk)
    self._rechazar_vencido(pool)
```

**Nunca N+1 en vistas DRF** — el queryset estándar trae `select_related` + `prefetch_related` + `annotate`, y el serializer reusa la anotación.

```python
# BAD — el serializer toca categoria/creador/memberships por pool
Pool.objects.all()

# GOOD — desde backend/pools/views.py:100; el serializer reusa `integrantes` (serializers.py:161)
Pool.objects.select_related("categoria", "creador")
    .prefetch_related("imagenes", Prefetch("memberships", ...))
    .annotate(integrantes=Count("memberships"))
```

## Code Examples

### Formulario Svelte con errores por campo

```svelte
<!-- DO — desde frontend/src/routes/login/+page.svelte:22; ApiError → fieldErrors → aria -->
catch (error) {
    if (error.status === 401) {
        general = 'Email o contraseña incorrectos.';
    } else {
        errors = fieldErrors(error.data);
        general = errors.detail || 'No se pudo iniciar sesión.';
        delete errors.detail;
    }
}
```

```svelte
<!-- DON'T — este proyecto no usa stores imperativos ni maneja errores a mano -->
<script>
    import { writable } from 'svelte/store';
    const email = writable('');
    async function enviar() { await fetch(...); alert('error'); } // sin mapeo de campos
</script>
```

### Validación de dominio en el serializer

```python
# DO — desde backend/pools/serializers.py:202; regla de objeto con la clave del campo
def validate(self, attrs):
    ...
    raise serializers.ValidationError({campo: "El comprometido supera la cantidad total."})

# DON'T — validar en la vista sin serializer ni mensaje por campo
if data["cantidad_total"] < pool.cantidad_creador:
    return Response({"error": "bad total"}, status=400)
```

### Fetch en `$effect` con contador de generación

```js
// DO — desde frontend/src/routes/pools/+page.svelte:88; la respuesta vieja se descarta
async function cargar(tabActivo, params) {
    const actual = ++pedido;
    cargando = true;
    try {
        const r = await api(endpointDeTab(tabActivo), { query });
        if (actual !== pedido) return; // llegó tarde: otra carga la reemplazó
        data = r;
    } finally {
        if (actual === pedido) cargando = false;
    }
}

// DON'T — dos $effect pueden pisarse: la respuesta lenta sobreescribe la nueva
$effect(() => { api(...).then((r) => (data = r)); });
```

## Error Handling

**Backend:** las reglas de negocio lanzan excepciones DRF con mensaje es-AR y clave de campo; las vistas quedan finas.

```python
# backend/pools/views.py:233 — el error nombra el campo para que el front lo mapee
def _validar_cantidad(self, pool, cantidad, disponible):
    if cantidad < pool.min_por_integrante:
        raise ValidationError({"cantidad": f"El mínimo por integrante es {pool.min_por_integrante}."})
```

**Integraciones externas (HTTP/SMTP) fail-soft:** se loguea y se sigue; un servicio caído nunca tumba el endpoint.

```python
# backend/pools/geocoding.py:63 — red, timeout, HTTP o JSON roto → None (sin excepción)
except (OSError, ValueError, http.client.HTTPException) as error:
    logger.warning("No se pudo geocodificar %r: %s", consulta, error)
    return None
```

**Frontend:** `ApiError` + `fieldErrors` es el único camino de errores de API; los errores de acción se resuelven con `mensajeError`; el 401 limpia la sesión sola.

```js
// frontend/src/lib/eliminacion.js:42 — detalle del API o aviso de red, siempre es-AR
export function mensajeError(error) {
    ...
    return 'No se pudo conectar con el servidor. Revisá tu conexión e intentá de nuevo.';
}

// frontend/src/lib/session.svelte.js:59 — 401 en loadMe → logout sin intervención de la página
if (error instanceof ApiError && error.status === 401) logout();
```

Los errores generales se anuncian con `role="alert"` y los avisos de estado con `role="status"` (`PanelChat.svelte:175-197`).

## Imports & Dependency Direction

- Backend: `urls → views → serializers → models`. Los modelos no importan vistas ni serializers. Entre apps se importa `pools.models` cuando hace falta (`users/serializers.py:12`), pero a `User` siempre se lo obtiene con `get_user_model()` (`pools/serializers.py:3`), nunca con un import directo de `users.models`.
- Orden de imports Python: stdlib → django → DRF/terceros → locales, con línea en blanco entre grupos (`pools/serializers.py:1-6`). Ruff cubre el lint (`backend/pyproject.toml:5-6`); las migraciones están excluidas y `RUF012` se ignora por el `Meta` de Django.
- Frontend: `routes/` y componentes importan de `$lib/`; dentro de `$lib` los módulos puros se importan entre sí en relativo (`recuperacion.js:8` → `./eliminacion.js`) y jamás importan `api.js` ni runes (`recuperacion.js:4`). Los módulos con runes (`*.svelte.js`) importan puros, nunca al revés (`admin.svelte.js:4-6`).
- No crear barrels: `$lib/index.js` es el placeholder del scaffold y no se usa.

## Testing Patterns

**Backend:** pytest + pytest-django con funciones planas, sin clases. Fixtures `api_client`, `user`, `categoria`, `pool`; builders con overrides; URLs con `reverse("pool-list")`; autenticación con `force_authenticate`, salvo los tests de auth que usan el JWT real.

```python
# backend/pools/tests.py:86 — un builder por app; overrides para cada caso
def payload(categoria, **overrides):
    data = {"titulo": "Pool de yerba", "fecha_caducidad": ..., "ciudad": "Cordoba"}
    data.update(overrides)
    return data
```

```python
# backend/users/tests.py:68 — login real cuando el test es de auth
def authenticate(api_client, user):
    token = login(api_client, user.email, PASSWORD).data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
```

**Frontend:** `node --test tests/*.test.js` solo para módulos puros de `$lib` con `node:assert/strict`; los componentes se validan compilándolos y renderizándolos server-side, no con DOM. Cada módulo puro nuevo lleva su test espejo.

```js
// frontend/tests/identidad.test.js:24 — ejecuta el componente real y mira el render
const { body } = await logoRender({ class: 'marca--cabecera' });
assert.match(body, /stroke="currentColor"/);
```

Los nombres de test citan el requisito del plan (`DW-<fase>.<n>`), p. ej. `frontend/tests/chat.test.js:27`.

## Naming Conventions

**Dominio y todo lo visible al usuario en español; framework/infra en inglés.**

- Campos y métodos de dominio: `titulo`, `fecha_caducidad`, `telefono`, `mensaje`; `vencio`/`caducar` (`models.py:98`, `models.py:104`), `_solo_creador`/`_solo_abierto` (`views.py:197`, `views.py:201`).
- Modelos de dominio en español cuando el término no tiene traducción natural: `SolicitudEliminacion` (`models.py:133`), `VotoEliminacion` (`models.py:155`), `Mensaje` (`models.py:212`), `EventoPool` (`models.py:236`).
- Clases de framework/CRUD en inglés: `PoolViewSet` (`views.py:89`), `MembershipSerializer` (`serializers.py:47`), `AdminUserListView` (`users/views.py:117`).
- Rutas y acciones de API en español: `mios`, `unidos`, `unirse`, `salir`, `mi-membresia`, `historial`, `mensajes`, `eliminacion` (`views.py:247-435`).
- Frontend: módulos puros en español (`pestanas.js`, `eliminacion.js`, `confianza.js`); módulos con runes con sufijo `.svelte.js` (`session.svelte.js`, `toast.svelte.js`, `admin.svelte.js`); componentes en PascalCase (`PoolCard.svelte`, `MiniPerfil.svelte`, `PanelChat.svelte`).
- CSS: BEM en español con `__` y `--`: `.chat__lista` (`PanelChat.svelte:211`), `.mini-perfil__dato` (`MiniPerfil.svelte:77`), `.cabecera__interior` (`+layout.svelte:262`); tokens `--e-4`, `--texto-sm`, `--radio-sm`, `--tinte-azul` (`app.css:21-95`).
- Tests backend: `test_<accion>_<caso>` (`test_unirse_sobre_disponible_400`, `pools/tests.py:472`).

## File Organization

```
backend/
  users|pools/                # una app por dominio: models.py, serializers.py, views.py, urls.py, tests.py
  pools/management/commands/  # tareas para cron: expirar_pools.py
  config/                     # settings.py + urls.py raíz; media/ para uploads (solo DEBUG)
frontend/
  src/routes/                 # SvelteKit file-based; rutas en español (/pools/[id], /admin/usuarios, /recuperar, /restablecer)
  src/lib/                    # *.svelte componentes · *.js puros · *.svelte.js con runes
  src/app.css                 # sistema de diseño: tokens, reset, componentes base
  tests/                      # <modulo>.test.js espeja $lib/<modulo>.js
```

Un módulo puro nuevo va en `$lib/<feature>.js` con su test en `tests/<feature>.test.js` (ej. `chat.js` ↔ `chat.test.js`); la página o componente que lo usa queda fino. Las categorías se siembran por data migration (`pools/migrations/0002_seed_categories.py`); `Category` con `on_delete=PROTECT`.

## Technology Decisions

- **SPA sin SSR:** `export const ssr = false` (`routes/+layout.js:1`); adapter-static con fallback `index.html` (`vite.config.js:12`).
- **Svelte 5 runes forzado** por `compilerOptions.runes` (`vite.config.js:8`) — `$state`/`$derived`/`$effect`/`$props`, sin stores.
- **Auth:** SimpleJWT; login por email (`users/urls.py:16-17`); tokens en localStorage `poolshop.session` (`session.svelte.js:3`); las llamadas usan solo `access` y el 401 hace logout (`session.svelte.js:59`). El reset responde neutro (sin enumeración) con throttle 5/min (`users/views.py:76-83`, `settings.py:194-196`).
- **Paginación:** DRF `PageNumberPagination` de 12 (`settings.py:192-193`); el front navega por query params (`pools/+page.svelte:113-119`).
- **Chat por polling incremental:** cursor `desde` + `limit` + `hay_mas` (`views.py:371-386`), intervalo 5 s con pestaña oculta en pausa (`PanelChat.svelte:50-56`), dedupe por id (`chat.js:44-47`).
- **Geocodificación server-side** (Nominatim): fail-soft, 1 pedido/s, 6 decimales (`geocoding.py:14-18`); el cliente nunca manda coords (read-only en `serializers.py:149-157`).
- **Expiración perezosa:** `expirar_vencidos()` en `get_queryset` (`views.py:98`) + comando `expirar_pools`; cancelación con UPDATE condicional para no pisar otra transición (`models.py:104-120`).
- **Email:** Django 6 `MAILERS`: consola por defecto, SMTP si `.env` define `EMAIL_HOST` (`settings.py:142-165`). Un solo `.env` en la raíz compartido con docker-compose (`settings.py:21-22`).
- **Leaflet** es el único dep de runtime; el mapa se limpia en el cleanup del `$effect` (`MapaPool.svelte:13-23`).

## Exemplar Files

**`backend/pools/views.py`** — permisos por acción, transacciones con `select_for_update`, errores es-AR por campo, acciones custom (`unirse`, `mensajes`, `eliminacion`), conteos por lote.

**`backend/pools/confianza.py`** — módulo de heurísticas puras: contrato estable, la entrada externa nunca lanza.

**`frontend/src/lib/chat.js` + `frontend/tests/chat.test.js`** — módulo puro + test espejo con `node --test`.

**`frontend/src/routes/pools/[id]/+page.svelte`** — paneles por rol, effects con clave derivada, `fieldErrors`, toasts.

**`frontend/src/routes/pools/+page.svelte`** — estado dirigido por URL (tabs, filtros, paginación) y guard contra respuestas viejas.

**`frontend/src/lib/api.js` + `session.svelte.js`** — `ApiError`, ciclo de tokens, 401 → logout.
