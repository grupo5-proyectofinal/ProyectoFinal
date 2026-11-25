from django.contrib import admin

from .models import Category, Membership, Pool, PoolImage

admin.site.register(Category)
admin.site.register(Pool)
admin.site.register(PoolImage)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("usuario", "pool", "cantidad", "pago_estado", "recepcion_confirmada")
    list_filter = ("pago_estado",)
    readonly_fields = ("pago_enviado", "pago_revisado", "recepcion_confirmada")
