---
name: poolshop-e2e
description: Recorridos end-to-end de PoolShop en un Chromium real (Playwright) con capturas — sesión que se renueva o vence, borrador de "Crear pool", foto de perfil HEIC, pool con imagen — entrando por la IP de la red como lo hace el cliente. Usala para confirmar en la app real cualquier cambio de sesión, formularios, subida de imágenes o flujos de pools, para sacar capturas para un PR o un informe, o cuando el usuario reporta "en mi navegador no anda", aunque no pida "e2e".
---

# Recorridos e2e de PoolShop

Los tests de `node --test` del front no tienen DOM: prueban lógica pura. Lo que
el cliente ve (redirecciones, toasts, imágenes que cargan o no) solo se confirma
en un navegador. Esta skill lo hace con el Chromium preinstalado.

## Pasos

1. Entorno listo y usuarios de prueba: skill `poolshop-entorno` (sección
   "Levantar la app" y "Usuarios de prueba"). Backend en `0.0.0.0:8000` y Vite en
   `0.0.0.0:5173`, ambos en background.
2. Imágenes de prueba (JPG, PNG, HEIC, WEBP):
   ```bash
   backend/.venv/bin/python .claude/skills/poolshop-e2e/scripts/generar_imagenes.py <scratchpad>/e2e-imagenes
   ```
3. Correr los recorridos contra la **IP del contenedor** (`hostname -I`), no
   localhost. El cliente prueba desde otro equipo (`http://192.168.x.x:5173`) y
   así aparecen los errores de host y de URLs de media que localhost esconde:
   ```bash
   node .claude/skills/poolshop-e2e/scripts/recorridos.cjs --base http://<ip>:5173 \
     --imagenes <scratchpad>/e2e-imagenes --capturas <scratchpad>/e2e-capturas [--solo sesion,foto]
   ```
4. **Mirar las capturas** con Read antes de dar algo por bueno: un `OK` dice
   que no hubo excepción, la captura dice si se ve bien. Las capturas que van al
   usuario o a un PR se sacan con `deviceScaleFactor: 2`.

## Recorridos incluidos

| Nombre | Qué confirma |
|---|---|
| `sesion` | Con el access vencido y el refresh válido, recargar `/pools/nuevo` no cierra la sesión |
| `expirada` | Con todo vencido: toast "Tu sesión expiró", login con `?next=` y borrador recuperado |
| `foto` | Foto de perfil HEIC (iPhone) se sube y se ve |
| `pool` | Pool creado con imagen WEBP (WhatsApp) que se ve en el detalle |

## Agregar un recorrido

Sumá una función `async nombre(page)` al objeto `RECORRIDOS` de
`scripts/recorridos.cjs`. Que tire `Error` con un motivo legible cuando algo no
está como debe, y que guarde una captura en `CAPTURAS`. Seleccioná por `id` de
los campos (los formularios usan `id` = nombre del campo de la API) y por texto
visible en es-AR para avisos y botones. Cada fase nueva suma los suyos
(variantes al unirse, comparador, mayoristas…).
