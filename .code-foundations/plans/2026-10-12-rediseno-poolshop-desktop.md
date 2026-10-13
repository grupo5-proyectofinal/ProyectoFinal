# Plan: Rediseño PoolShop (mockup Desktop) — Plan A
**Created:** 2026-10-12
**Status:** complete
**Started:** 2026-10-12 15:27
**Completed:** 2026-10-12 21:11
**Duration:** 15:27 → 21:11 (~5 h 45 min)
**Current Phase:** 7/7
**Complexity:** complex
**Review cadence:** 3

---
## Context

La app está completa y funcionando, pero su interfaz quedó en el sistema visual viejo. El mockup `docs/PoolShop Desktop.html` define la piel nueva (rojo `#DE3A3A` + naranja `#EA6A1F`, Bricolage Grotesque + DM Sans, fondo blanco, header con buscador, hero en Inicio, cards con progreso) para las pantallas que ya existen. Este plan (A) lleva la app a ese diseño con una **capa de primitivas Svelte** y sin tocar flujos, rutas ni contratos de API (salvo un ordering mínimo de presentación). Las features nuevas del mockup (reseñas/ranking, notificaciones, radio/mapa, crear con IA) van en el Plan B — IA quedó fuera de alcance por decisión del usuario.

## Constraints

- **Fidelidad visual al mockup**: colores, tipografías, radios, espaciados y estructura de cada pantalla según `docs/PoolShop Desktop.html` (extraído en `.code-foundations/design/`).
- **Contraste AA conservado** donde el diseño actual lo garantiza; todo par token/fondo usado para texto se mide y se documenta.
- **Responsive desktop-first** (mockup 1440) con móvil funcional; se conservan las estrategias actuales (menú móvil, grids que colapsan).
- **Sin dependencias nuevas de UI**; fuentes vía Google Fonts (mismo mecanismo que hoy) o self-host si falla.
- **Textos es-AR**; no se cambian flujos, rutas ni contratos de API (única excepción: `ordering=-integrantes` en `GET /pools/`).
- **Elementos que dependen de features nuevas** (Ranking en nav, campana, badge de chat, barra "cerca tuyo", filtros de distancia/calificación) **no entran**: son Plan B.
- **Sin tests nuevos** (decisión del usuario: "basta de tests"): los SSR que el rediseño deja obsoletos se **podan con razón registrada**; los tests de lógica pura no se tocan y la suite queda verde.

## Chosen Approach

**B) Capa de primitivas Svelte** — crear `frontend/src/lib/ui/` con primitivas que encapsulan el design system nuevo (tokens + variantes + ARIA) y refactorizar las pantallas para consumirlas. **Fallback:** la pantalla que resulte inviable de refactorizar se restylea in-place con las clases del sistema nuevo, y se registra la excepción (approach A aplicado localmente).

## Rejected Approaches

- **A) Evolución in-place:** recomendada por el planificador (diff mínimo, menos churn), descartada por el usuario en favor de la consistencia estructural de las primitivas.
- **C) Tailwind v4 + headless:** dependencia nueva, reescritura total de markup y choca con la restricción confirmada de "sin dependencias nuevas de UI".

---
## Implementation Phases

### Phase 1: Fundaciones + shell
**Model:** opencode-go/deepseek-v4-pro
**Skills:** aposd-designing-deep-modules, test-value
**Gate:** Full

**Goal:** Reemplazar el sistema visual viejo por el del mockup: tokens y fuentes nuevos, la capa de primitivas `lib/ui/` con su contrato, y el header/layout responsive (buscador funcional, nav Inicio/Explorar/Mis Pools, CTA Crear Pool, menú avatar).

**Scope:**
- IN: tokens/paleta/tipografía en `app.css` + `app.html`; primitivas `lib/ui/` (Boton, Campo, Chip, Badge, Aviso, Tarjeta, Avatar); header/layout nuevo con menú móvil; validación AA documentada; tests de primitivas + `header.test.js` actualizado.
- OUT: pantallas (fases 2-6); Ranking/campana/badge de chat (Plan B); dark mode (no está en el mockup).

**Constraints:** la API de primitivas se diseña con design-it-twice (2-3 alternativas, comparar, elegir) y cada primitiva debe tener ≥2 usos reales previstos (YAGNI); los tokens deben alcanzar para TODAS las pantallas (estados, badges, tablas, mapas) para que las fases siguientes no toquen `app.css`.

**Edge cases:** contraste de la paleta nueva (blanco sobre `#DE3A3A` ≈ 4.4:1 — borde AA: ajustar tono mínimo para texto chico y registrar medidas); menú móvil abierto/cerrado y foco; buscador con `q` vacío/espacios; fallback de fuentes si Google Fonts no carga; foco visible en todos los controles.

**Depends on:** none | **Unlocks:** Phase 2, 3, 4, 5, 6
**File scope:** `frontend/src/app.css`, `frontend/src/app.html`, `frontend/src/lib/ui/**`, `frontend/src/lib/Logo.svelte`, `frontend/src/routes/+layout.svelte`, `frontend/tests/header.test.js`, `frontend/tests/identidad.test.js` (poda de pins de logo)

**Produces:**
- Tokens en `app.css`: nombres estables (`--marca`, `--marca-fuerte`, `--acento-naranja`, `--tinta`, `--tinta-suave`, `--linea`, `--crema`, `--melocoton`, `--fuente-display`, `--fuente-texto`, radios/sombras).
- Primitivas con contrato: `Boton{variante:'primario'|'secundario'|'ghost'|'peligro-suave', tamano?:'sm'|'lg', bloque?:boolean, href?:string, tipo?, disabled?, onclick?}` + slot; `Campo{id, etiqueta, ayuda?, error?, requerido?}` + slot de control (oculta el wiring ARIA); `Chip{activo?, onclick?}`; `Badge{variante}`; `Aviso{variante:'exito'|'error'|'aviso'|'info'}`; `Tarjeta{?}`; `Avatar{nombre, foto?, tamano?}`.
- Shell: header (logo, buscador → `/pools?q=`, nav, CTA, menú avatar) + footer + menú móvil.

**Approach notes:** las primitivas encapsulan clases y ARIA; las pantallas no vuelven a escribir `class="btn ..."` a mano. El mockup manda en lo visual; ante ambigüedad, decidir con criterio y registrarlo en Notes. El logo (`Logo.svelte`) se ajusta al mockup; si el restyle rompe aserciones de logo en `identidad.test.js`, se podan en esta fase (P5 trabaja después sobre esa versión).
**File hints:** `frontend/src/app.css` — tokens actuales con notas AA medidas; `.code-foundations/design/mockup/17-Componente-encabezado.page.html` y `01-...page.html` — header/hero de referencia; `.code-foundations/design/shots/17-*.png` — cómo se ve.

**Done when:**
- [ ] DW-1.1: `app.css` con los tokens del mockup; pares de contraste de texto medidos y documentados (ninguno por debajo de AA en su tamaño de uso).
- [ ] DW-1.2: `lib/ui/` con las 7 primitivas y sus variantes del mockup; wiring ARIA de `Campo` (error → `aria-describedby`/`aria-invalid`) verificado a mano.
- [ ] DW-1.3: header/layout nuevos en 1440 y móvil (logo del mockup, menú móvil funcional), sin Ranking/campana/badge.
- [ ] DW-1.4: buscador del header navega a `/pools?q=<término>`.
- [ ] DW-1.5: pins obsoletos de `header.test.js` (y logo en `identidad.test.js`) podados con razón; sin dependencias nuevas (`package.json` intacto).
- [ ] DW-1.6: `npm run build` verde; suite restante verde (sin tests nuevos); salida guardada en `.code-foundations/build/`.

**Difficulty:** HIGH
**Uncertainty:** la paleta puede exigir ajustes mínimos de tono para AA (afecta los tokens y todas las fases).

---

### Phase 2: Inicio + Explorar
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** cc-refactoring-guidance, test-value
**Gate:** Standard

**Goal:** Llevar Inicio (hero, destacados, categorías, cerca de completarse) y Explorar (filtros + grilla de cards) al look del mockup consumiendo las primitivas, con el ordering mínimo `-integrantes`.

**Scope:**
- IN: `+page.svelte` (Inicio) y `pools/+page.svelte` (Explorar) restyleados con primitivas; **tabs Mis pools/Unidos del listado** (`?tab=mios|unidos`) con su grilla; `PoolCard`/`PoolCardSkeleton` al diseño de card del mockup (zona de imagen, pill de descuento, precio + tachado, barra de progreso, restantes, tiempo, "Unirme"); categorías como círculos; `ordering=-integrantes` en `GET /pools/` + test; tests SSR actualizados.
- OUT: barra "cerca tuyo"/ubicación, radio de distancia, filtros por creador y por calificación, badges de distancia (Plan B).

**Constraints:** los filtros actuales (q, categoria, precio_min/max, ciudad, estado, ordering) se conservan con sus params; la paginación con clamp (`paginaDeParams`) no cambia de comportamiento.

**Edge cases:** Inicio sin pools (secciones con empty state del sistema nuevo); filtros sin resultados; card sin imagen; nombre/precio largo (no romper layout); categoría sin icono mapeado; pool con `disponible=0`.

**Depends on:** Phase 1 | **Unlocks:** Phase 7
**File scope:** `frontend/src/routes/+page.svelte`, `frontend/src/routes/pools/+page.svelte`, `frontend/src/lib/PoolCard.svelte`, `frontend/src/lib/PoolCardSkeleton.svelte`, `backend/pools/views.py`, `backend/pools/tests.py`, `frontend/tests/unit.test.js`

**Produces:** pantallas restyleadas; contrato de API: `GET /api/v1/pools/?ordering=-integrantes` (más integrantes primero).

**Approach notes:** "destacados" usa `ordering=-vistas` (ya existe); "cerca de completarse" usa `-integrantes` (agregar `integrantes` a `ordering_fields` en `views.py`; la anotación `Count("memberships")` ya existe); si la fidelidad exige exactitud de unidades, anotar suma de cantidades y ordenar por eso (registrar). El mockup 08 ("Mis pools / historial") mapea a piezas existentes: la vista de tabs vive acá y el historial en el detalle (fase 3) — no se crea ruta nueva.
**File hints:** `.code-foundations/design/mockup/01-*.page.html` (hero/secciones/cards), `02-*.page.html` (filtros/grilla), `shots/01-*.png`, `shots/02-*.png`.

**Done when:**
- [ ] DW-2.1: Inicio con hero (título, subtítulo, CTA "Crear un pool") y secciones destacados/categorías/cerca de completarse fieles al mockup.
- [ ] DW-2.2: cards de pool con el diseño del mockup (progreso, descuento, restantes, tiempo) en Inicio y Explorar.
- [ ] DW-2.3: Explorar conserva todos los filtros y la paginación; los params siguen viajando a la API.
- [ ] DW-2.4: `ordering=-integrantes` implementado y verificado a mano en dev (sin test nuevo).
- [ ] DW-2.5: empty states y casos límite cubiertos a mano; pins obsoletos podados; `npm run build` verde.
- [ ] DW-2.6: tabs Mis pools/Unidos fieles al mockup 08 (grilla + acciones), sin ruta nueva.

**Difficulty:** MEDIUM
**Uncertainty:** el orden por integrantes puede no reflejar "cerca de completarse" si los pools tienen totales distintos.

---

### Phase 3: Ver pool + Unirse + Chat + Eliminación
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** cc-refactoring-guidance, test-value
**Gate:** Standard

**Goal:** Restyle completo de la pantalla más rica (`pools/[id]`): datos del pool, participantes, compartir, unirse con teléfono + mensaje, chat, panel de eliminación, mapa y mini-perfil, conservando todos los comportamientos.

**Scope:**
- IN: `pools/[id]/+page.svelte` + `PanelChat`, `PanelEliminacion`, `MiniPerfil`, `MapaPool` al sistema nuevo; **historial del pool (timeline)**; sección compartir (copiar enlace); tests SSR actualizados.
- OUT: reseñas/calificación del creador (Plan B); cambios de lógica de chat/eliminación/votos.

**Constraints:** el chat conserva polling, avisos de lectura/escritura y cursor; la eliminación conserva reglas de votos; el join conserva teléfono + mensaje y validaciones; el mapa sigue siendo Leaflet/OSM (estilo nuevo de marcadores/controles).

**Edge cases:** pool en cada estado (abierto/listo/en_curso/finalizado/cancelado) — chat en solo lectura y CTAs correctos; usuario no logueado (CTA a login); pool sin coordenadas (mapa oculto, sin hueco visual); miembro sin foto (Avatar con iniciales); teléfono/mensaje largos; enlace copiable sin permisos de clipboard (fallback).

**Depends on:** Phase 1 | **Unlocks:** Phase 7
**File scope:** `frontend/src/routes/pools/[id]/+page.svelte`, `frontend/src/lib/PanelChat.svelte`, `frontend/src/lib/PanelEliminacion.svelte`, `frontend/src/lib/MiniPerfil.svelte`, `frontend/src/lib/MapaPool.svelte`, `frontend/tests/chat.test.js`, `frontend/tests/historial.test.js`

**Produces:** pantalla de detalle restyleada; componentes de panel al sistema nuevo.

**Approach notes:** los helpers puros (chat.js, historial.js, eliminacion.js) NO se tocan — si un test SSR depende de markup, se actualiza al markup nuevo.
**File hints:** `.code-foundations/design/mockup/03-*.page.html` (detalle/compartir), `09-*.page.html` (chat), `11-*.page.html` (eliminación), `04-*.page.html` (unirse); `shots/03-*.png`, `shots/09-*.png`.

**Done when:**
- [ ] DW-3.1: detalle con secciones del mockup (participantes, descripción, detalles del producto, compartir con copiar enlace) y CTAs por estado.
- [ ] DW-3.2: join con teléfono prellenado + mensaje, con el look nuevo y validaciones intactas.
- [ ] DW-3.3: chat restyleado (burbujas/avatares) conservando polling y avisos; solo lectura donde corresponde.
- [ ] DW-3.4: eliminación, mapa (Leaflet) y mini-perfil con el sistema nuevo.
- [ ] DW-3.5: pins obsoletos podados (chat/historial); `npm run build` verde.
- [ ] DW-3.6: historial del pool (timeline) restyleado, conservando textos y paginación.

**Difficulty:** MEDIUM-HIGH
**Uncertainty:** el markup del chat/paneles es el más enredado; puede exigir refactor mayor que el previsto (fallback: restyle in-place documentado).

---

### Phase 4: Crear manual + Gestionar
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** cc-refactoring-guidance, test-value
**Gate:** Standard

**Goal:** Restyle del flujo de creación manual (formulario + validación de enlace + vista previa "Así se verá tu pool") y de la gestión del pool por el creador.

**Scope:**
- IN: `pools/nuevo/+page.svelte`, `pools/[id]/editar/+page.svelte`, `PanelEnlace` al sistema nuevo; vista previa de card con datos del formulario; tests SSR actualizados.
- OUT: creación con IA (fuera de alcance); cambios de reglas de validación de enlace.

**Constraints:** `PanelEnlace` conserva el contrato `{nivel, validaciones[]}` y sus etiquetas; el form conserva campos, validaciones por campo y envío.

**Edge cases:** enlace inválido/malformado (panel con nivel bajo); validaciones mixtas (https/acortador/longitud); preview con datos incompletos (campos vacíos no rompen la card); errores por campo del backend; imagen opcional.

**Depends on:** Phase 1, 2 | **Unlocks:** Phase 7
**File scope:** `frontend/src/routes/pools/nuevo/+page.svelte`, `frontend/src/routes/pools/[id]/editar/+page.svelte`, `frontend/src/lib/PanelEnlace.svelte`, `frontend/tests/confianza.test.js`

**Produces:** pantallas de creación/gestión restyleadas; preview de card reutilizando `PoolCard`.

**File hints:** `.code-foundations/design/mockup/06-*.page.html` (crear manual + "Así se verá tu pool"), `07-*.page.html` (gestionar); `shots/06-*.png`, `shots/07-*.png`.

**Done when:**
- [ ] DW-4.1: formulario de creación con el look nuevo y la vista previa de card del mockup.
- [ ] DW-4.2: `PanelEnlace` restyleado conservando niveles/etiquetas y sus tests.
- [ ] DW-4.3: gestión (participantes, datos, acciones) restyleada sin perder acciones existentes.
- [ ] DW-4.4: pins obsoletos podados; `npm run build` verde.

**Difficulty:** MEDIUM
**Uncertainty:** la vista previa puede requerir extraer lógica del form para reusar datos sin acoplarse.

---

### Phase 5: Perfil
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** cc-refactoring-guidance, test-value
**Gate:** Standard

**Goal:** Restyle de "Perfil" (datos de la cuenta, acciones y eliminación de cuenta) con el sistema nuevo.

**Scope:**
- IN: `perfil/+page.svelte` restyleado; tests SSR actualizados.
- OUT: "Reseñas recibidas" y calificaciones (Plan B); Mis pools/Unidos (son tabs dentro de Explorar → fase 2); historial del pool (→ fase 3); cambios de datos/acciones del perfil.

**Constraints:** el perfil conserva edición de datos y el flujo de eliminación de cuenta con su confirmación.

**Edge cases:** perfil sin teléfono/ciudad; errores por campo al guardar; acciones destructivas con confirmación intacta.

**Depends on:** Phase 1 | **Unlocks:** Phase 7
**File scope:** `frontend/src/routes/perfil/+page.svelte`, `frontend/tests/identidad.test.js`

**Produces:** pantalla de perfil restyleada.

**File hints:** `.code-foundations/design/mockup/15-*.page.html` (perfil); `shots/15-*.png`.

**Done when:**
- [ ] DW-5.1: Perfil (datos, acciones) restyleado y fiel al mockup; "Eliminar cuenta" del mockup no existe en la app → omitido con razón registrada (feature nueva, fuera de alcance).
- [ ] DW-5.2: pins obsoletos podados; `npm run build` verde.

**Difficulty:** LOW
**Uncertainty:** ninguna relevante.

---

### Phase 6: Auth + backoffice
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** cc-refactoring-guidance, test-value
**Gate:** Standard

**Goal:** Restyle de las pantallas de acceso (login, registro, recuperar, restablecer) según el mockup y del backoffice de usuarios por consistencia (no está en el mockup).

**Scope:**
- IN: `login`, `registro`, `recuperar`, `restablecer` con el layout del mockup (panel lateral/hero, campos, errores por campo); `admin/usuarios` (lista, alta, detalle) con tokens + primitivas; tests SSR actualizados.
- OUT: cambios de flujo de auth, permisos o validaciones; notificaciones (Plan B).

**Constraints:** auth conserva sus reglas (throttle, mensajes neutros de recuperación, redirects); el backoffice conserva sus acciones (roles, activación, paginación).

**Edge cases:** credenciales incorrectas; email inexistente (mensaje neutro); token inválido/expirado en restablecer; registro con errores por campo; admin sin permisos (redirect); tabla vacía.

**Depends on:** Phase 1 | **Unlocks:** Phase 7
**File scope:** `frontend/src/routes/login/+page.svelte`, `frontend/src/routes/registro/+page.svelte`, `frontend/src/routes/recuperar/+page.svelte`, `frontend/src/routes/restablecer/+page.svelte`, `frontend/src/routes/admin/**`, `frontend/tests/recuperacion.test.js`, `frontend/tests/admin.test.js`

**Produces:** pantallas de auth y backoffice restyleadas.

**Approach notes:** el backoffice no tiene mockup: se aplican tokens y primitivas manteniendo su estructura actual (no rediseñar jerarquías).
**File hints:** `.code-foundations/design/mockup/13-*.page.html`, `14-*.page.html`; `shots/13-*.png`, `shots/14-*.png`.

**Done when:**
- [ ] DW-6.1: login/registro/recuperar/restablecer con el look del mockup y errores por campo.
- [ ] DW-6.2: backoffice restyleado por consistencia sin perder acciones.
- [ ] DW-6.3: pins obsoletos podados; `npm run build` verde.

**Difficulty:** MEDIUM
**Uncertainty:** el mockup de auth es mínimo; el layout exacto se decide en la fase (registrar).

---

### Phase 7: Fidelidad final (responsive + AA + capturas)
**Model:** opencode-go/deepseek-v4.1-flash#max
**Skills:** aposd-verifying-correctness, test-value
**Gate:** Standard

**Goal:** Verificar la fidelidad contra el mockup con capturas lado a lado (desktop 1440 y móvil), corregir diferencias, validar contraste/foco y dejar la evidencia.

**Scope:**
- IN: capturas de cada pantalla cubierta vs su mockup; pase de responsive fino; validación AA de pares usados; corrección de diferencias detectadas; suite completa + build; reporte.
- OUT: features del Plan B; cambios de flujos.

**Constraints:** cada diferencia se corrige o se registra con razón (no silenciar); las capturas van a `.code-foundations/build/planA-capturas/`.

**Edge cases:** pantallas sin mockup (admin — criterio de consistencia); diferencias por fuente no cargada; estados especiales (empty, error) que el mockup no muestra; zoom/navegación por teclado.

**Depends on:** Phase 2, 3, 4, 5, 6 | **Unlocks:** none
**File scope:** `frontend/src/**` (correcciones puntuales), `.code-foundations/build/planA-capturas/**`

**Produces:** evidencia visual (capturas desktop/móvil por pantalla) + reporte de diferencias resueltas/aceptadas + suite completa guardada.

**Approach notes:** reutilizar el harness Playwright + Edge ya instalado (`%TEMP%\poolshop-e2e`, `manual-test.js` como referencia); el mockup renderizado está en `.code-foundations/design/shots/`.
**File hints:** `.code-foundations/design/shots/*.png` — objetivo lado a lado.

**Done when:**
- [ ] DW-7.1: capturas desktop 1440 de las 12 pantallas cubiertas, lado a lado con el mockup.
- [ ] DW-7.2: capturas móvil (≤390px) de las pantallas principales sin roturas de layout.
- [ ] DW-7.3: contraste AA verificado en los pares de texto usados; foco visible en controles.
- [ ] DW-7.4: diferencias detectadas corregidas o registradas con razón.
- [ ] DW-7.5: suite restante (backend + front podado) verde + build, con salida guardada.

**Difficulty:** MEDIUM
**Uncertainty:** aparecerán detalles de fidelidad imprevistos; el alcance de correcciones puede crecer.

---
## Test Coverage
**Level:** Sin tests nuevos — decisión del usuario ("basta de tests"; los pins de markup no aportan valor en un rediseño). La verificación del plan es visual (capturas lado a lado) + build.

## Test Plan
- [ ] Podado por fase: eliminar los SSR que el rediseño deja obsoletos (pins de textos/clases), con razón registrada; los tests de lógica pura (chat, historial, confianza, recuperación, admin…) no se tocan.
- [ ] P1 — podar pins obsoletos de `header.test.js` y de logo en `identidad.test.js`; contraste medido y registrado a mano; `npm run build` verde.
- [ ] P2 — `ordering=-integrantes` verificado a mano en dev (sin test nuevo); podar pins obsoletos del listado; `npm run build` verde.
- [ ] P3 — podar pins obsoletos del detalle/chat/historial; `npm run build` verde.
- [ ] P4 — podar pins obsoletos de crear/editar; `npm run build` verde.
- [ ] P5 — podar pins obsoletos de perfil; `npm run build` verde.
- [ ] P6 — podar pins obsoletos de auth/admin; `npm run build` verde.
- [ ] P7 — capturas lado a lado (desktop + móvil), AA y foco a mano; suite restante verde + build; reporte.

## Assumptions
| Assumption | Confidence | Verify Before Phase | Fallback If Wrong |
|---|---|---|---|
| Fuentes Bricolage Grotesque + DM Sans vía Google Fonts funcionan en dev/prod | HIGH | P1 | self-host de woff2 en `static/` |
| El mockup es la fuente de verdad visual; lo ambiguo se decide y registra | HIGH | P1 | criterio + registro en Notes |
| `ordering=-integrantes` alcanza para "cerca de completarse" | MEDIUM | P2 | anotar suma de cantidades y ordenar por eso |
| Los SVG del mockup son reutilizables como íconos | HIGH | P1 | dibujar equivalentes (stroke 1.8–2, mismo lenguaje) |
| El backoffice puede restylearse por consistencia sin mockup | HIGH | P6 | tokens nuevos sin refactor a primitivas |
| AA se logra con ajustes mínimos de tono | MEDIUM | P1 | oscurecer lo mínimo necesario y documentar medidas |

## Decision Log
| Decision | Alternatives Considered | Rationale | Phase |
|---|---|---|---|
| Capa de primitivas (B) | A in-place, C Tailwind | Decisión del usuario (consistencia estructural) | 1-6 |
| Crear con IA fuera de alcance | API real / adaptador / simulado | Decisión del usuario (entrega posterior) | — |
| Reseñas entre participantes | Solo creador / ambas | Decisión del usuario | Plan B |
| Responsive desktop-first | Solo desktop | Decisión del usuario | 1-7 |
| Sin tests nuevos; podar los SSR obsoletos | 100% / valor / per-phase | Decisión del usuario ("basta de tests"): los pins de markup no aportan en un rediseño; lógica pura intacta | todas |
| Tokens dentro de `app.css` | `theme.css` aparte | El proyecto ya centraliza tokens ahí | 1 |

---
## Notes
- Contraste a vigilar: blanco sobre `#DE3A3A` ≈ 4.4:1 (borde AA) — para texto chico usar un rojo levemente más oscuro; medir y registrar.
- El mockup extraído vive en `.code-foundations/design/` (`mockup/*.page.html` + `.css`, `shots/*.png`); la fuente original es `docs/PoolShop Desktop.html` (untracked en git — decidir si versionarlo).
- Harness E2E para P7 ya disponible: playwright-core + Edge en `%TEMP%\poolshop-e2e` (`manual-test.js` de referencia).
- `header.test.js` cambia en P1 (nav nuevo); los SSR por componente cambian en su fase.
- Ranking/campana/badge de chat/barra "cerca tuyo"/filtros de distancia y calificación: Plan B.
- **Sin tests en este plan** (decisión del usuario): no se escriben tests nuevos; los SSR obsoletos se podan con razón (pins de markup sin valor en un rediseño). La verificación es visual: capturas lado a lado (P7) + `npm run build`.

---
## Execution Log
### Phase 1: Fundaciones + shell (Gate: Full)
- [x] BUILD: Discovery + design + implementation (stub → implement → validate) complete
- [x] REVIEW: Verification passed (r2; r1 falló por 3 bloqueadores — contraste 3.94:1, foco del buscador, poda sin razón — los tres fixeados)
- [x] Committed
Commit: db9baec
Summary: Tokens/fuentes del mockup + capa de primitivas lib/ui/ (7) + header/layout nuevo (buscador → /pools?q=, menú móvil con ARIA), contraste AA medido; suite 92 y build verdes. Deja el sistema visual listo para que las fases 2-6 consuman las primitivas.

### Phase 2: Inicio + Explorar (Gate: Standard)
- [x] BUILD: Discovery + design + implementation complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: f2b0e06
Summary: Inicio y Explorar restyleados con las primitivas (hero, categorías en círculos, cards nuevas, tabs Mis pools/Unidos); API con ordering por integrantes y por restante (fallback aplicado: -integrantes no reflejaba "cerca de completarse"); suites 92/277 y build verdes. Regla para fases 3-6: al pasar clases a primitivas, el scope de Svelte no aplica → wrappers propios.
- [x] Covered by batch review 2026-10-12 (phases 2-4)

### Phase 3: Ver pool + Unirse + Chat + Eliminación (Gate: Standard)
- [x] BUILD: Discovery + design + implementation complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: f86f6a1
Summary: detalle + chat + unión + eliminación + mapa + mini-perfil + timeline restyleados consumiendo lib/ui/ (polling y reglas intactas); 24/24 verificaciones visuales en Edge headless, suite 92 y build verdes; sin poda (chat/historial no pinan markup).
- [x] Covered by batch review 2026-10-12 (phases 2-4)

### Phase 4: Crear manual + Gestionar (Gate: Standard)
- [x] BUILD: Discovery + design + implementation complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: 0a5f4fc
Summary: crear con preview viva de PoolCard y validación por campo; gestión con el molde 07 y panel de imágenes; PanelEnlace con Tarjeta; 20/20 verificación visual, 2 defectos reales de la preview arreglados; suite 92 y build verdes; sin poda.
- [x] Covered by batch review 2026-10-12 (phases 2-4)

### Phase 5: Perfil (Gate: Standard)
- [x] BUILD: Discovery + design + implementation complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: 6fcd824
Summary: Perfil restyleado al mockup 15 con primitivas (14/14 verificaciones visuales, 3 defectos reales corregidos); "Eliminar cuenta" del mockup omitido con razón (no existe el flujo/endpoint en la app; feature nueva fuera de alcance); suite 92 y build verdes; sin poda.
- [x] Covered by batch review 2026-10-12 (phases 5-7)

### Phase 6: Auth + backoffice (Gate: Standard)
- [x] BUILD: Discovery + design + implementation complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: d88251f
Summary: auth (login/registro/recuperar/restablecer) con el layout del mockup 13/14 y backoffice con tokens + primitivas sin perder acciones; fix real de desborde móvil de la tabla; guard estático de admin.test.js refinado (el mismo defecto real sigue detectándose); 28/28 verificaciones visuales, suite 92 y build verdes.
- [x] Covered by batch review 2026-10-12 (phases 5-7)

### Phase 7: Fidelidad final (responsive + AA + capturas) (Gate: Standard)
- [x] BUILD: Discovery + design + implementation complete
- [x] REVIEW: DEFERRED — batch pending (tests green at commit)
- [x] Committed
Commit: 0164479
Summary: 54 capturas desktop/móvil + 28 comparativas lado a lado con el mockup; 2 defectos reales corregidos (el "+" del hero invisible por svg 0x0 y el "+" faltante del header); AA: 0 pares activos bajo AA; foco: 0 controles sin indicador; diferencias aceptadas registradas por pantalla; suite 92/92 + 277 y build verdes.
- [x] Covered by batch review 2026-10-12 (phases 5-7)

### VERIFY (2026-10-12)
- [x] Trailing batch review P5-P7: PASS
- [x] Fix de VERIFY: import muerto `iniciales` eliminado de `perfil/+page.svelte`
- [x] Suite final: frontend 92/92 + build verde (`.code-foundations/build/rediseno-poolshop-desktop-verify.txt`); backend 277 passed (corrida propia del batch review)
- [x] Performance: sin regresiones (anotación `restante` en queryset; sin N+1 ni hotspots nuevos)
- Deuda registrada: CSS legacy duplicado en `app.css` (.btn/.badge/.chip/.alerta/.avatar junto a las primitivas) — limpieza para un pase posterior; capturas y artefactos en `.code-foundations/build/` (ignorado por git)
