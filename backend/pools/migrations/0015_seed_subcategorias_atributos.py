from django.db import migrations

# Iteración 3: "Agregar atributos en base al producto según la categoría.
# Ej. Ropa > Remera > Talle, Color". Los atributos del padre los heredan sus hijos.
TALLES_ROPA = ["XS", "S", "M", "L", "XL", "XXL"]
TALLES_PANTALON = ["36", "38", "40", "42", "44", "46", "48"]
TALLES_CALZADO = [str(n) for n in range(34, 46)]
COLORES = ["Negro", "Blanco", "Gris", "Azul", "Rojo", "Verde", "Beige", "Rosa"]

# {padre: {"atributos": {nombre: opciones}, "hijos": {hijo: {nombre: opciones}}}}
CATALOGO = {
    "Ropa": {
        "atributos": {"Color": COLORES},
        "hijos": {
            "Remera": {"Talle": TALLES_ROPA},
            "Buzo": {"Talle": TALLES_ROPA},
            "Pantalón": {"Talle": TALLES_PANTALON},
            "Calzado": {"Talle": TALLES_CALZADO},
        },
    },
    "Higiene personal": {
        "atributos": {},
        "hijos": {"Perfume": {"Contenido": ["30 ml", "50 ml", "100 ml", "200 ml"]}},
    },
    "Electrónica": {
        "atributos": {},
        "hijos": {"Accesorios": {"Color": COLORES}},
    },
}


def sembrar(apps, schema_editor):
    Category = apps.get_model("pools", "Category")
    Atributo = apps.get_model("pools", "AtributoCategoria")

    def atributos(categoria, definicion):
        for orden, (nombre, opciones) in enumerate(definicion.items()):
            Atributo.objects.update_or_create(
                categoria=categoria, nombre=nombre, defaults={"opciones": opciones, "orden": orden}
            )

    for nombre_padre, datos in CATALOGO.items():
        padre, _ = Category.objects.get_or_create(nombre=nombre_padre)
        atributos(padre, datos["atributos"])
        for nombre_hijo, definicion in datos["hijos"].items():
            hijo, _ = Category.objects.get_or_create(
                nombre=nombre_hijo, defaults={"padre": padre}
            )
            if hijo.padre_id != padre.pk:
                hijo.padre = padre
                hijo.save(update_fields=["padre"])
            atributos(hijo, definicion)


def deshacer(apps, schema_editor):
    """Borra lo sembrado que nadie usa; las subcategorías con pools quedan."""
    Category = apps.get_model("pools", "Category")
    Atributo = apps.get_model("pools", "AtributoCategoria")
    for nombre_padre, datos in CATALOGO.items():
        for nombre_hijo in datos["hijos"]:
            Atributo.objects.filter(categoria__nombre=nombre_hijo).delete()
            Category.objects.filter(nombre=nombre_hijo, pools__isnull=True).delete()
        Atributo.objects.filter(
            categoria__nombre=nombre_padre, nombre__in=list(datos["atributos"])
        ).delete()
    # Postgres difiere los chequeos de FK de los borrados hasta el commit; la
    # migración anterior (0014) altera esas tablas en la misma transacción y
    # falla con "pending trigger events" si quedan pendientes.
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


class Migration(migrations.Migration):
    dependencies = [("pools", "0014_variantes")]

    operations = [migrations.RunPython(sembrar, deshacer)]
