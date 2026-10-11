<!-- base-commit: 1f5f37eceb869e917e0c9ed17df52fedbbaf400c -->
<!-- generated: 2026-10-08 -->

# Code Standards

Convenciones reales de PoolShop (Django 6 + DRF / SvelteKit Svelte 5). Extraídas del código, no inventadas.

## Forbidden Patterns

**Nunca texto de UI o mensajes de error en inglés** — todo lo que ve el usuario y toda `ValidationError` va en es-AR.

```python
# BAD — rompe el idioma del producto y los tests que comparan mensajes
raise ValidationError("Pool is not open.")

# GOOD — de backend/pools/views.py:146; los tests y el front dependen de esto
raise ValidationError("El pool no está abierto.")
```

**Nunca `fetch` directo en páginas o componentes** — se pierde el manejo de `ApiError`, el header `Authorization` y el armado de query.

```js
// BAD — token duplicado, errores sin mapear, query armada a mano
const r = await fetch(`/api/v1/pools/?q=${q}`, { headers: auth() });

// GOOD — desde frontend/src/routes/pools/+page.svelte:55; `api` centraliza auth, query y errores
data = await api('/pools/', { query: Object.fromEntries(params) });
```

**Nunca N+1 en vistas DRF** — `PoolViewSet.get_queryset` es el estándar: select_related + prefetch_related + annotate.

```python
# BAD — serializer toca categoria/creador/memberships por pool
Pool.objects.all()

# GOOD — desde backend/pools/views.py:57; el serializer reusa la anotación `integrantes`
Pool.objects.select_related("categoria", "creador")
    .prefetch_related("imagenes", "memberships__usuario")
    .annotate(integrantes=Count("memberships"))
```

**Nunca commitear `.env` ni hardcodear secretos** — `config/settings.py:29` lee `os.environ["SECRET_KEY"]`; el `.env` vive en la raíz y está en `.gitignore`.

## Code Examples

### Formulario Svelte con errores por campo

```svelte
<!-- DO — desde frontend/src/routes/login/+page.svelte:13; ApiError → fieldErrors → aria -->
<script>
	async function enviar(event) {
		event.preventDefault();
		try {
			await login(email, password);
			goto(resolve('/'));
		} catch (error) {
			if (error.status === 401) general = 'Email o contraseña incorrectos.';
			else { errors = fieldErrors(error.data); general = errors.detail; delete errors.detail; }
		}
	}
</script>
<input bind:value={email} aria-invalid={errors.email ? 'true' : undefined}
	aria-describedby={errors.email ? 'email-error' : undefined} />
{#if errors.email}<p class="error" id="email-error">{errors.email}</p>{/if}
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
# DO — desde backend/pools/serializers.py:113; separa reglas de campo y de objeto
def validate(self, attrs):
    total = attrs.get("cantidad_total", getattr(self.instance, "cantidad_total", None))
    if total is not None and comprometido > total:
        raise serializers.ValidationError({"cantidad_total": "El comprometido supera la cantidad total."})
    return attrs

# DON'T — validar en la vista sin serializer ni mensaje por campo
if data["cantidad_total"] < pool.cantidad_creador:
    return Response({"error": "bad total"}, status=400)
```

## Error Handling

**Backend:** las reglas de negocio lanzan excepciones DRF con mensaje es-AR y clave de campo; las vistas quedan finas.

```python
# backend/pools/views.py:114 — el error nombra el campo para que el front lo mapee
def _validar_cantidad(self, pool, cantidad, disponible):
    if cantidad < pool.min_por_integrante:
        raise ValidationError({"cantidad": f"El mínimo por integrante es {pool.min_por_integrante}."})
```

**Frontend:** `ApiError` + `fieldErrors` es el único camino de errores de API; el error general va en `role="alert"`. El 401 en `loadMe` limpia la sesión sola (`session.svelte.js:59`).

```js
// frontend/src/lib/api.js:44 — nunca devolver response cruda
if (!response.ok) throw new ApiError(response.status, data);
```

## Imports & Dependency Direction

- Backend: `urls → views → serializers → models`. Los modelos no importan vistas; entre apps se usa `get_user_model()` (ver `pools/serializers.py:6`), nunca un import directo de `users.models`.
- Frontend: `routes/` y componentes importan desde `$lib/`; lo compartido vive en `$lib` (`api.js`, `session.svelte.js`, `formato.js`, `estados.js`). No crear barrels: `$lib/index.js` es el placeholder del scaffold y no se usa.
- Orden de imports observado (Python): stdlib → django → DRF/terceros → locales, con línea en blanco entre grupos (ver `pools/views.py:1-14`). Ruff (`backend/pyproject.toml`) cubre el lint; las migraciones están excluidas.

## Testing Patterns

**Backend:** pytest + pytest-django con funciones planas, sin clases. Fixtures `db`, `api_client`, `user`, `categoria`; builders con overrides (`register_payload()`, `payload(categoria, **overrides)`); URLs con `reverse("pool-list")`.

```python
# backend/pools/tests.py:59 — un builder por app, overrides para cada caso
def payload(categoria, **overrides):
    data = {"titulo": "Pool de yerba", "fecha_caducidad": ..., "ciudad": "Cordoba"}
    data.update(overrides)
    return data
```

**Frontend:** `node --test` (`npm test`) solo para helpers puros de `$lib` (`formato.js`, `estados.js`) con `node:assert/strict`. No hay tests de DOM.

## Naming Conventions

**Dominio y todo lo visible al usuario en español; framework/infra en inglés.**

- Campos y métodos de dominio: `titulo`, `fecha_caducidad`, `cantidad_creador`, `filtrar_q`, `_solo_creador` (`backend/pools/`).
- Rutas y acciones de API: `/pools/nuevo`, `/mis-pools`, `/unidos`, acciones `mios`, `unidos`, `unirse`, `salir`, `mi-membresia` (`backend/pools/views.py`).
- Clases DRF/Django en inglés: `PoolViewSet`, `RegisterSerializer`, `CategoryViewSet`.
- CSS: BEM en español con `__` y `--`: `.cabecera__interior`, `.btn.btn--primario`, `.menu-movil__enlace`; tokens `--e-4`, `--texto-sm`, `--radio-sm` (`frontend/src/app.css`).
- Tests: `test_<accion>_<caso>` (`test_register_duplicate_email`, `test_crear_pool_requiere_auth`).

## File Organization

```
backend/
  users|pools/        # una app por dominio: models.py, serializers.py, views.py, urls.py, tests.py
  config/             # settings.py + urls.py raíz; media/ para uploads (solo DEBUG)
frontend/
  src/routes/         # SvelteKit file-based; rutas en español (/pools/[id], /mis-pools, /unidos)
  src/lib/            # componentes (PoolCard.svelte) y módulos compartidos
  src/app.css         # sistema de diseño: tokens, reset, componentes base
  tests/unit.test.js  # tests de helpers puros
```

## Technology Decisions

- **SPA sin SSR:** `export const ssr = false` en `src/routes/+layout.js`; adapter-static con fallback `index.html`.
- **Svelte 5 runes forzado** por `compilerOptions.runes` en `vite.config.js` — `$state`/`$derived`/`$effect`, sin stores.
- **Auth:** SimpleJWT; `User.USERNAME_FIELD = "email"` (login con email); tokens en localStorage bajo `poolshop.session`.
- **Paginación:** DRF `PageNumberPagination` de 12; el front navega con query params, no con estado local.
- **Email dev:** `MAILERS` con `console.EmailBackend` (`config/settings.py:139`).
- **Un solo `.env` en la raíz** compartido por Django y docker-compose (`load_dotenv(BASE_DIR.parent / ".env")`).
- **Categorías por data migration** (`pools/migrations/0002_seed_categories.py`); `Category` con `on_delete=PROTECT`.

## Exemplar Files

**`backend/pools/views.py`** — permisos por acción, transacciones con `select_for_update`, errores es-AR por campo, actions custom (`unirse`, `mi-membresia`).

**`backend/pools/serializers.py`** — campos computados (`disponible`, `mi_cantidad`), validación de campo vs. objeto, `read_only_fields` como contrato.

**`frontend/src/routes/pools/+page.svelte`** — filtros dirigidos por URL, `$effect` + `page.url`, estados de carga/error/vacío, skeleton.

**`frontend/src/routes/login/+page.svelte`** — formulario con `fieldErrors`, atributos ARIA, spinner en submit.

**`frontend/src/lib/api.js` + `session.svelte.js`** — `ApiError`, ciclo de vida de tokens, 401 → logout.
