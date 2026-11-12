# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Vecinos y vecinas en Argentina** que necesitan productos que solo se venden al por mayor o en cantidades grandes y quieren comprar en grupo para pagar menos. Es el usuario primario: entra desde el celular, muchas veces desde el mismo barrio o ciudad.
- **Organizador del pool (vendedor)**: abre la publicación, analiza el enlace de la tienda, define cantidades, caducidad y datos de pago, compra al mayorista y coordina la entrega. Es el único que puede editarla o pedir su eliminación.
- **Participante (comprador)**: se suma al pool, elige cantidad y variantes, paga por transferencia o efectivo, sube el comprobante y confirma la recepción.
- **Observador**: explora pools y mayoristas sin unirse.
- **Staff / administración**: mantiene el directorio de mayoristas, las categorías y los parámetros del comparador desde el backoffice.
- **Equipo y evaluadores académicos**: PoolShop es la entrega final de la facultad; la documentación, los casos de prueba y la demo forman parte del producto.

## Product Purpose

PoolShop une personas interesadas en comprar al por mayor para que cada una compre solo la cantidad que necesita, a un precio justo, coordinando el grupo en un mismo lugar. El éxito es que un pool recorra completo su ciclo —abierto, listo, en curso, finalizado o cancelado— con cantidades claras, pagos verificados, entrega confirmada y reseñas. En el plano académico, el éxito es una entrega defendible con documentación, pruebas y una demo desplegada.

## Positioning

La unidad del producto es el **pool**, no el producto ni el chat: una compra colectiva con reglas, cantidades, caducidad, estados, pagos y evidencia. Alrededor de ese núcleo, PoolShop suma dos mecanismos que un marketplace genérico o un grupo de WhatsApp no pueden copiar sin reconstruir el flujo:

1. **Inteligencia de precio desde el enlace de la tienda**: autocompletado de nombre, precio e imagen, y comparador de costo final con envío, impuestos y aduana estimada.
2. **Confianza verificable**: directorio de mayoristas curado, comprobantes de pago, confirmación de recepción y reseñas entre participantes.

El alcance es la compra de barrio en Argentina.

## Operating Context

- La compra empieza con un enlace de una tienda (MercadoLibre, VTEX, Tiendanube, Amazon, mayoristas con o sin tienda online) o con una oferta que el organizador encontró personalmente.
- El grupo se coordina dentro del pool: chat interno, avisos en la app y por mail, y un estado que todos ven.
- El pago típico es transferencia (alias/CBU) o efectivo; el participante sube el comprobante y el organizador lo confirma o rechaza. Cada participante confirma la recepción de su parte.
- Los pools tienen fecha de caducidad y se cancelan solos si no se completan; las tareas periódicas mandan recordatorios de recepción cada 3 días.
- Los usuarios entran desde el celular o la computadora, por localhost, la IP de la red o el dominio; las imágenes se sirven desde `/media/`.
- La puesta en marcha es una demo académica en Render (Docker para desarrollo), no una operación comercial.

## Capabilities and Constraints

**Implementado:**

- Cuentas con nombre de usuario o email + contraseña, verificación de email obligatoria, recuperación de contraseña, perfil con foto, DNI, ubicación y baja con anonimización.
- Pools con título, producto, descripción, categoría y subcategoría, atributos/variantes, precio unitario y total calculado, cantidad total y mínima por integrante, caducidad, imágenes, ubicación con mapa y datos de pago (alias/CBU y titular).
- Autocompletado desde el enlace de la tienda con protección anti-SSRF y lectura de precios en es-AR; comparador de costo final con tipo de cambio y alícuotas editables, rotuladas como estimación.
- Membresías con cantidad, reparto por variantes, edición, salida y lock transaccional; estados `abierto`, `listo`, `en_curso`, `finalizado`, `cancelado`; eliminación con aprobación de los miembros.
- Chat por pool (polling), notificaciones en la app y por mail con preferencias por tipo y baja sin iniciar sesión, reseñas y puntajes entre participantes, perfiles públicos.
- Directorio de mayoristas curado con filtros, ficha, confianza del sitio, sugerencias de usuarios y carga por CSV; backoffice para mayoristas, categorías, atributos y parámetros.
- Tareas periódicas (caducidad, recordatorios de recepción, limpieza de sesiones) y CI con ruff, pytest, `node --test` y build del frontend.

**Restricciones y límites:**

- Idioma y moneda: español rioplatense, pesos argentinos con centavos; DNI, CBU/alias y provincias argentinas.
- No hay datos reales de mayoristas ni tipo de cambio cargado por defecto: el directorio arranca vacío y el tipo de cambio en 0. No inventar ofertas, clientes, testimonios ni métricas.
- Las estimaciones de aduana e impuestos son valores de referencia y deben rotularse como estimación.
- Stack actual (hecho de implementación, no compromiso de marca): Django 6 + DRF + PostgreSQL 17, SvelteKit SPA con adapter-static, Docker; Python 3.13+, Node 20.19+.
- Sesión JWT de 30 minutos con refresh rotativo hasta 14 días; medios en disco (`MEDIA_ROOT`), no en object storage; chat por polling, sin websockets.
- El proyecto es una entrega académica: no se prometen SLA, soporte ni operación comercial.

## Brand Commitments

- **Nombre: PoolShop** — único compromiso vinculante confirmado.
- La identidad visual actual (logo, paleta rojo/naranja, tipografías, dirección editorial) es la encarnación vigente, no un compromiso: un rediseño puede reemplazarla.
- El español rioplatense es el registro actual; no se confirmó como obligatorio, pero cambiarlo sería una decisión de producto, no un ajuste de estilo.

## Evidence on Hand

- `docs/ERS-PoolShop.docx` — especificación de requisitos (IEEE 830) con alcance, roles, estados y requisitos funcionales/no funcionales.
- `docs/Arquitectura-PoolShop*.docx`, `docs/Planificación-PoolShop.docx`, `docs/Escenario-PoolShop.docx`.
- `docs/Release1..4-PoolShop.docx` y sus presentaciones PDF, con capturas de recorridos reales.
- `docs/casos-de-prueba.md` (casos PS-H1 a PS-H25) y `docs/kanban.md` (estado del trabajo y desvíos aceptados).
- `docs/LogoPS.png` — asset de logo.
- App funcional con flujos reales de punta a punta; CI en `.github/workflows/ci.yml`.
- **Ausencias que no se deben fabricar:** no hay usuarios reales, testimonios, clientes, precios de mayoristas cargados ni tipo de cambio configurado. El directorio de mayoristas está vacío a propósito hasta que el equipo lo cargue.

## Product Principles

1. **El pool es la unidad de coordinación.** Toda función nueva debe reforzar el ciclo de vida de una compra colectiva (quién, cuánto, cuándo, cómo paga y cómo recibe), no crear otro objeto suelto.
2. **La confianza se muestra con evidencia.** Estados visibles, comprobantes, confirmaciones, reseñas y análisis de enlaces valen más que promesas; si un dato no existe, se muestra vacío y se explica, nunca se inventa.
3. **El precio final es el que decide.** Precio unitario, envío, impuestos, aduana y tipo de cambio se muestran juntos y con su carácter de estimación.
4. **La fricción del vecino es el enemigo.** Autocompletar el enlace, repartir cantidades por variante y avisar por mail reducen pasos; el flujo debe funcionar en un celular y en una conexión común.
5. **La entrega académica es parte del producto.** Documentación, casos de prueba, CI y demo desplegada se mantienen al día con cada release.

## Accessibility & Inclusion

- El código aplica criterios WCAG AA de contraste en los tokens (ratios anotados en `frontend/src/app.css`), foco visible, navegación por teclado en el menú y respeto por `prefers-reduced-motion`.
- El contenido está en español rioplatense, con fechas, montos y direcciones en formato argentino.
- El uso principal es mobile web; las pantallas deben funcionar en un celular sin scroll horizontal.
