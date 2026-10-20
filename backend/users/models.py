from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    dni = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=30, blank=True)
    genero = models.CharField(max_length=30, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    foto = models.ImageField(upload_to="users/", blank=True)
    # Preferencias de notificación: qué avisos recibe y si además le llegan por mail.
    notificar_estados = models.BooleanField(default=True)
    notificar_mensajes = models.BooleanField(default=True)
    notificar_miembros = models.BooleanField(default=True)
    notificar_por_email = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]
