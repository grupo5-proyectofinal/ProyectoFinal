from django.contrib import admin

from .models import Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "dominio", "estado", "verificado", "provincia")
    list_filter = ("estado", "verificado", "provincia")
    search_fields = ("nombre", "dominio")

