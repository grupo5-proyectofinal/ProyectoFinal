# Plan: Pools — ciclo de vida y ubicación

**Created:** 2026-10-08
**Status:** complete
**Started:** 2026-10-08 19:57
**Completed:** 2026-10-09 09:53
**Duration:** 2026-10-08 19:57 → 2026-10-09 09:53
**Complexity:** complex
**Review cadence:** 2

---

## Context

PoolShop tiene la base funcionando (usuarios, pools, búsqueda, rediseño UI), pero queda todo el backlog confirmado del usuario: "Olvidé mi contraseña" + correo, backoffice ABM de usuarios, nombre del usuario logueado, categorías (alta de "Higiene personal" / baja de "Alimentos"), ubicación del pool con mapa, caducidad de pools abiertos, pestaña de pools unidos, confianza al unirse (datos extra + perfil visible al creador), análisis propio del enlace de tienda, historial de cambios, eliminación de pool con aprobación, estados, chat entre integrantes e identidad visual (logo/colores) + entorno (Node ≥20).

Decisiones fijadas con el usuario: Leaflet/OpenStreetMap para mapas; análisis del enlace con lógica propia (sin servicios externos); SMTP configurable con consola en dev; backoffice propio en la app; flujo completo de eliminación del ERS; unión con datos extra y perfil visible al creador; logo a medida; se mantiene la línea visual actual.

La planificación se dividió en 3 planes verticales encadenados (≤7 fases c/u): **P1 Pools — ciclo de vida y ubicación** (este), **P2 Cuentas y administración**, **P3 Confianza, social e identidad**. Orden de build: P1 → P2 → P3.

## Constraints

- Stack actual, sin servicios pagos: Django 6 + DRF + SimpleJWT; SvelteKit (Svelte 5 runes, `ssr=false`); Postgres 17 en Docker; API `/api/v1` con mensajes es-AR; paginación page-number (12).
- No romper flujos ni casos de prueba existentes (PS-*); actualizar los tests afectados.
- Sin secretos en el repo: todo por `.env`.
- Tests sin acceso a red (servicios externos mockeados).
- La eliminación con aprobación exige unanimidad de los miembros (ERS 2.3/3.7) y es hard delete; el creador inicia y no vota.
- Geocodificación: Nominatim público (≤1 req/s) solo al guardar el pool, nunca en lectura; el guardado no se bloquea si falla.
- "Vencido" = `fecha_caducidad < hoy` (timezone America/Argentina/Buenos_Aires); el pool sigue válido todo el día de su fecha.
- Ejecución secuencial: las fases comparten áreas de código; no se asume paralelismo entre fases (opencode no deriva waves).

## Chosen Approach

**3 planes verticales por dominio.** Este es el Plan 1: agrupa todo lo que toca el modelo y el ciclo de vida del pool, para exponer temprano el riesgo de migraciones y reglas sobre datos existentes. **Fallback:** P2 no depende de P1; P3 sí (su fase de historial registra eventos de los flujos creados acá).

## Rejected Approaches

- **Por capas (datos/API primero):** concentra la integración front↔back al final; sin entregas verificables end-to-end.
- **Demo-first:** pospone los cambios que tocan datos existentes (migraciones, caducidad, eliminación) y aumenta el riesgo de retrabajo.

---

## Implementation Phases

### Phase 1: Categorías
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `cc-quality-practices`
**Gate:** Standard

**Goal:** Actualizar el catálogo de categorías: alta de "Higiene personal" y baja de "Alimentos" reasignando sus pools a "Otros", en una migración de datos con reverse y tests actualizados.

**Scope:**
- IN: migración nueva (crear "Higiene personal", reasignar pools de "Alimentos" a "Otros", borrar "Alimentos"); test de migración; actualizar `test_categorias_sembradas`.
- OUT: UI de categorías (consume la API sin cambios); documentos de casos de prueba históricos.

**Constraints:** `Otros` ya existe por el seed, pero la migración usa `get_or_create` por robustez; el reverse recrea "Alimentos" sin restaurar los pools.

**Edge cases:** base sin "Otros" (get_or_create); "Higiene personal" preexistente (idempotente); pools en Alimentos de cualquier estado (solo cambia la categoría); reverse ejecutado dos veces (no duplica).

**Depends on:** none | **Unlocks:** —
**File scope:** `backend/pools/migrations/**`, `backend/pools/tests.py`
**Produces:** catálogo nuevo servido por `GET /api/v1/categories/` (contrato estable).
**Rollback:** punto de no retorno parcial -- el reverse recrea "Alimentos", pero no puede devolverle los pools (sin traza de origen); mitigación: reasignación manual documentada.

**File hints:** `backend/pools/migrations/0002_seed_categories.py` (patrón del seed); `backend/pools/tests.py` (assert a actualizar).

**Done when:**
- [x] DW-1.1: `GET /api/v1/categories/` incluye "Higiene personal" y no "Alimentos".
- [x] DW-1.2: un pool creado en "Alimentos" antes de migrar queda en "Otros" (test con MigrationExecutor).
- [x] DW-1.3: suite de `pools` verde con el assert de categorías actualizado.

**Difficulty:** LOW
**Uncertainty:** Si existen pools reales en "Alimentos"; la decisión de reasignar a "Otros" ya está tomada.

### Phase 2: Ubicación y mapa
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `cc-routine-and-class-design`, `cc-defensive-programming`
**Gate:** Standard

**Goal:** Agregar ubicación georreferenciada: lat/lng geocodificadas server-side al crear/editar el pool (Nominatim, fail-soft) y mapa Leaflet con marcador en el detalle.

**Scope:**
- IN: campos `latitud`/`longitud` (nullable) en `Pool` + migración; módulo de geocodificación (dirección+ciudad, timeout, User-Agent, fail-soft, sin reintentos) con interfaz mínima `geocodificar(direccion, ciudad) -> (Decimal, Decimal) | None`; hook en create/update (solo si cambia la dirección o faltan coords); serializer expone lat/lng; componente de mapa (paquete `leaflet` directo, sin wrappers) en el detalle; estado "sin ubicación".
- OUT: mapa en listado/home; búsqueda por radio/distancia; picker interactivo en el form.

**Constraints:** geocodificar solo al guardar (nunca en lectura); ≤1 req/s (Nominatim); la UI no debe romper si faltan coords; única dependencia nueva permitida: `leaflet` en el front.

**Edge cases:** Nominatim caído/timeout → coords null + log, el guardado no falla; dirección ambigua → primer resultado; sin resultados → null; edición sin cambio de dirección → no re-geocodifica; coordenada fuera de rango → descartar; pools viejos sin coords → "sin ubicación" hasta el próximo guardado con dirección nueva.

**Depends on:** none | **Unlocks:** —
**File scope:** `backend/pools/models.py`, `backend/pools/serializers.py`, `backend/pools/geocoding.py`, `backend/pools/views.py`, `backend/pools/migrations/**`, `backend/pools/tests.py`, `frontend/src/routes/pools/[id]/**`, `frontend/src/lib/**`, `frontend/package.json`
**Produces:** `Pool.latitud/longitud` (nullable) + `geocodificar()` + componente `MapaPool` (props: lat, lng, titulo).
**Approach notes:** Geocodificar solo al guardar y persistir coords (cuota Nominatim); no re-geocodificar si la dirección no cambia.

**File hints:** `backend/pools/models.py` (campos + validación), `backend/pools/views.py` (hook de guardado), `frontend/src/routes/pools/[id]/+page.svelte` (detalle).

**Done when:**
- [x] DW-2.1: crear un pool con dirección geocodificable guarda lat/lng (Nominatim mockeado, sin red en tests).
- [x] DW-2.2: si la geocodificación falla o no hay resultados, el pool se crea igual con coords null (error path).
- [x] DW-2.3: el detalle muestra el mapa con marcador cuando hay coords, y "sin ubicación" cuando no.
- [x] DW-2.4: editar la dirección actualiza las coords; editarla sin cambiarla no vuelve a consultar (no-op).

**Difficulty:** MED
**Uncertainty:** Estabilidad de Nominatim en dev; mitigada con fail-soft + mock en tests.

### Phase 3: Caducidad y estados
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `cc-control-flow-quality`, `cc-defensive-programming`, `aposd-verifying-correctness`
**Gate:** Standard

**Goal:** Caducidad real: un pool abierto que pasa su fecha sin completarse queda cancelado, no admite unirse/editar/salir, y la UI lo refleja; con comando de expiración para cron y chequeo perezoso en las lecturas.

**Scope:**
- IN: regla de vencimiento y transición abierto→cancelado; evaluación perezosa en list/detail/acciones; management command `expirar_pools` (idempotente, para cron); bloqueo de `unirse`/edición/`salir`/`mi-membresia` sobre vencidos; reflejo del estado en la UI (badge y acciones ocultas).
- OUT: notificaciones de caducidad; estado nuevo "vencido" (se reutiliza `cancelado`, ERS 2.3).

**Constraints:** solo pools `abierto` expiran (`listo`/`en_curso` no); el chequeo perezoso solo escribe cuando corresponde; guard clauses tempranos, sin anidar >3.

**Edge cases:** fecha = hoy → sigue válido todo el día; ya cancelado → no-op; comando repetido → no-op; pool `listo` con fecha pasada → no cambia; unirse a vencido sin lectura previa → 400 "El pool está vencido"; carrera expiración vs unión → lock existente (`_bloqueado`) + re-chequeo intra-transacción (TOCTOU).

**Depends on:** none | **Unlocks:** —
**File scope:** `backend/pools/models.py`, `backend/pools/views.py`, `backend/pools/management/**`, `backend/pools/tests.py`, `frontend/src/lib/estados.js`, `frontend/src/lib/PoolCard.svelte`, `frontend/src/routes/pools/**`
**Produces:** `expirar_vencidos() -> list[int]` (pks cancelados; invocada desde list/retrieve/acciones) + comando `expirar_pools` idempotente. Seam → P3.F3: engancha `registrar_evento` en esa transición y en las mutaciones existentes.
**Approach notes:** Decisión de producto: caducar **cancelando** (no "finalizar", no estado nuevo); la fecha es válida todo el día.

**File hints:** `backend/pools/models.py` (máquina de estados existente), `backend/pools/views.py` (acciones a guardar), `frontend/src/lib/PoolCard.svelte` (badges).

**Done when:**
- [x] DW-3.1: un pool abierto con fecha pasada queda `cancelado` tras una lectura (test con fecha retroactiva).
- [x] DW-3.2: `unirse` a un pool vencido responde 400 sin consumir disponible (dirty).
- [x] DW-3.3: `expirar_pools` cancela abiertos vencidos, es idempotente e ignora listo/en_curso/finalizados/cancelados.
- [x] DW-3.4: un pool `listo` con fecha pasada NO se cancela.
- [x] DW-3.5: la UI no ofrece unirse/editar en pools cancelados (revisión de guardas + check manual).

**Difficulty:** MED
**Uncertainty:** Límite "vence hoy" (documentado arriba).

### Phase 4: Eliminación con aprobación — API
**Model:** opencode-go/deepseek-v4-pro
**Skills:** `aposd-designing-deep-modules`, `cc-defensive-programming`
**Gate:** Full
**Security-sensitive:** yes

**Goal:** API del flujo de eliminación del ERS: eliminación directa del creador en `abierto`; en `listo`/`en_curso`, solicitud del creador y borrado solo si todos los miembros aceptan.

**Scope:**
- IN: modelos `SolicitudEliminacion` y `VotoEliminacion` (+ migración); endpoints `POST/GET /pools/{id}/eliminacion/` y `POST /pools/{id}/eliminacion/voto/`; reglas (unánime → borrar; rechazo → cerrar solicitud; re-solicitud permitida); bloqueo de `unirse`/`salir` con solicitud pendiente; permisos por rol; tests.
- OUT: notificaciones; UI (Phase 5); soft-delete.

**Constraints:** unanimidad requerida (ERS 3.7); hard delete con cascade; el creador no vota; mutaciones con `select_for_update` (patrón `_bloqueado`); errores es-AR por campo; diseñar la interfaz dos veces antes de implementar.

**Edge cases:** solicitud duplicada → 400; voto duplicado → 400; no miembro vota → 403; creador vota → 400; pool sale de `listo`/`en_curso` con solicitud pendiente → solicitud cerrada sin borrar; último voto concurrente → lock + evaluación intra-transacción; pool con imágenes → cascade.

**Depends on:** none | **Unlocks:** Phase 5
**File scope:** `backend/pools/models.py`, `backend/pools/serializers.py`, `backend/pools/views.py`, `backend/pools/migrations/**`, `backend/pools/tests.py`
**Produces:** contrato → Phase 5: `POST /pools/{id}/eliminacion/ -> 201 {id, estado:"pendiente"}`; `GET -> {estado, votos:[{usuario, acepta}], total, aceptaron}`; `POST /pools/{id}/eliminacion/voto/ {acepta: bool} -> 200 {estado}`; errores 400/403 es-AR.
**Rollback:** punto de no retorno en el borrado del pool -- mitigado con aprobación unánime + solo el creador solicita; sin soft-delete en alcance.

**File hints:** `backend/pools/views.py` (actions y `_bloqueado`), `backend/pools/serializers.py` (contratos), `backend/pools/models.py` (estados).

**Done when:**
- [x] DW-4.1: creador solicita en `listo`/`en_curso` → 201; `unirse`/`salir` bloqueados con pendiente (dirty).
- [x] DW-4.2: todos aceptan → pool borrado y memberships en cascade.
- [x] DW-4.3: un rechazo → solicitud cerrada y pool intacto.
- [x] DW-4.4: permisos y estados: no-creador 403, no-miembro 403, duplicados 400, solicitar/votar en `abierto` 400.
- [x] DW-4.5: eliminar directo en `abierto` sigue funcionando (regresión).

**Difficulty:** HIGH
**Uncertainty:** Semántica con solicitud pendiente + cambio de estado del pool; fijada en las reglas de arriba.

### Phase 5: Eliminación con aprobación — UI
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `cc-control-flow-quality`, `cc-defensive-programming`
**Gate:** Standard

**Goal:** UI del flujo: el creador solicita y ve el avance, cada miembro acepta o rechaza desde el detalle, y la eliminación directa en `abierto` pide confirmación.

**Scope:**
- IN: botón "Solicitar eliminación" (creador, `listo`/`en_curso`) con confirmación; panel de estado con votos (n/N) visible a integrantes; acciones Aceptar/Rechazar para miembros (una sola vez); al borrarse → toast + redirect a `/pools`; confirmación del eliminar directo existente.
- OUT: notificaciones; historial del evento (va en Plan 3).

**Edge cases:** 403/400 mapeados al aviso; miembro que ya votó ve su voto sin acciones; rechazo → aviso y opción de re-solicitar; pool desaparecido entre recargas → redirect con toast; no autenticado no ve el panel; error de red → alerta inline.

**Depends on:** Phase 4 | **Unlocks:** —
**File scope:** `frontend/src/routes/pools/[id]/**`, `frontend/src/lib/**`
**Produces:** — (consume el contrato de Phase 4).

**File hints:** `frontend/src/routes/pools/[id]/+page.svelte` (acciones del detalle).

**Done when:**
- [x] DW-5.1: creador ve "Solicitar eliminación" solo en `listo`/`en_curso`, con confirmación (cancelarla no llama a la API).
- [x] DW-5.2: miembro ve Aceptar/Rechazar, su voto queda registrado y no puede cambiarlo.
- [x] DW-5.3: con unanimidad → toast + redirect; con rechazo → aviso y pool intacto.
- [x] DW-5.4: eliminar directo en `abierto` conserva confirmación y comportamiento (regresión).

**Difficulty:** MED
**Uncertainty:** —

### Phase 6: Pestañas y pulido
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `cc-refactoring-guidance`
**Gate:** Standard

**Goal:** Pestañas Todos / Mis pools / Unidos dentro de la pantalla de pools (dirigidas por URL) y verificación de `/pools/nuevo` sin regresiones.

**Scope:**
- IN: pestañas en `/pools` con estado en query (`?tab=todos|mios|unidos`); reuso del listado/filtros/paginación por pestaña; `/mis-pools` y `/unidos` redirigen a sus tabs; nav ajustada; verificación funcional de `/pools/nuevo`.
- OUT: rediseño de tarjetas; paginación nueva.

**Constraints:** refactor en pasos chicos con suite verde tras cada paso; no cambiar endpoints.

**Edge cases:** `tab` inválido → `todos`; filtros por URL compartidos entre pestañas; deep-link a tab sin sesión → login (guard existente); 401 en tabs autenticados → logout (patrón actual).

**Depends on:** none | **Unlocks:** —
**File scope:** `frontend/src/routes/pools/**`, `frontend/src/routes/mis-pools/**`, `frontend/src/routes/unidos/**`, `frontend/src/routes/+layout.svelte`, `frontend/src/lib/**`
**Produces:** —

**File hints:** `frontend/src/routes/pools/+page.svelte` (listado + filtros), `frontend/src/routes/+layout.svelte` (nav).

**Done when:**
- [x] DW-6.1: `/pools` muestra pestañas y cambia de dataset con `?tab=` (todos/mios/unidos).
- [x] DW-6.2: `/mis-pools` y `/unidos` redirigen a su tab (sin páginas muertas).
- [x] DW-6.3: filtros, orden y paginación funcionan por pestaña; `/pools/nuevo` sigue operativo (revisión).

**Difficulty:** LOW
**Uncertainty:** —

---

## Test Coverage
**Level:** 100% de los done-when (unit + integración + manual donde aplique), con casos borde y dirty.

## Test Plan
- [ ] F1: migración (reasignación a "Otros", idempotencia, reverse, base sin "Otros") + assert de categorías (DW-1.1..3).
- [ ] F2: unit de `geocodificar` con Nominatim mockeado (ok / sin resultados / timeout) + integración crear/editar (coords y fail-soft) + no-op al reeditar la misma dirección (DW-2.1..4).
- [ ] F3: integración caducidad en detalle/acciones; comando (idempotencia; ignora listo/en_curso/finalizado/cancelado); dirty: unirse a vencido, fecha=hoy válida (DW-3.1..5).
- [ ] F4: integración solicitud/voto (unánime borra; rechazo cierra; duplicados; permisos; estados; pendiente + cambio de estado) + concurrencia con lock (DW-4.1..5).
- [ ] F5: manual UI por rol (creador/miembro), confirmaciones canceladas sin llamada, redirect al borrarse (DW-5.1..4).
- [ ] F6: manual pestañas/filtros/orden/paginación por tab, redirects `/mis-pools`/`/unidos`, verificación `/pools/nuevo` (DW-6.1..3).
- [ ] Regresión: suite backend completa + tests unit del front.

---

## Assumptions
| Assumption | Confidence | Verify Before Phase | Fallback If Wrong |
| --- | --- | --- | --- |
| Nominatim público usable desde dev (sin key) | MED | F2 | Pool sin coords y sin mapa; geocodificación manual por env |
| Puede haber pools reales en "Alimentos" | ALTA | F1 | Reasignar a "Otros" ya decidido; si se revierte, reasignación manual (el reverse no distingue) |
| Cron no disponible en dev | ALTA | F3 | Chequeo perezoso en lecturas + comando manual |

## Decision Log
| Decision | Alternatives Considered | Rationale | Phase |
| --- | --- | --- | --- |
| Caducar "cancelando" el pool vencido | Finalizar / estado nuevo "vencido" | ERS 2.3: cancelado por no alcanzar el total a tiempo | F3 |
| Eliminación hard delete con unanimidad | Soft-delete / borrado con mayoría | ERS 3.7: "se eliminará si todos aceptan" | F4 |
| Pestañas con `?tab=` dentro de `/pools` | Páginas separadas (statu quo) | Pedido del usuario: "pestaña de pools unidos" | F6 |
| Geocodificar server-side al guardar | Geocoder client-side / picker | Cuota de Nominatim + coords persistidas | F2 |
| Categoría "Alimentos" → "Otros" | Reasignar a "Higiene personal" | Semántica correcta | F1 |

---

## Notes
- Follow-up (batch 1–2, Note 1): guard `is_finite()` en `backend/pools/geocoding.py` para payloads NaN de Nominatim (1 línea).
- `/pools/nuevo`: revisar en las fases 1, 2, 3 y 6 que el alta siga sin regresiones.
- Los tests de F2/F3 no deben tocar la red ni relojes reales (mocks).
- La fecha de vencimiento es válida todo el día local (America/Argentina/Buenos_Aires).

---

## Execution Log

### Phase 1: Categorías (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: 6550e15
Summary: Catálogo actualizado (alta "Higiene personal", baja "Alimentos" con reasignación de pools a "Otros") vía data migration idempotente + tests de migración; suite backend en 86 verdes; migración aplicada en la dev DB (2 pools reales reasignados, estados intactos).
- Batch: Covered by batch review 2026-10-08 (phases 1–2)

### Phase 2: Ubicación y mapa (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: 2471492
Summary: lat/lng geocodificadas server-side al guardar (Nominatim fail-soft, ≤1 req/s) + mapa Leaflet en el detalle con estado "sin ubicación"; suite en 105 backend / 13 frontend verdes; migración 0004 aplicada en la dev DB.
- Batch: Covered by batch review 2026-10-08 (phases 1–2)

### Phase 3: Caducidad y estados (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: d85b72c
Summary: Caducidad real (abierto vencido → cancelado) con evaluación perezosa + comando `expirar_pools` idempotente y guards intra-transacción para unirse/salir/mi-membresia; la UI deja de ofrecer unirse/editar en cancelados; suite 115 backend / 16 frontend verdes; comando verificado en la dev DB.
- Batch: Covered by batch review 2026-10-08 (phase 3)

### Phase 4: Eliminación con aprobación — API (Gate: Full)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: Verification passed (3-sample) — majority PASS
- [x] Committed
Commit: 78bf361
Summary: API del flujo de eliminación del ERS (solicitud + votos unánimes, hard delete con cascade, permisos por rol, bloqueo de unirse/salir/mi-membresia con solicitud pendiente); contrato entregado a F5; suite 133 backend verdes.

### Phase 5: Eliminación con aprobación — UI (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: 9b1274b
Summary: Panel de eliminación en el detalle (solicitar/votar/confirmar, avance n/N, desenlaces con toast+redirect o aviso de rechazo) + guards que ocultan acciones bloqueadas y manejo de 404 del pool; helpers puros con tests; 22 frontend verdes.
- Batch: Covered by batch review 2026-10-09 (phases 5–6)

### Phase 6: Pestañas y pulido (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: e8fa45e
Summary: Pestañas URL-driven en /pools (todos/mios/unidos) con filtros/orden/paginación por pestaña; /mis-pools y /unidos quedan como redirects; extensión de scope documentada (fix backend en los actions mios/unidos para aplicar filtros, DW-6.3); suite 148 backend / 31 frontend verdes.
- Fix 2026-10-09: batch review findings addressed (catch vacío de categorías → aviso inline no bloqueante en /pools y /pools/nuevo; comentario obsoleto de pestanas.js eliminado) — commit 91b82ca
- Batch: Covered by batch review 2026-10-09 (phases 5–6, round 2)
