from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class PoolShopUserAdmin(UserAdmin):
    """User en el admin de Django (antes no estaba registrado)."""

    list_display = ("email", "username", "first_name", "last_name", "is_active", "is_staff")
    search_fields = ("email", "username", "first_name", "last_name", "dni")
    ordering = ("email",)
    fieldsets = (
        *UserAdmin.fieldsets,
        (
            "PoolShop",
            {
                "fields": (
                    "dni",
                    "telefono",
                    "genero",
                    "direccion",
                    "ciudad",
                    "foto",
                    "email_verificado",
                    "notificar_estados",
                    "notificar_mensajes",
                    "notificar_miembros",
                    "notificar_pagos",
                    "notificar_por_email",
                )
            },
        ),
    )
