from django.contrib import admin

from .models import Comparacion, Oferta, ParametroCosto, Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "dominio", "estado", "verificado", "provincia")
    list_filter = ("estado", "verificado", "provincia")
    search_fields = ("nombre", "dominio")


admin.site.register(ParametroCosto)
admin.site.register(Comparacion)
admin.site.register(Oferta)
