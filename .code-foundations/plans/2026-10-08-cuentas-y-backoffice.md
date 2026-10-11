# Plan: Cuentas y administración

**Created:** 2026-10-08
**Status:** complete
**Started:** 2026-10-09 10:09
**Completed:** 2026-10-10 13:06
**Duration:** 2026-10-09 10:09 → 2026-10-10 13:06
**Complexity:** complex
**Review cadence:** 3

---

## Context

PoolShop tiene la base funcionando (usuarios, pools, búsqueda, rediseño UI), pero queda todo el backlog confirmado del usuario: "Olvidé mi contraseña" + correo, backoffice ABM de usuarios, nombre del usuario logueado, categorías (alta de "Higiene personal" / baja de "Alimentos"), ubicación del pool con mapa, caducidad de pools abiertos, pestaña de pools unidos, confianza al unirse (datos extra + perfil visible al creador), análisis propio del enlace de tienda, historial de cambios, eliminación de pool con aprobación, estados, chat entre integrantes e identidad visual (logo/colores) + entorno (Node ≥20).

Decisiones fijadas con el usuario: Leaflet/OpenStreetMap para mapas; análisis del enlace con lógica propia (sin servicios externos); SMTP configurable con consola en dev; backoffice propio en la app; flujo completo de eliminación del ERS; unión con datos extra y perfil visible al creador; logo a medida; se mantiene la línea visual actual.

La planificación se dividió en 3 planes verticales encadenados (≤7 fases c/u): **P1 Pools — ciclo de vida y ubicación**, **P2 Cuentas y administración** (este), **P3 Confianza, social e identidad**. Orden de build: P1 → P2 → P3. Este plan no depende de P1.

## Constraints

- Stack actual, sin servicios pagos: Django 6 + DRF + SimpleJWT; SvelteKit (Svelte 5 runes, `ssr=false`); Postgres 17 en Docker; API `/api/v1` con mensajes es-AR; paginación page-number (12).
- No romper flujos ni casos de prueba existentes (PS-*); actualizar los tests afectados.
- Sin secretos en el repo: todo por `.env`.
- Tests sin acceso a red (servicios externos mockeados).
- El rol admin reutiliza `is_staff` (Django); no se crean roles nuevos.
- Email: consola por defecto; SMTP si el `.env` define credenciales; link del mail a `FRONTEND_URL`.
- El reset no debe revelar la existencia de cuentas (respuesta neutra).
- Ejecución secuencial: las fases comparten áreas de código; no se asume paralelismo entre fases (opencode no deriva waves).

## Chosen Approach

**3 planes verticales por dominio.** Este es el Plan 2: tres tracks independientes (reset de contraseña, backoffice de usuarios, header con identidad de sesión) en cinco fases acopladas solo por pares productor→consumidor. **Fallback:** puede ejecutarse antes o después de P1 sin cambios; solo P3 depende de P1.

## Rejected Approaches

- **Por capas (datos/API primero):** concentra la integración front↔back al final; sin entregas verificables end-to-end.
- **Demo-first:** pospone los cambios que tocan datos existentes (migraciones, caducidad, eliminación) y aumenta el riesgo de retrabajo.

---

## Implementation Phases

### Phase 1: Reset — API + email
**Model:** opencode-go/deepseek-v4-pro
**Skills:** `cc-defensive-programming`, `aposd-designing-deep-modules`
**Gate:** Full
**Security-sensitive:** yes

**Goal:** Flujo completo de recuperación de contraseña: solicitar (respuesta neutra, sin revelar cuentas) y confirmar con token; mail por consola en dev o SMTP según `.env`.

**Scope:**
- IN: `POST /api/v1/auth/password-reset/ {email}` (siempre 200; envía solo si existe) y `POST /api/v1/auth/password-reset/confirm/ {uid, token, password, password2}`; token con `default_token_generator`; mail con link a `${FRONTEND_URL}/restablecer?uid=&token=`; config MAILERS (consola por defecto, SMTP si hay credenciales) + `.env.example`; throttle anónimo; tests.
- OUT: UI (Phase 2); blacklist de JWT (nota abajo).

**Constraints:** respuesta neutra para no enumerar cuentas; validar password con los validators de Django; errores es-AR por campo; no loguear tokens; `set_password` invalida el token de reset (un solo uso efectivo).

**Edge cases:** email inexistente → 200 sin envío; email malformado → contrato neutro coherente; token inválido/expirado/reusado → 400; uid roto → 400; password débil o mismatch → 400 con clave; SMTP caído → no tumbar el endpoint (log + respuesta neutra); throttle excedido → 429.

**Depends on:** none | **Unlocks:** Phase 2
**File scope:** `backend/users/**`, `backend/config/settings.py`, `.env.example`
**Produces:** contrato → Phase 2: endpoints (200 neutro / 200 al confirmar / 400 con claves) + formato del link.
**Approach notes:** Reset propio con tokens de Django (sin dependencias nuevas); contrato neutro ante cuentas existentes o no.

**File hints:** `backend/users/urls.py` (rutas auth), `backend/config/settings.py` (MAILERS), `backend/users/views.py` (patrón de vistas).

**Done when:**
- [x] DW-1.1: solicitud con email existente envía un mail con el link correcto; con email inexistente responde igual (200) y no envía (test de neutralidad).
- [x] DW-1.2: confirm con token válido cambia la clave: login viejo 401 y login nuevo 200 (end-to-end).
- [x] DW-1.3: token inválido/expirado/reusado y uid roto → 400 sin efectos (dirty).
- [x] DW-1.4: password débil o mismatch → 400 con la clave correspondiente.
- [x] DW-1.5: sin SMTP usa consola; con `EMAIL_HOST` usa SMTP (test de settings).

**Difficulty:** MED
**Uncertainty:** simplejwt sin blacklist: los JWT emitidos antes del reset siguen válidos hasta expirar -- limitación aceptada.

### Phase 2: Reset — UI
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `cc-defensive-programming`
**Gate:** Standard

**Goal:** Pantallas de recuperación: `/recuperar` (pedir el link) y `/restablecer` (definir clave nueva), con el enlace "¿Olvidaste tu contraseña?" en el login.

**Scope:**
- IN: páginas públicas con el sistema visual actual; lectura de `uid`/`token` del query; errores por campo; éxito → redirect a `/login` con toast; link desde login.
- OUT: templates de mail custom; captcha.

**Edge cases:** `uid`/`token` faltantes → estado de error claro con salida a `/recuperar`; token expirado/usado → mensaje es-AR; doble submit → botón deshabilitado; password débil → mensaje del backend; /recuperar siempre muestra confirmación neutral.

**Depends on:** Phase 1 | **Unlocks:** —
**File scope:** `frontend/src/routes/recuperar/**`, `frontend/src/routes/restablecer/**`, `frontend/src/routes/login/**`, `frontend/src/lib/**`
**Produces:** — (consume el contrato de Phase 1).

**File hints:** `frontend/src/routes/login/+page.svelte` (patrón de formulario y enlace).

**Done when:**
- [x] DW-2.1: `/recuperar` muestra confirmación neutral exista o no la cuenta.
- [x] DW-2.2: el link del mail abre `/restablecer` con uid/token y permite fijar la clave; después el login funciona.
- [x] DW-2.3: token inválido/expirado o parámetros faltantes → mensaje claro con salida a `/recuperar`.
- [x] DW-2.4: el login expone el enlace de recuperación y navega a `/recuperar`.

**Difficulty:** LOW
**Uncertainty:** —

### Phase 3: Backoffice — API
**Model:** opencode-go/deepseek-v4-pro
**Skills:** `aposd-designing-deep-modules`, `cc-defensive-programming`
**Gate:** Full
**Security-sensitive:** yes

**Goal:** API de administración de usuarios para staff: listar/buscar, ver, crear, editar perfil y activar/desactivar cuentas.

**Scope:**
- IN: `/api/v1/admin/usuarios/` (GET con `q`, `is_active`, paginado; POST alta reusando el registro sin autologin) y `/api/v1/admin/usuarios/{id}/` (GET/PATCH); permisos `IsAdminUser`; `/auth/me` expone `is_staff`; tests.
- OUT: gestión de roles por API; borrado físico (baja = desactivar).

**Constraints:** email/dni/username/is_staff no editables por API; un admin no puede desactivarse a sí mismo; mensajes es-AR; contrato chico y documentado.

**Edge cases:** usuario inexistente → 404; duplicados (email/dni/username) → 400 por campo; PATCH vacío → 200 sin cambios; desactivado → login 401; `q` vacío → lista completa; página fuera de rango → comportamiento DRF estándar.

**Depends on:** none | **Unlocks:** Phase 4
**File scope:** `backend/users/**`
**Produces:** contrato → Phase 4: endpoints admin + `{is_staff}` en `/auth/me`.

**File hints:** `backend/users/serializers.py` (registro existente), `backend/users/views.py` (patrón de vistas).

**Done when:**
- [x] DW-3.1: no-staff recibe 403 en todos los endpoints admin; staff 200 (dirty).
- [x] DW-3.2: listado filtra por `q` (email/usuario/nombre/apellido) y `is_active`, paginado de 12.
- [x] DW-3.3: PATCH edita campos permitidos; desactivar impide login (401) y reactivar lo restaura.
- [x] DW-3.4: no puede desactivarse a sí mismo; cambios a email/dni/username/is_staff se ignoran.
- [x] DW-3.5: alta crea usuario con clave válida e `is_staff=false`; duplicados → 400.
- [x] DW-3.6: `/auth/me` incluye `is_staff`.

**Difficulty:** MED
**Uncertainty:** —

### Phase 4: Backoffice — UI
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `cc-defensive-programming`
**Gate:** Standard

**Goal:** Panel de usuarios en la app: listado con búsqueda/filtros, detalle editable y activar/desactivar, accesible solo para staff.

**Scope:**
- IN: `/admin/usuarios` (listado con `q`, filtro activo/inactivo, paginación) y `/admin/usuarios/[id]` (ver, editar, toggle); alta de usuario; guard de rol; entrada "Admin" condicional en la nav.
- OUT: roles granulares; auditoría visual; edición de email/dni.

**Edge cases:** staff que pierde el rol → 403 mapeado y redirect; no auto-desactivarse desde la UI; estados carga/vacío/error; usuario inexistente → 404 con aviso.

**Depends on:** Phase 3 | **Unlocks:** —
**File scope:** `frontend/src/routes/admin/**`, `frontend/src/routes/+layout.svelte`, `frontend/src/lib/**`
**Produces:** — (consume el contrato de Phase 3).

**File hints:** `frontend/src/routes/pools/+page.svelte` (patrón listado+filtros), `frontend/src/routes/perfil/+page.svelte` (patrón formulario).

**Done when:**
- [x] DW-4.1: solo staff ve "Admin" y accede; usuario común en la URL → redirect (dirty).
- [x] DW-4.2: listado con búsqueda, filtro y paginación funcionando.
- [x] DW-4.3: detalle edita campos y activa/desactiva con reflejo inmediato.
- [x] DW-4.4: alta de usuario desde el panel con errores por campo.

**Difficulty:** MED
**Uncertainty:** —

### Phase 5: Header con usuario
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** `cc-control-flow-quality`
**Gate:** Standard

**Goal:** Mostrar avatar y nombre del usuario logueado en el header (escritorio y móvil) con menú de sesión.

**Scope:**
- IN: avatar (foto o monograma con tono estable) + nombre + menú con "Mi perfil" y "Cerrar sesión"; misma identidad en el menú móvil; foco/Escape como el patrón accesible actual.
- OUT: cambios al menú móvil más allá de sumar la identidad; nombre en footer.

**Edge cases:** sin foto → monograma; nombre vacío → username; `session.user` en carga → placeholder discreto; sin sesión → botones actuales; Escape/click afuera cierran el menú.

**Depends on:** none | **Unlocks:** —
**File scope:** `frontend/src/routes/+layout.svelte`, `frontend/src/app.css`
**Produces:** —

**File hints:** `frontend/src/routes/+layout.svelte` (header actual), `frontend/src/lib/formato.js` (`iniciales`), `frontend/src/lib/estados.js` (`tonoNombre`).

**Done when:**
- [x] DW-5.1: logueado ve avatar + nombre en escritorio y móvil; el menú navega a perfil y cierra sesión.
- [x] DW-5.2: sin foto usa monograma; sin sesión no aparece la identidad.
- [x] DW-5.3: Escape y foco cumplen el patrón accesible del header (verificación por teclado).

**Difficulty:** LOW
**Uncertainty:** —

---

## Test Coverage
**Level:** 100% de los done-when (unit + integración + manual donde aplique), con casos borde y dirty.

## Test Plan
- [ ] F1: integración reset (neutralidad con email existente/inexistente, token válido/inválido/expirado/reusado, uid roto, password débil/mismatch, MAILERS consola/SMTP, throttle) (DW-1.1..5).
- [ ] F2: manual UI (estados de `/recuperar` y `/restablecer`, parámetros faltantes, link real desde consola) (DW-2.1..4).
- [ ] F3: integración admin API (403 no-staff, filtros `q`/`is_active`, PATCH, toggle y login bloqueado, self-guard, duplicados, alta) + `is_staff` en `/auth/me` (DW-3.1..6).
- [ ] F4: manual UI panel (guard de rol, listado, detalle, alta, estados) (DW-4.1..4).
- [ ] F5: manual header (escritorio/móvil, monograma, Escape/foco, sin sesión) (DW-5.1..3).
- [ ] Regresión: suites backend y front completas.

---

## Assumptions
| Assumption | Confidence | Verify Before Phase | Fallback If Wrong |
| --- | --- | --- | --- |
| Sin credenciales SMTP en dev | ALTA | F1 | Consola por defecto; SMTP se activa por `.env` |
| `is_staff` alcanza como rol admin | ALTA | F3 | Campo/rol nuevo solo si piden granularidad |
| No hay blacklist de JWT en el proyecto | ALTA | F1 | Documentado: tokens previos expiran solos |

## Decision Log
| Decision | Alternatives Considered | Rationale | Phase |
| --- | --- | --- | --- |
| Reset con tokens de Django (custom) | dj-rest-auth / tokens propios | Sin dependencias nuevas; patrón conocido | F1 |
| Rol admin = `is_staff` | Grupos/permisos / campo rol | Mínimo y suficiente | F3 |
| Baja = desactivar (`is_active=False`) | Borrado físico | Integridad referencial (pools/memberships) | F3 |
| Mail por consola en dev | SMTP obligatorio | Demo sin cuentas; SMTP configurable | F1 |

---

## Notes
- simplejwt sin blacklist: los JWT vigentes tras un reset expiran naturalmente (limitación aceptada).
- Throttle anónimo en la solicitud de reset para frenar abuso.
- `FRONTEND_URL` en `.env` define el host del link del mail.

---

## Execution Log

### Phase 1: Reset — API + email (Gate: Full)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: Verification passed (3-sample) — majority PASS (3/3)
- [x] Committed
Commit: 0e6491b
Summary: Reset de contraseña end-to-end en la API (solicitud neutra con throttle + confirmación por token de Django de un solo uso; MAILERS consola/SMTP por entorno); contrato entregado a F2; suite 163 backend verdes.

### Phase 2: Reset — UI (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: 4eadb7e
Summary: Pantallas /recuperar y /restablecer sobre el contrato de F1 (confirmación neutral, errores por campo, enlace muerto con salida, toast + redirect al login) + enlace en el login; helpers puros con tests; 39 frontend verdes y build OK.
- Fix 2026-10-09: batch review findings addressed (normalización de `detail` lista/string → pantalla "Enlace inválido" alcanzable; tests con la forma real) — commit 8f88429
- Batch: Covered by batch review 2026-10-09 (phase 2, round 2)

### Phase 3: Backoffice — API (Gate: Full)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: Verification passed (3-sample) — majority PASS (3/3)
- [x] Committed
Commit: f95dd79
Summary: API admin para staff (listado con q/is_active + alta + detalle/PATCH con toggle y self-lockout; inmutables fuera del serializer; `/auth/me` con is_staff); contrato entregado a F4; suite 180 backend verdes.

### Phase 4: Backoffice — UI (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: a6c9852
Summary: Panel /admin/usuarios (listado con búsqueda/filtro/paginación, detalle editable con toggle y auto-desactivarse bloqueado, alta con errores por campo) + guard por is_staff con nav condicional; helpers puros con tests; 57 frontend verdes y build OK.
- Fix 2026-10-10: batch review findings addressed (import de `notificar` en el listado admin + guard estático de identificadores sin binding en páginas admin) — commit 2a035c4
- Batch: Covered by batch review 2026-10-10 (phases 4–5, round 2)

### Phase 5: Header con usuario (Gate: Standard)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: b584c7d
Summary: Identidad del logueado en el header (avatar o monograma + nombre + menú de sesión en escritorio y móvil; Escape con retorno de foco y click afuera); 67 frontend verdes y build OK.
- Batch: Covered by batch review 2026-10-10 (phases 4–5, round 2)
