---
name: poolshop-convenciones
description: Convenciones de código de PoolShop (Django/DRF + SvelteKit Svelte 5) resumidas para aplicarlas al escribir: textos es-AR, api() en vez de fetch, locks al mutar pools, registrar_evento, notificaciones por servicio.py, formularios con fieldErrors, módulos puros testeables, migraciones de datos. Usala antes de escribir o revisar cualquier código del repo PoolShop (modelos, endpoints, serializers, páginas, componentes, tests), aunque el pedido sea chico.
---

# Convenciones de PoolShop

La fuente completa es `docs/code-standards.md` (con ejemplos `DO/DON'T` y
archivos de referencia). Esto es lo que más se rompe al agregar funcionalidades,
con el porqué, para no tener que releer todo en cada cambio.

## Idioma

Todo lo que ve el usuario va en español rioplatense (voseo: "Elegí", "Iniciá
sesión"), incluidos los errores de la API. Los tests comparan mensajes y el
front los muestra tal cual. Dominio en español (`titulo`, `fecha_caducidad`,
acciones `unirse`, `mi-membresia`); clases de framework en inglés
(`PoolViewSet`, `MembershipSerializer`).

## Backend

- **Mutar un pool:** `with transaction.atomic(): pool = self._bloqueado(pk)` y
  recién ahí validar y cambiar. Sin lock, dos uniones simultáneas superan el cupo.
- **Validar:** en el serializer, con `ValidationError({"campo": "mensaje"})`. El
  front mapea por clave al campo correcto; un error sin clave se ve como general.
- **Historial:** cada acción que cambia algo del pool llama a
  `registrar_evento(pool, tipo, actor, datos)` (`pools/models.py`). `datos` nunca
  lleva teléfono, mensaje ni otra PII.
- **Notificar:** por `notificaciones/servicio.py`, que respeta las preferencias
  de cada usuario y manda el mail con `on_commit`. No crear `Notificacion` a mano.
- **PII:** teléfono y mensaje del miembro solo los ve el creador
  (`MembershipSerializer.to_representation`). Datos nuevos sensibles siguen la
  misma regla, en el serializer.
- **Consultas:** `select_related` + `prefetch_related` + `annotate` en el
  queryset; el serializer reusa las anotaciones. Un test con
  `CaptureQueriesContext` cuida el N+1 de las listas.
- **Integraciones externas** (HTTP, SMTP, geocoding, scraping): fail-soft. Se
  loguea con `logger.warning`/`logger.exception` y el endpoint sigue andando.
- **Imágenes:** los `models.ImageField` ya usan `CampoImagen`
  (`config/imagenes.py`): no agregar validaciones de formato propias.
- **Catálogos** (categorías, subcategorías, atributos): data migration con
  `reverse`, siguiendo `pools/migrations/0003_higiene_personal_baja_alimentos.py`.
- **Tareas periódicas:** comando en `management/commands/` y sumarlo a
  `TAREAS` en `pools/management/commands/tareas_periodicas.py` (lo corren el cron
  de Render y el `scheduler` de compose).
- **Tests:** funciones planas de pytest, fixtures `api_client`/`user`/`pool`,
  `reverse("pool-…")`, nombre `test_<accion>_<caso>`. Una regresión de un bug
  reportado lleva un comentario que diga qué rompía.

## Frontend

- **Llamadas:** siempre `api()` de `$lib/api.js`, nunca `fetch`. Ahí viven el
  token, la renovación automática de la sesión y `ApiError`.
- **401:** si llega a la página, la sesión ya venció y el usuario ya fue
  avisado. No llamar a `logout()` ni redirigir: el layout lleva al login con `?next=`.
- **Formularios:** `const { detail, non_field_errors, ...porCampo } = fieldErrors(e.data)`.
  Los campos van a `<Campo error=…>` y `detail` a un `<Aviso variante="error">`.
  Que ningún error quede sin mostrarse.
- **Estado:** runes (`$state`, `$derived`, `$effect`), sin stores. Para cargas en
  `$effect`, usar el contador de generación (`const actual = ++pedido`).
- **Lógica:** en un módulo puro `$lib/<feature>.js` (sin runes ni `api.js`), con
  su test `tests/<feature>.test.js` corrido por `node --test`. La página queda fina.
- **UI:** primitivas de `$lib/ui/` (`Boton`, `Campo`, `Aviso`, `Tarjeta`,
  `Badge`, `Chip`, `Avatar`), tokens de `src/app.css` (`--e-4`, `--marca`…) y
  CSS BEM en español (`.bloque__elemento--variante`). Los avisos breves van con
  `notificar(mensaje, tipo)`, que sobrevive a la navegación.
- **Accesibilidad:** errores con `role="alert"` (lo pone `Aviso variante="error"`),
  estados con `role="status"`, foco visible, nada que dependa solo del color.

## Antes de dar algo por terminado

Skill `poolshop-entorno` → `verificar.sh`. Si el cambio se ve en pantalla, sumá
o corré el recorrido correspondiente con la skill `poolshop-e2e` y mirá la captura.
