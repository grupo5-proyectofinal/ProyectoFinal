import os
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.deconstruct import deconstructible


@deconstructible
class AlmacenPrivado(FileSystemStorage):
    """Archivos fuera de MEDIA_ROOT (que se sirve público en /media/).

    Lee `PRIVATE_MEDIA_ROOT` en cada acceso (respeta `override_settings` en
    tests). Los archivos se entregan solo desde endpoints con permisos.
    """

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)


def almacen_privado():
    """Storage de los comprobantes: la base si `ARCHIVOS_EN_DB`, si no la carpeta privada.

    Es un callable (no una instancia) para que las migraciones no dependan del
    entorno: `makemigrations` guarda esta función, no el storage elegido.
    """
    if settings.ARCHIVOS_EN_DB:
        from pools.almacen import AlmacenDB

        return AlmacenDB(privado=True)
    return AlmacenPrivado()


class ArchivoAlmacenado(models.Model):
    """Archivo guardado en la base (ver `pools/almacen.py`)."""

    nombre = models.CharField(max_length=255)
    privado = models.BooleanField(default=False)
    contenido = models.BinaryField()
    tamano = models.PositiveIntegerField()
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["nombre", "privado"], name="unique_archivo_almacenado_nombre_privado"
            )
        ]

    def __str__(self):
        return self.nombre


def validar_fecha_caducidad(fecha):
    hoy = timezone.localdate()
    if fecha < hoy:
        raise ValidationError("La fecha de caducidad debe ser futura.")
    if fecha > hoy + timedelta(days=30):
        raise ValidationError("La fecha de caducidad no puede superar los 30 días.")


# Días que tienen los participantes para seguir o salir cuando se extiende el plazo.
DIAS_RECONFIRMACION = 3


class Category(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    # Subcategorías (Ropa > Remera): heredan los atributos del padre.
    padre = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="subcategorias"
    )

    class Meta:
        ordering = ["nombre"]
        verbose_name_plural = "categories"

    def __str__(self):
        return f"{self.padre} > {self.nombre}" if self.padre_id else self.nombre

    def atributos_efectivos(self):
        """Atributos de la categoría y de su padre (Remera hereda los de Ropa).

        Usa el prefetch de `atributos` / `padre__atributos` si está.
        """
        propios = list(self.atributos.all())
        heredados = list(self.padre.atributos.all()) if self.padre_id else []
        nombres = {a.nombre for a in propios}
        # Primero lo propio (Talle de Remera) y después lo heredado (Color de Ropa).
        return propios + [a for a in heredados if a.nombre not in nombres]


class AtributoCategoria(models.Model):
    """Atributo que eligen los integrantes al unirse (Talle, Color, Contenido…).

    `opciones` es la lista de valores posibles; cada pool ofrece un subconjunto.
    """

    categoria = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="atributos")
    nombre = models.CharField(max_length=40)
    opciones = models.JSONField(default=list)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["categoria", "nombre"], name="atributo_unico_por_categoria"
            )
        ]

    def __str__(self):
        return f"{self.categoria}: {self.nombre}"


class Pool(models.Model):
    class TipoPago(models.TextChoices):
        TRANSFERENCIA = "transferencia", "Transferencia"
        SIN_ESPECIFICAR = "sin_especificar", "Sin especificar"

    class Estado(models.TextChoices):
        ABIERTO = "abierto", "Abierto"
        LISTO = "listo", "Listo"
        # Venció la fecha con participantes: el administrador decide si extiende o cancela.
        CADUCADO = "caducado", "Caducado"
        # Se extendió el plazo: cada participante confirma si sigue o sale.
        RECONFIRMACION = "reconfirmacion", "Esperando confirmación"
        EN_CURSO = "en_curso", "En curso"
        FINALIZADO = "finalizado", "Finalizado"
        CANCELADO = "cancelado", "Cancelado"

    titulo = models.CharField(max_length=200)
    nombre_producto = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="pools")
    # Los links de MercadoLibre/Amazon con parámetros pasan de 200 (el default).
    enlace = models.URLField(max_length=2000, blank=True)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_total = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    cantidad_creador = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    min_por_integrante = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    fecha_caducidad = models.DateField(validators=[validar_fecha_caducidad])
    # Variantes que ofrece el creador: {"Talle": ["S", "M"], "Color": ["Negro"]}.
    atributos = models.JSONField(default=dict, blank=True)
    # Objetivo opcional por combinación de variantes:
    # [{"atributos": {"Talle": "S"}, "cantidad": 6}]. Vacío = sin cupo por variante.
    reparto = models.JSONField(default=list, blank=True)
    # Datos para la transferencia: solo los ven los participantes (no el público).
    alias_cbu = models.CharField(max_length=60, blank=True)
    titular_cuenta = models.CharField(max_length=120, blank=True)
    tipo_pago = models.CharField(
        max_length=20, choices=TipoPago.choices, default=TipoPago.SIN_ESPECIFICAR
    )
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTO)
    # Hasta cuándo responden los participantes tras extender el plazo.
    reconfirmacion_hasta = models.DateTimeField(null=True, blank=True)
    creador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pools_creados"
    )
    vistas = models.PositiveIntegerField(default=0)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return self.titulo

    @property
    def disponible(self):
        usado = self.cantidad_creador + sum(m.cantidad for m in self.memberships.all())
        return max(self.cantidad_total - usado, 0)

    def actualizar_estado(self, disponible=None):
        """Mantiene abierto/listo según el disponible; no toca otros estados.

        Devuelve True si cambió el estado (para guardar con update_fields).
        """
        if self.estado not in (self.Estado.ABIERTO, self.Estado.LISTO):
            return False
        valor = self.disponible if disponible is None else disponible
        nuevo = self.Estado.LISTO if valor == 0 else self.Estado.ABIERTO
        if nuevo == self.estado:
            return False
        self.estado = nuevo
        return True

    def pagos_pendientes(self):
        """Memberships cuyo pago todavía no confirmó el creador."""
        return self.memberships.exclude(pago_estado=Membership.PagoEstado.CONFIRMADO)

    def recepciones_pendientes(self):
        """Memberships que todavía no confirmaron haber recibido el producto."""
        return self.memberships.filter(recepcion_confirmada__isnull=True)

    def vencio(self, hoy=None):
        """True si el pool es un abierto cuya fecha ya pasó (la fecha vale todo el día)."""
        return self.estado == self.Estado.ABIERTO and self.fecha_caducidad < (
            hoy or timezone.localdate()
        )

    def caducar(self, hoy=None):
        """Si venció, lo pasa a caducado (con participantes) o lo cancela (sin nadie).

        El update es condicional para no pisar otra transición (p. ej. un
        unirse que lo dejó en listo). True si cambió el estado.
        """
        hoy = hoy or timezone.localdate()
        if not self.vencio(hoy):
            return False
        hay_miembros = self.memberships.exclude(usuario_id=self.creador_id).exists()
        nuevo = self.Estado.CADUCADO if hay_miembros else self.Estado.CANCELADO
        cambiados = Pool.objects.filter(
            pk=self.pk, estado=self.Estado.ABIERTO, fecha_caducidad__lt=hoy
        ).update(estado=nuevo)
        if cambiados == 0:
            return False
        self.estado = nuevo
        # Sin datos cuando se cancela: así lo leen el historial y los tests previos.
        registrar_evento(
            self,
            EventoPool.Tipo.EXPIRADO,
            datos={"estado": nuevo} if nuevo == self.Estado.CADUCADO else None,
        )
        # Import local: notificaciones referencia a Pool y no debe cargarse antes.
        from notificaciones.servicio import notificar_estado

        notificar_estado(self, nuevo, expirado=nuevo == self.Estado.CANCELADO)
        return True

    def resolver_reconfirmacion(self, ahora=None):
        """Cierra la reconfirmación si ya respondieron todos o se acabó el plazo.

        Quita a quienes no respondieron y deja el pool abierto (o listo, si el
        cupo está completo). Bajo lock propio: sirve desde la vista y desde el
        job. True si la cerró.
        """
        ahora = ahora or timezone.now()
        with transaction.atomic():
            pool = Pool.objects.select_for_update().get(pk=self.pk)
            if pool.estado != self.Estado.RECONFIRMACION:
                return False
            sin_respuesta = list(pool.memberships.filter(reconfirmado__isnull=True))
            plazo_cumplido = (
                pool.reconfirmacion_hasta is None or pool.reconfirmacion_hasta <= ahora
            )
            if sin_respuesta and not plazo_cumplido:
                return False
            for membership in sin_respuesta:
                registrar_evento(
                    pool,
                    EventoPool.Tipo.SALIDA,
                    actor=membership.usuario,
                    datos={"cantidad": membership.cantidad, "motivo": "sin_respuesta"},
                )
                membership.delete()
            pool.estado = self.Estado.ABIERTO
            pool.reconfirmacion_hasta = None
            pool.actualizar_estado()
            pool.save(update_fields=["estado", "reconfirmacion_hasta", "actualizado"])
            registrar_evento(
                pool, EventoPool.Tipo.ESTADO, datos={"estado": pool.estado}
            )
            from notificaciones.servicio import notificar_estado

            notificar_estado(pool, pool.estado)
        self.estado = pool.estado
        self.reconfirmacion_hasta = None
        return True

    def es_participante(self, usuario):
        """True si `usuario` es el creador o un miembro del pool."""
        if usuario is None or not usuario.is_authenticated:
            return False
        return self.creador_id == usuario.id or self.memberships.filter(usuario=usuario).exists()


def expirar_vencidos():
    """Procesa los vencimientos y devuelve los pks de los pools abiertos que cambiaron.

    Abiertos vencidos: caducan (con participantes) o se cancelan (sin nadie).
    Reconfirmaciones con el plazo cumplido: se cierran. Idempotente.
    """
    hoy = timezone.localdate()
    vencidos = Pool.objects.filter(estado=Pool.Estado.ABIERTO, fecha_caducidad__lt=hoy)
    cambiados = [pool.pk for pool in vencidos if pool.caducar(hoy)]
    ahora = timezone.now()
    for pool in Pool.objects.filter(
        estado=Pool.Estado.RECONFIRMACION, reconfirmacion_hasta__lte=ahora
    ):
        pool.resolver_reconfirmacion(ahora)
    return cambiados


class PoolImage(models.Model):
    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="imagenes")
    imagen = models.ImageField(upload_to="pools/")
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]

    def __str__(self):
        return f"Imagen {self.pk} de {self.pool}"


class Membership(models.Model):
    class PagoEstado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ENVIADO = "enviado", "Enviado"
        CONFIRMADO = "confirmado", "Confirmado"
        RECHAZADO = "rechazado", "Rechazado"

    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="memberships")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # PII del miembro, aportada al unirse y visible solo para el creador del pool
    # (regla en MembershipSerializer). blank=True: las memberships previas a la
    # feature no tienen estos datos; la obligatoriedad se valida en el boundary.
    # Qué variantes pidió: [{"atributos": {"Talle": "M", "Color": "Negro"}, "cantidad": 2}].
    detalle = models.JSONField(default=list, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    mensaje = models.CharField(max_length=500, blank=True)
    # Pago de la parte del miembro: sube el comprobante y el creador lo revisa.
    pago_estado = models.CharField(
        max_length=20, choices=PagoEstado.choices, default=PagoEstado.PENDIENTE
    )
    comprobante = models.FileField(
        upload_to="comprobantes/%Y/%m/", storage=almacen_privado, blank=True
    )
    pago_motivo_rechazo = models.CharField(max_length=255, blank=True)
    pago_enviado = models.DateTimeField(null=True, blank=True)
    pago_revisado = models.DateTimeField(null=True, blank=True)
    # Cuándo el miembro confirmó que recibió el producto (nulo = todavía no).
    recepcion_confirmada = models.DateTimeField(null=True, blank=True)
    # Cuándo confirmó que sigue tras una extensión de plazo (nulo = sin responder).
    reconfirmado = models.DateTimeField(null=True, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pool", "usuario"], name="unique_membership_pool_usuario")
        ]

    def __str__(self):
        return f"{self.usuario} en {self.pool} ({self.cantidad})"


class SolicitudBaja(models.Model):
    """Un integrante que ya pagó pide salir del pool y que le devuelvan el dinero.

    El administrador la aprueba o la rechaza. Si la aprueba, el integrante sale
    del pool y la devolución se coordina fuera de la app: el administrador marca
    que la hizo y el integrante confirma que la recibió. Guarda la cantidad y el
    monto del momento porque la membresía se borra al aprobar.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        RECHAZADA = "rechazada", "Rechazada"
        APROBADA = "aprobada", "Esperando devolución"
        DEVUELTA = "devuelta", "Devolución realizada"
        CONFIRMADA = "confirmada", "Devolución recibida"

    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="solicitudes_baja")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="solicitudes_baja"
    )
    cantidad = models.PositiveIntegerField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    motivo = models.CharField(max_length=255)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    motivo_rechazo = models.CharField(max_length=255, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    resuelto = models.DateTimeField(null=True, blank=True)
    devuelto = models.DateTimeField(null=True, blank=True)
    confirmado = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado", "-id"]
        constraints = [
            # Una sola solicitud abierta por integrante y pool.
            models.UniqueConstraint(
                fields=["pool", "usuario"],
                condition=models.Q(estado="pendiente"),
                name="unique_baja_pendiente_pool_usuario",
            )
        ]

    def __str__(self):
        return f"Baja de {self.usuario} en {self.pool} ({self.estado})"


class Mensaje(models.Model):
    """Un mensaje del chat del pool, visible para sus integrantes.

    El texto se normaliza y valida en el boundary (`MensajeSerializer`); el
    `max_length` queda como respaldo a nivel de base.
    """

    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="mensajes")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mensajes"
    )
    texto = models.CharField(max_length=1000)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ascendente por id: el chat se lee como conversación y el polling pide
        # "lo nuevo" con `id > desde`.
        ordering = ["id"]
        indexes = [models.Index(fields=["pool", "id"], name="mensaje_pool_id_idx")]

    def __str__(self):
        return f"Mensaje {self.pk} de {self.autor} en {self.pool}"


class EventoPool(models.Model):
    """Un cambio del pool, para el historial que ven sus integrantes.

    `actor` nulo significa que lo hizo el sistema (p. ej. la expiración).
    `datos` guarda solo lo necesario para el texto del evento: nunca PII del
    miembro (teléfono/mensaje).
    """

    class Tipo(models.TextChoices):
        CREADO = "creado", "Creado"
        EDICION = "edicion", "Edición"
        IMAGEN = "imagen", "Imagen"
        UNION = "union", "Unión"
        SALIDA = "salida", "Salida"
        CANTIDAD = "cantidad", "Cantidad"
        ESTADO = "estado", "Estado"
        EXPIRADO = "expirado", "Expirado"
        # Los dos siguientes ya no se generan (se quitó la eliminación de pools); se
        # conservan para mostrar el historial de pools anteriores.
        SOLICITUD_ELIMINACION = "solicitud_eliminacion", "Solicitud de eliminación"
        VOTO_ELIMINACION = "voto_eliminacion", "Voto de eliminación"
        PAGO_ENVIADO = "pago_enviado", "Pago enviado"
        PAGO_CONFIRMADO = "pago_confirmado", "Pago confirmado"
        PAGO_RECHAZADO = "pago_rechazado", "Pago rechazado"
        RECEPCION = "recepcion", "Recepción confirmada"
        EXTENDIDO = "extendido", "Plazo extendido"
        RECONFIRMACION = "reconfirmacion", "Reconfirmación"
        BAJA_SOLICITADA = "baja_solicitada", "Baja solicitada"
        BAJA_APROBADA = "baja_aprobada", "Baja aprobada"
        BAJA_RECHAZADA = "baja_rechazada", "Baja rechazada"
        DEVOLUCION = "devolucion", "Devolución"

    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="eventos")
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="eventos_pool",
    )
    datos = models.JSONField(default=dict, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Lo más nuevo primero: el timeline se lee como un feed.
        ordering = ["-creado", "-id"]

    def __str__(self):
        return f"{self.get_tipo_display()} en {self.pool}"


def registrar_evento(pool, tipo, actor=None, datos=None):
    """Registra un cambio del pool en su historial. `actor=None` es el sistema."""
    return EventoPool.objects.create(pool=pool, tipo=tipo, actor=actor, datos=datos or {})


class Resena(models.Model):
    """La calificación que un participante deja a otro al terminar un pool.

    Una por (pool, autor, destinatario); solo en pools finalizados y entre
    participantes (reglas en `ResenaSerializer`).
    """

    pool = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="resenas")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resenas_escritas"
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resenas_recibidas"
    )
    puntaje = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comentario = models.CharField(max_length=500, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["pool", "autor", "destinatario"], name="unique_resena_pool_autor_destinatario"
            )
        ]

    def __str__(self):
        return f"Reseña de {self.autor} a {self.destinatario} ({self.puntaje})"
