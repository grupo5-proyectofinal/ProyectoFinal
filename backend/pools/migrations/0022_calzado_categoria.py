from django.db import migrations

# Corrección del cliente: "Calzado debería ser una categoría con subcategorías
# Zapatilla, Sandalias y Zapato". Calzado deja de colgar de Ropa y pasa a ser
# una categoría raíz; sus pools quedan en Calzado (sin tipo). El Talle de
# calzado queda en el padre y lo heredan los hijos; Color se agrega porque
# antes lo heredaba de Ropa.
COLORES = ["Negro", "Blanco", "Gris", "Azul", "Rojo", "Verde", "Beige", "Rosa"]
HIJOS = ["Zapatilla", "Sandalias", "Zapato"]


def separar(apps, schema_editor):
    Category = apps.get_model("pools", "Category")
    Atributo = apps.get_model("pools", "AtributoCategoria")

    calzado, _ = Category.objects.get_or_create(nombre="Calzado")
    if calzado.padre_id is not None:
        calzado.padre = None
        calzado.save(update_fields=["padre"])
    if not Atributo.objects.filter(categoria=calzado, nombre="Talle").exists():
        Atributo.objects.create(
            categoria=calzado, nombre="Talle", opciones=[str(n) for n in range(34, 46)], orden=0
        )
    Atributo.objects.get_or_create(
        categoria=calzado, nombre="Color", defaults={"opciones": COLORES, "orden": 1}
    )
    for nombre in HIJOS:
        hijo, _ = Category.objects.get_or_create(nombre=nombre, defaults={"padre": calzado})
        if hijo.padre_id != calzado.pk:
            hijo.padre = calzado
            hijo.save(update_fields=["padre"])


def volver(apps, schema_editor):
    """Calzado vuelve a Ropa; los tipos nuevos se borran solo si nadie los usa.

    Los pools de un tipo nuevo (Zapatilla…) pasan a Calzado para poder borrarlo.
    """
    Category = apps.get_model("pools", "Category")
    Atributo = apps.get_model("pools", "AtributoCategoria")
    Pool = apps.get_model("pools", "Pool")

    calzado = Category.objects.filter(nombre="Calzado").first()
    ropa = Category.objects.filter(nombre="Ropa").first()
    if calzado is None:
        return
    for nombre in HIJOS:
        hijo = Category.objects.filter(nombre=nombre, padre=calzado).first()
        if hijo is None:
            continue
        Pool.objects.filter(categoria=hijo).update(categoria=calzado)
        hijo.delete()
    Atributo.objects.filter(categoria=calzado, nombre="Color").delete()
    if ropa is not None:
        calzado.padre = ropa
        calzado.save(update_fields=["padre"])


class Migration(migrations.Migration):
    dependencies = [("pools", "0021_borrador_y_precio_envio")]

    operations = [migrations.RunPython(separar, volver)]
