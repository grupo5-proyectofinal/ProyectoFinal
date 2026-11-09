---
name: poolshop-migraciones-datos
description: Cómo agregar, renombrar, reasignar o dar de baja datos de catálogo en PoolShop (categorías, subcategorías, atributos por categoría, parámetros) con data migrations de Django reversibles y testeadas. Usala siempre que haya que cambiar qué categorías u opciones ve el usuario ("agregá la categoría X", "sacá Y", "Ropa > Remera > Talle"), aunque el pedido no mencione migraciones.
---

# Migraciones de datos de catálogo en PoolShop

Las categorías no se cargan con fixtures ni desde el admin: se siembran por data
migration (`pools/migrations/0002_seed_categories.py` y siguientes). Así cada
entorno (tu máquina, `docker compose`, Render) queda igual después de `migrate`,
que corre solo al arrancar. Cargarlas a mano en un entorno las deja desfasadas
de los demás y de los tests.

## Receta

1. Mirá la última migración de la app (`ls backend/pools/migrations`). La nueva
   depende de esa. Si hay dos hojas, primero hace falta un merge, como en
   `0010_merge_pagos_resena`.
2. Escribí la migración a mano. `makemigrations` no genera datos. Modelos de
   referencia:
   - alta simple: `0011_categoria_ropa.py`;
   - alta + baja con reasignación de pools: `0003_higiene_personal_baja_alimentos.py`.
3. Reglas:
   - **Modelos históricos:** usá `apps.get_model("pools", "Category")`, nunca
     importes `pools.models`. El modelo actual puede tener campos que en ese punto
     del historial todavía no existen.
   - **Idempotencia:** `get_or_create` para altas y `filter(...).delete()` para
     bajas. Una migración que corre dos veces o sobre datos parciales no debe romper.
   - **Reasignar antes de borrar:** `Pool.categoria` es `on_delete=PROTECT`.
     Mové los pools (a "Otros" o a la categoría nueva) con `update()` y después borrá.
   - **Reverse que no destruye:** el reverse borra solo lo que nadie usa
     (`pools__isnull=True`). Si hubiera que perder datos para volver atrás, es
     preferible dejar la fila.
   - **Nombres visibles en es-AR**, con mayúscula inicial y acentos
     ("Higiene personal", "Electrónica"): el front los muestra tal cual.
4. Front: si la categoría necesita ícono, sumá la palabra clave en `ICONOS` de
   `frontend/src/routes/+page.svelte`. Sin coincidencia se usa el cubo genérico.
5. Tests en `backend/pools/tests.py`:
   - que la API (`reverse("category-list")`, sin paginar) la devuelva;
   - que el reverse no borre una categoría con pools. Se importa con
     `importlib.import_module("pools.migrations.00XX_…")` y se llama a la función
     con `(apps, None)`, donde `apps` es `django.apps.apps`;
   - para migraciones con reasignación, usá el patrón de `MigrationExecutor`
     (`migrar_pools` / `apps_historicas` en `pools/tests.py`), que migra hacia
     atrás y hacia adelante sobre datos reales.
6. Corré `python manage.py migrate` en el entorno local
   (`poolshop-entorno/scripts/preparar.sh` lo hace) y los tests.

## Atributos y subcategorías (Fase 2)

Cuando existan `Category.padre` y `AtributoCategoria`, la siembra va en una
migración aparte, posterior a la de esquema:

- primero los padres y después los hijos (`get_or_create(nombre=…, padre=…)`);
- opciones de atributo como lista JSON ordenada (`["XS", "S", "M", "L", "XL", "XXL"]`);
- el reverse borra hijos y atributos que no estén en uso, en orden inverso.
