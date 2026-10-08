from django.db import migrations


def actualizar_categorias(apps, schema_editor):
    """Alta de "Higiene personal", reasignación de "Alimentos" a "Otros" y baja."""
    Category = apps.get_model("pools", "Category")
    Pool = apps.get_model("pools", "Pool")
    otros, _ = Category.objects.get_or_create(nombre="Otros")
    Category.objects.get_or_create(nombre="Higiene personal")
    Pool.objects.filter(categoria__nombre="Alimentos").update(categoria_id=otros.pk)
    Category.objects.filter(nombre="Alimentos").delete()


def revertir_categorias(apps, schema_editor):
    """Recrea "Alimentos"; elimina "Higiene personal" si no tiene pools."""
    Category = apps.get_model("pools", "Category")
    Category.objects.get_or_create(nombre="Alimentos")
    Category.objects.filter(nombre="Higiene personal", pools__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("pools", "0002_seed_categories")]

    operations = [migrations.RunPython(actualizar_categorias, revertir_categorias)]
