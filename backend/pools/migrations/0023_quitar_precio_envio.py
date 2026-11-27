from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("pools", "0022_calzado_categoria")]

    operations = [migrations.RemoveField(model_name="pool", name="precio_envio")]
