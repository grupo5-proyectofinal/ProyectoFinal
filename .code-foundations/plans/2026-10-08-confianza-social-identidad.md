# Plan: Confianza, social e identidad

**Created:** 2026-10-08
**Status:** complete
**Started:** 2026-10-10 13:16
**Completed:** 2026-10-11 12:42
**Duration:** 2026-10-10 13:16 → 2026-10-11 12:42
**Complexity:** complex
**Review cadence:** 2

---

## Context

PoolShop tiene la base funcionando (usuarios, pools, búsqueda, rediseño UI), pero queda todo el backlog confirmado del usuario: "Olvidé mi contraseña" + correo, backoffice ABM de usuarios, nombre del usuario logueado, categorías (alta de "Higiene personal" / baja de "Alimentos"), ubicación del pool con mapa, caducidad de pools abiertos, pestaña de pools unidos, confianza al unirse (datos extra + perfil visible al creador), análisis propio del enlace de tienda, historial de cambios, eliminación de pool con aprobación, estados, chat entre integrantes e identidad visual (logo/colores) + entorno (Node ≥20).

Decisiones fijadas con el usuario: Leaflet/OpenStreetMap para mapas; análisis del enlace con lógica propia (sin servicios externos); SMTP configurable con consola en dev; backoffice propio en la app; flujo completo de eliminación del ERS; unión con datos extra y perfil visible al creador; logo a medida; se mantiene la línea visual actual.

La planificación se dividió en 3 planes verticales encadenados (≤7 fases c/u): **P1 Pools — ciclo de vida y ubicación**, **P2 Cuentas y administración**, **P3 Confianza, social e identidad** (este). Orden de build: P1 → P2 → P3; la fase de historial depende de los flujos creados en P1.

## Constraints

- Stack actual, sin servicios pagos: Django 6 + DRF + SimpleJWT; SvelteKit (Svelte 5 runes, `ssr=false`); Postgres 17 en Docker; API `/api/v1` con mensajes es-AR; paginación page-number (12).
- No romper flujos ni casos de prueba existentes (PS-*); actualizar los tests afectados.
- Sin secretos en el repo: todo por `.env`.
- Tests sin acceso a red (servicios externos mockeados).
- El análisis del enlace es local: no se hace fetch de URLs de terceros (sin SSRF).
- Datos personales (teléfono/mensaje del miembro) visibles solo al creador; nunca se registran en el historial.
- Chat por polling REST (sin WebSockets); escritura desde `listo`, lectura para integrantes.
- Ejecución secuencial: las fases comparten áreas de código; no se asume paralelismo entre fases (opencode no deriva waves).

## Chosen Approach

**3 planes verticales por dominio.** Este es el Plan 3: confianza (datos del miembro + análisis del enlace), social (historial + chat) e identidad visual. Su fase de historial consume los flujos de P1 (expiración, eliminación con aprobación). **Fallback:** las fases 1, 2, 4, 5 y 6 son independientes de P1/P2 y podrían reordenarse.

## Rejected Approaches

- **Por capas (datos/API primero):** concentra la integración front↔back al final; sin entregas verificables end-to-end.
- **Demo-first:** pospone los cambios que tocan datos existentes (migraciones, caducidad, eliminación) y aumenta el riesgo de retrabajo.

---

## Implementation Phases

### Phase 1: Unión con datos y perfil
**Model:** opencode-go/deepseek-v4-pro
**Skills:** `aposd-designing-deep-modules`, `cc-defensive-programming`
**Gate:** Full
**Security-sensitive:** yes

**Goal:** Dar confianza al creador: el miembro aporta teléfono (prellenado del perfil) y un mensaje al unirse, y el creador ve esos datos más el perfil y los pools en común del miembro, con privacidad estricta.

**Scope:**
- IN: campos `telefono` (requerido) y `mensaje` en `Membership` (+ migración); payload de `unirse` extendido; privacidad: teléfono/mensaje visibles SOLO al creador; endpoint de perfil público (`/api/v1/usuarios/{id}/`: nombre, foto, ciudad, antigüedad, pools en común, conteos); UI: modal de unión mejorado + panel del creador con datos y mini-perfil; tests por rol.
- OUT: calificaciones; validación por SMS; re-edición de los datos post-unión.

**Constraints:** teléfono/mensaje nunca se exponen a otros miembros ni en listados; validar teléfono (largo/formato) en el boundary; diseñar la interfaz de serialización por rol una vez y documentarla.

**Edge cases:** teléfono vacío/solo espacios → 400; mensaje largo → validar límite; miembro sin foto → monograma; sin pools en común → lista vacía; miembro que sale del pool → sus datos se van con la membership; consulta del perfil desde fuera del pool → solo datos públicos.

**Depends on:** none | **Unlocks:** —
**File scope:** `backend/pools/**`, `backend/users/**`, `frontend/src/routes/pools/[id]/**`, `frontend/src/lib/**`
**Produces:** payload `{cantidad, telefono, mensaje}` + regla de visibilidad por rol + endpoint de perfil público.
**Approach notes:** Privacidad resuelta en la serialización por rol (no en el front); sin re-edición de datos post-unión.

**File hints:** `backend/pools/serializers.py` (`MembershipSerializer`), `backend/pools/views.py` (`unirse`), `frontend/src/routes/pools/[id]/+page.svelte`.

**Done when:**
- [x] DW-1.1: unirse sin teléfono → 400; con datos válidos guarda teléfono/mensaje (test).
- [x] DW-1.2: el creador recibe teléfono/mensaje en el detalle; otro miembro y el público NO (test de privacidad por rol, dirty).
- [x] DW-1.3: el endpoint de perfil devuelve los pools en común correctos.
- [x] DW-1.4: la UI de unión prellena el teléfono y muestra los datos al creador (verificación funcional).

**Difficulty:** MED
**Uncertainty:** Re-edición de datos de la membership fuera de alcance; si se pide, se extiende `mi-membresia`.

### Phase 2: Análisis del enlace
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `aposd-designing-deep-modules`, `cc-defensive-programming`
**Gate:** Standard

**Goal:** Análisis propio del enlace de tienda con validaciones visibles que den confianza a quien mira el pool: formato/HTTPS/dominio, señales de riesgo y nivel de uso interno.

**Scope:**
- IN: módulo `confianza.py` con `analizar_enlace(url) -> {nivel, validaciones[]}`: URL válida, HTTPS, acortadores, IP literal, TLD/patrones sospechosos, longitud; uso interno (# de pools con el mismo dominio); serializer expone `analisis_enlace` cuando hay enlace; panel "Validaciones del enlace" en el detalle con aclaración "análisis propio".
- OUT: servicios externos (VirusTotal/X-Force descartado por el usuario); bloqueo de publicación; reseñas externas.

**Constraints:** solo heurísticas locales; sin fetch ni deserialización (string matching puro: por eso NO se marca security-sensitive); cómputo barato sin caché persistente.

**Edge cases:** enlace vacío → sin panel; URL malformada → nivel con detalle; scheme implícito/mayúsculas → normalizar; acortador conocido → alerta; dominio repetido → "uso alto" (señal positiva; umbral en implementación).

**Depends on:** none | **Unlocks:** —
**File scope:** `backend/pools/confianza.py`, `backend/pools/serializers.py`, `backend/pools/views.py`, `backend/pools/tests.py`, `frontend/src/routes/pools/[id]/**`, `frontend/src/lib/**`
**Produces:** contrato `analisis_enlace: {nivel, validaciones: [{clave, ok, detalle}]}` + panel UI.
**Approach notes:** Contrato estable `{nivel, validaciones[]}` para poder enchufar un servicio externo después sin tocar la UI.

**File hints:** `backend/pools/serializers.py` (PoolSerializer), `frontend/src/routes/pools/[id]/+page.svelte` (detalle).

**Done when:**
- [x] DW-2.1: cada regla del analizador tiene tests, incluidos casos dirty (malformada, IP literal, acortador, sin HTTPS).
- [x] DW-2.2: pool con enlace muestra el panel con validaciones y nivel; sin enlace no aparece.
- [x] DW-2.3: "nivel de uso" refleja el conteo de pools con el mismo dominio (test).
- [x] DW-2.4: no se hace ningún fetch de la URL analizada (revisión + tests sin red).

**Difficulty:** MED
**Uncertainty:** Umbral de "uso alto" ajustable sin cambiar contrato.

### Phase 3: Historial del pool
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `cc-refactoring-guidance`, `aposd-designing-deep-modules`, `test-value`
**Gate:** Standard

**Goal:** Registrar y mostrar el historial de cambios del pool para sus integrantes: uniones, bajas, cantidades, ediciones, imágenes, estados y solicitudes de eliminación.

**Scope:**
- IN: modelo `EventoPool` (tipo, actor null=sistema, datos JSON, fecha) + migración; helper `registrar_evento()`; hooks en los flujos existentes (crear, editar, imágenes, unirse/salir/mi-membresia, transiciones, expiración y solicitud/voto de eliminación del Plan 1); endpoint `GET /pools/{id}/historial/` solo integrantes, paginado; timeline en el detalle de integrantes.
- OUT: notificaciones; edición/borrado de eventos.

**Constraints:** cada hook entra en un paso chico con la suite verde entre pasos (cc-refactoring); no registrar PII (teléfono/mensaje) en `datos`; textos es-AR.

**Edge cases:** pool borrado → eventos en cascade; edición sin cambios → no registra; actor desactivado → nombre igual; historial vacío (pools previos) → estado vacío; no integrante → 403/404.

**Depends on:** Plan 1 completo (cross-plan: expiración y eliminación existen) | **Unlocks:** —
**File scope:** `backend/pools/**`, `frontend/src/routes/pools/[id]/**`
**Produces:** contrato `GET /pools/{id}/historial/ -> {results: [{tipo, actor, datos, creado}]}` + timeline UI.

**File hints:** `backend/pools/views.py` (puntos de mutación), `backend/pools/models.py`, `frontend/src/routes/pools/[id]/+page.svelte`.

**Done when:**
- [x] DW-3.1: cada flujo clave emite el evento correcto (tests por tipo: unión, salida, cantidad, edición, estado).
- [x] DW-3.2: expiración (sistema) y solicitud/voto de eliminación quedan registrados con actor correcto.
- [x] DW-3.3: historial: integrantes 200 (creador incluido), no integrante 403/404; paginado (dirty).
- [x] DW-3.4: la UI muestra el timeline solo a integrantes, sin datos personales en los textos.

**Difficulty:** MED
**Uncertainty:** Volumen de eventos en pools longevos; el paginado cubre.

### Phase 4: Chat — API
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `aposd-designing-deep-modules`, `cc-defensive-programming`, `test-value`
**Gate:** Standard

**Goal:** Mensajería por pool para integrantes: enviar y leer mensajes con polling incremental por `desde`.

**Scope:**
- IN: modelo `Mensaje` (pool, autor, texto, creado) + migración + índice (pool, id); `GET /pools/{id}/mensajes/?desde=<id>&limit=` (ascendente, default 50, máx 200); `POST /pools/{id}/mensajes/ {texto}`; permisos de integrantes; lectura en cualquier estado, escritura desde `listo` hasta `finalizado` (ERS); tests.
- OUT: WebSockets/SSE; adjuntos; leído/no leído; borrar/editar.

**Constraints:** polling REST (decisión fijada); texto normalizado (strip, no vacío, ≤1000); se renderiza como texto (sin HTML); errores es-AR.

**Edge cases:** texto vacío/whitespace → 400; >1000 → 400; no integrante → 403; pool inexistente → 404; `desde` inválido → 0; `limit` fuera de rango → clamp; escritura en `abierto`/`cancelado` → 400; autor desactivado → mensajes siguen visibles.

**Depends on:** none | **Unlocks:** Phase 5
**File scope:** `backend/pools/models.py`, `backend/pools/serializers.py`, `backend/pools/views.py`, `backend/pools/migrations/**`, `backend/pools/tests.py`
**Produces:** contrato → Phase 5: `GET -> {results:[{id, autor:{id,username,foto}, texto, creado}], hay_mas}`; `POST {texto} -> 201`; polling con `desde` = último id.
**Approach notes:** `desde` (último id) es el contrato del polling; lectura siempre, escritura desde `listo`.

**File hints:** `backend/pools/views.py` (patrón `_paginar`/`_bloqueado`), `backend/pools/models.py`.

**Done when:**
- [x] DW-4.1: integrante envía y lee; no integrante 403 en GET y POST (dirty).
- [x] DW-4.2: polling incremental: `desde` devuelve solo lo nuevo, ascendente y limitado.
- [x] DW-4.3: texto vacío/whitespace o >1000 → 400 sin persistir.
- [x] DW-4.4: escritura bloqueada en `abierto`/`cancelado`, lectura permitida (test por estados).

**Difficulty:** MED
**Uncertainty:** —

### Phase 5: Chat — UI
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `cc-control-flow-quality`, `test-value`
**Gate:** Standard

**Goal:** Panel de chat integrado al detalle: ver y enviar mensajes con refresco por polling, solo para integrantes.

**Scope:**
- IN: sección de chat para integrantes; carga inicial + polling con `desde` (solo con la pestaña visible); envío con limpieza del input y manejo de error; scroll al último mensaje; avatares/monogramas; aviso cuando la escritura está bloqueada por estado.
- OUT: notificaciones/contador global; edición de mensajes.

**Constraints:** un único intervalo por vista, limpiado al desmontar/cambiar de pool; sin polling con `document.hidden`; no duplicar mensajes al re-render.

**Edge cases:** sin mensajes → estado vacío; error de red → aviso discreto y reintento en el próximo tick; cambio de estado en caliente → 400 al enviar con aviso; fetch en vuelo al desmontar → no actualizar estado muerto.

**Depends on:** Phase 4 | **Unlocks:** —
**File scope:** `frontend/src/routes/pools/[id]/**`, `frontend/src/lib/**`
**Produces:** — (consume el contrato de Phase 4).

**File hints:** `frontend/src/routes/pools/[id]/+page.svelte` (detalle).

**Done when:**
- [x] DW-5.1: integrante ve el panel; no integrante no (dirty por rol).
- [x] DW-5.2: enviar agrega el mensaje y persiste tras recargar.
- [x] DW-5.3: mensajes de otro usuario aparecen por polling en ≤10 s (verificación manual asistida).
- [x] DW-5.4: el intervalo se detiene al salir de la página y no hay duplicados (revisión de cleanup).

**Difficulty:** MED
**Uncertainty:** Intervalo de polling -- 5 s de arranque, ajustable.

### Phase 6: Identidad y entorno
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `code-clarity-and-docs`, `test-value`
**Gate:** Standard

**Goal:** Cerrar la identidad visual (logo SVG propio, favicon, consolidación de colores) manteniendo la línea editorial, y fijar el requisito de Node para Vite 8.

**Scope:**
- IN: logo SVG (isotipo + wordmark) en header y pantallas de auth; favicon; revisión/consolidación de la paleta existente (tokens de `app.css`, sin romper contraste AA); `engines.node` en `package.json` (rango exacto según Vite 8) + README.
- OUT: rediseño total; logo en páginas internas secundarias.

**Edge cases:** favicon cacheado (cache-bust por nombre); logo legible a tamaños chicos; modo solo claro (actual); `npm install` en Node viejo → mensaje claro de engines (`.npmrc` ya tiene `engine-strict`).

**Depends on:** none | **Unlocks:** —
**File scope:** `frontend/static/**`, `frontend/src/app.html`, `frontend/src/app.css`, `frontend/src/routes/+layout.svelte`, `frontend/src/routes/login/**`, `frontend/src/routes/registro/**`, `frontend/package.json`, `README.md`
**Produces:** assets de marca + requisito de Node declarado.

**File hints:** `frontend/src/app.css` (tokens), `frontend/src/app.html` (favicon), `README.md` (requisitos).

**Done when:**
- [x] DW-6.1: el logo aparece en header y auth; el favicon nuevo se sirve (verificación visual).
- [x] DW-6.2: `package.json` declara `engines.node` y el README documenta Node ≥20; `npm run build` pasa con el Node actual (v24).
- [x] DW-6.3: la paleta consolidada no rompe contraste ni la suite del front (build + tests verdes).

**Difficulty:** LOW
**Uncertainty:** Rango exacto de engines según la versión de Vite -- verificar al implementar.

---

## Test Coverage
**Level:** Valor sobre cobertura (skill `test-value`): un test por riesgo real (regla, borde, error, permiso); **sin cuota de 100%**; mutation spot-check del código cambiado; prohibido sumar tests de relleno o aserciones de fuente como sustituto de comportamiento.

## Test Plan
- [ ] F1: integración unión con datos (400 sin teléfono; guardado) + privacidad por rol (creador ve; miembro/público no) + perfil con pools en común (DW-1.1..4).
- [ ] F2: unit de reglas del analizador (nominal + dirty: malformada, IP literal, acortador, sin HTTPS) + integración del panel y del conteo de uso (DW-2.1..4).
- [ ] F3: integración eventos por flujo (unión, salida, cantidad, edición, estado, expiración, eliminación/voto) + permisos y paginado del historial + regresión de flujos tocados (DW-3.1..4).
- [ ] F4: integración mensajes (permisos, `desde`/`limit`, validaciones, estados de escritura) (DW-4.1..4).
- [ ] F5: manual chat (envío, polling ≤10 s, bloqueo por estado, cleanup) (DW-5.1..4).
- [ ] F6: manual identidad (logo, favicon) + `npm run build` con engines declarado (DW-6.1..3).
- [ ] Regresión: suites backend y front completas.

---

## Assumptions
| Assumption | Confidence | Verify Before Phase | Fallback If Wrong |
| --- | --- | --- | --- |
| Polling alcanza para el chat (demo/curso) | ALTA | F4 | Migrar a SSE/WebSockets con el mismo contrato |
| Heurísticas propias alcanzan sin APIs externas | ALTA | F2 | Adaptador externo detrás del mismo contrato |
| "Pools en común" consultable a esta escala | MED | F1 | Índices dedicados si la query crece |

## Decision Log
| Decision | Alternatives Considered | Rationale | Phase |
| --- | --- | --- | --- |
| Escritura del chat desde `listo` | Siempre / solo `en_curso` | ERS 2.3: el chat nace en "Listo para comprar" | F4 |
| Análisis sin fetch de la URL | HEAD request al dominio | Evita SSRF y dependencias de red | F2 |
| Eventos con `actor=null` para el sistema | Pseudo-usuario | Simple y honesto | F3 |
| Logo SVG a medida | Tercerizar / text-only | Pedido del usuario; sin dependencias | F6 |

---

## Notes
- Política de tests actualizada (2026-10-10): valor sobre cobertura (skill `test-value`); sin cuotas; cada test debe poder fallar por un defecto real; mutation spot-check del código cambiado.
- El historial no registra datos personales (teléfono/mensaje).
- F4 (chat) queda Standard a propósito: seam aditivo, sin seguridad ni cascada; lo cubre el review por lote (cadencia 2).
- El polling debe limpiar intervalos al desmontar y no correr con `document.hidden`.
- El análisis del enlace es orientativo ("análisis propio"), no bloquea publicaciones.

---

## Execution Log

### Phase 1: Unión con datos y perfil (Gate: Full)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: Verification passed (3-sample) — majority PASS (3/3)
- [x] Committed
Commit: b569abf
Summary: Unión con teléfono/mensaje + perfil visible al creador (privacidad por rol en la serialización; endpoint público con pools en común; UI con prefill y panel del creador); migración 0006 aplicada; suite 192 backend / 69 frontend.

### Phase 2: Análisis del enlace (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: 94a31ea
Summary: Módulo de análisis local del enlace (heurísticas + uso interno por dominio, sin fetch) y panel de validaciones en el detalle; tests por riesgo con mutation spot-check (5/6 mutantes muertos); 213 backend / 75 frontend.
- Batch: Covered by batch review 2026-10-10 (phases 2–3)

### Phase 3: Historial del pool (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: 5962f83
Summary: EventoPool + hooks en todos los flujos del pool + endpoint de historial para integrantes con timeline en el detalle (sin PII); 239 backend / 81 frontend; mutation spot-check 6/6.
- Batch: Covered by batch review 2026-10-10 (phases 2–3)

### Phase 4: Chat — API (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: b12d046
Summary: API de chat por pool (Mensaje + índice; GET/POST con permisos de integrantes, polling `desde`/`limit`, escritura desde listo hasta finalizado); +40 casos, mutation 8/8; suite 279 backend; migración 0008 aplicada.
- Batch: Covered by batch review 2026-10-11 (phases 4–5)

### Phase 5: Chat — UI (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: 8f65ce4
Summary: Panel de chat en el detalle (polling 5 s con `desde`, catch-up con tope, sin polling oculto, cleanup de intervalo/listener, borrador conservado en error, dedupe por id) gateado por rol/estado; 92 frontend; mutation 9/9.
- Batch: Covered by batch review 2026-10-11 (phases 4–5)

### Phase 6: Identidad y entorno (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: 2509017
Summary: Logo SVG propio + favicon con cache-bust + consolidación de 14 tokens de color + engines Node/README; 104 frontend; mutation 4/4; fix de especificidad en la marca del pie.
- Fix 2026-10-11: batch review findings addressed (CSS de tamaño/responsive de la marca movido dentro del componente con su hash; tests SSR rojo→verde; reglas muertas eliminadas) — commit 6ecd17e
- Batch: Covered by batch review 2026-10-11 (phase 6, round 2)
