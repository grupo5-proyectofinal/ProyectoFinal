"""Carga los datos de la demo: 20 usuarios + un admin y ~45 pools en todos los estados.

    python manage.py poblar_demo            # carga (si ya está cargado, no hace nada)
    python manage.py poblar_demo --borrar   # borra todo lo de la demo

En Render corre al arrancar el servicio cuando `POBLAR_DEMO=true` (ver Dockerfile):
el plan free no tiene Shell.

Cada acción pasa por los endpoints reales (`APIClient` autenticado como el usuario
que la hace): unirse, subir comprobantes, revisar pagos, confirmar, chatear,
calificar, pedir bajas… Así valen todas las reglas de la app y quedan el
historial y las notificaciones como los dejaría un uso real. El ORM solo se usa
para lo que la API no permite: dar de alta usuarios ya verificados, correr una
fecha al pasado (para que un pool caduque) y repartir los timestamps en las
últimas semanas, para que la historia no parezca hecha en un minuto.

Todo corre en una transacción: si algo falla no queda nada a medias. Durante la
carga no sale ningún mail (backend en memoria).
"""

import hashlib
import random
from contextlib import ExitStack
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth.hashers import make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Q
from django.test.utils import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from notificaciones.models import Notificacion
from pools.demo import datos, imagenes
from pools.models import (
    Category,
    EventoPool,
    Membership,
    Mensaje,
    Pool,
    Resena,
    SolicitudBaja,
    cancelar_caducados_sin_respuesta,
)
from pools.variantes import variantes_vigentes
from users.models import User

# Número fijo para el advisory lock de Postgres: dos arranques simultáneos no cargan dos veces.
LLAVE_LOCK = 20261120
API = "/api/v1"
MENSAJES_AL_UNIRSE = [
    "¿Se puede retirar a la tarde?",
    "Retiro yo personalmente, gracias.",
    "",
    "Si sobra cupo después agrego más.",
    "",
    "",
]


def pesos(valor):
    """$ 12.345,00 (formato es-AR)."""
    texto = f"{Decimal(valor):,.2f}"
    return "$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def geocodificar_demo(direccion, ciudad):
    """Coordenadas fijas cerca del centro de la ciudad (sin pedirle nada a Nominatim)."""
    centro = datos.CIUDADES.get(ciudad)
    if centro is None:
        return None
    semilla = int(hashlib.sha256(f"{direccion}|{ciudad}".encode()).hexdigest(), 16)
    dlat = Decimal((semilla % 2400) - 1200) / Decimal(100000)
    dlon = Decimal(((semilla // 2400) % 2400) - 1200) / Decimal(100000)
    return (centro[0] + dlat).quantize(Decimal("0.000001")), (centro[1] + dlon).quantize(
        Decimal("0.000001")
    )


class Command(BaseCommand):
    help = "Carga (o borra con --borrar) los datos de la demo de PoolShop."

    def add_arguments(self, parser):
        parser.add_argument(
            "--borrar",
            action="store_true",
            help="Borra los usuarios de la demo y todo lo que crearon.",
        )

    def handle(self, *args, **options):
        if options["borrar"]:
            self._borrar()
            return
        with ExitStack() as pila:
            pila.enter_context(
                override_settings(
                    ALLOWED_HOSTS=["*"],
                    MAILERS={
                        "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
                    },
                )
            )
            pila.enter_context(mock.patch("pools.views.geocodificar", geocodificar_demo))
            pila.enter_context(transaction.atomic())
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_xact_lock(%s)", [LLAVE_LOCK])
            if User.objects.filter(username=datos.ADMIN["username"]).exists():
                self.stdout.write("La demo ya está cargada: no hago nada.")
                return
            Cargador(self.stdout).cargar()

    def _borrar(self):
        usuarios = User.objects.filter(email__endswith="@" + datos.DOMINIO_EMAIL)
        with transaction.atomic():
            archivos = []
            for usuario in usuarios:
                if usuario.foto:
                    archivos.append(usuario.foto)
            pools = Pool.objects.filter(creador__in=usuarios)
            for pool in pools.prefetch_related("imagenes"):
                archivos.extend(imagen.imagen for imagen in pool.imagenes.all())
            for membership in Membership.objects.filter(
                Q(usuario__in=usuarios) | Q(pool__in=pools)
            ).exclude(comprobante=""):
                archivos.append(membership.comprobante)
            cantidad = usuarios.count()
            usuarios.delete()
            for archivo in archivos:
                nombre, almacen = archivo.name, archivo.storage
                transaction.on_commit(lambda n=nombre, a=almacen: a.delete(n))
        self.stdout.write(f"Borrados {cantidad} usuarios de la demo y sus pools.")


class Cargador:
    def __init__(self, stdout):
        self.stdout = stdout
        self.azar = random.Random(2026)
        self.ahora = timezone.now()
        self.hoy = timezone.localdate()
        self.usuarios = {}
        self.clientes = {}
        self.categorias = {c.nombre: c for c in Category.objects.select_related("padre")}
        self.tramos = []  # (pool, inicio real, fin real, spec)
        self.operacion = 845_211_000

    # ───────────────────────────── utilidades ─────────────────────────────

    def log(self, texto):
        self.stdout.write(texto)

    def _cliente(self, usuario):
        if usuario.pk not in self.clientes:
            cliente = APIClient()
            cliente.force_authenticate(usuario)
            self.clientes[usuario.pk] = cliente
        return self.clientes[usuario.pk]

    def api(self, quien, metodo, ruta, datos_=None, formato="json"):
        usuario = self.usuarios[quien] if isinstance(quien, str) else quien
        respuesta = getattr(self._cliente(usuario), metodo)(
            API + ruta, datos_, format=formato
        )
        if respuesta.status_code >= 400:
            raise CommandError(
                f"{metodo.upper()} {ruta} como {usuario.username}: "
                f"{respuesta.status_code} {getattr(respuesta, 'data', respuesta.content)}"
            )
        return getattr(respuesta, "data", None)

    def nombre(self, clave):
        usuario = self.usuarios[clave]
        return f"{usuario.first_name} {usuario.last_name}"

    # ───────────────────────────── usuarios ─────────────────────────────

    def cargar_usuarios(self):
        clave_hash = make_password(datos.CLAVE_DEMO)  # un solo hash: PBKDF2 es lento
        filas = [("admin", datos.ADMIN)] + [
            (
                clave,
                {
                    "username": f"{nombre}.{apellido}".lower()
                    .translate(str.maketrans("áéíóúñ", "aeioun")),
                    "first_name": nombre,
                    "last_name": apellido,
                    "ciudad": ciudad,
                    "direccion": direccion,
                    "genero": genero,
                    "chat": chat,
                },
            )
            for clave, (nombre, apellido, ciudad, direccion, genero, chat) in datos.USUARIOS.items()
        ]
        dni = 27_431_000
        for indice, (clave, fila) in enumerate(filas):
            dni += 731_219
            while User.objects.filter(dni=str(dni)).exists():
                dni += 1
            caracteristica = datos.CARACTERISTICAS.get(fila["ciudad"], "379")
            usuario = User.objects.create(
                username=fila["username"],
                email=f"{fila['username']}@{datos.DOMINIO_EMAIL}",
                first_name=fila["first_name"],
                last_name=fila["last_name"],
                dni=fila.get("dni") or str(dni),
                telefono=fila.get("telefono")
                or f"+54 {caracteristica} 15{4 + indice % 5}{indice:02d}-{1000 + indice * 377 % 9000}",
                genero=fila["genero"],
                direccion=fila["direccion"],
                ciudad=fila["ciudad"],
                password=clave_hash,
                email_verificado=True,
                # Las direcciones son ficticias: los mails de la demo no salen a ningún lado.
                notificar_por_email=False,
                notificar_mensajes=fila.get("chat", True),
                is_staff=clave == "admin",
                is_superuser=clave == "admin",
            )
            self.usuarios[clave] = usuario
            if clave != "admin":
                # La foto entra por el endpoint de perfil, como desde la app.
                foto = imagenes.avatar(fila["first_name"], fila["last_name"])
                self.api(
                    clave,
                    "patch",
                    "/auth/me/",
                    {"foto": SimpleUploadedFile(f"{usuario.username}.jpg", foto, "image/jpeg")},
                    formato="multipart",
                )
            User.objects.filter(pk=usuario.pk).update(
                date_joined=self.ahora - timedelta(days=50 + self.azar.randint(0, 40)),
                last_login=self.ahora - timedelta(hours=self.azar.randint(1, 72)),
            )
        self.log(f"Usuarios: {len(self.usuarios)} (incluye admin.demo).")

    # ───────────────────────────── pools ─────────────────────────────

    def crear_pool(self, spec):
        creador = self.usuarios[spec["creador"]]
        transferencia = spec["tipo_pago"] == "transferencia"
        cuerpo = {
            "titulo": spec["titulo"],
            "nombre_producto": spec["producto"],
            "descripcion": spec["descripcion"],
            "categoria": self.categorias[spec["categoria"]].pk,
            "enlace": spec["enlace"],
            "precio_unitario": spec["precio"],
            "cantidad_total": spec["total"],
            "cantidad_creador": spec["creador_cantidad"],
            "min_por_integrante": spec["minimo"],
            "fecha_caducidad": (self.hoy + timedelta(days=spec["dias"])).isoformat(),
            "tipo_pago": spec["tipo_pago"],
            "alias_cbu": f"{creador.username}.mp" if transferencia else "",
            "titular_cuenta": f"{creador.first_name} {creador.last_name}" if transferencia else "",
            "direccion": creador.direccion,
            "ciudad": creador.ciudad,
            "atributos": spec.get("atributos", {}),
        }
        if spec["escenario"] == "borrador":
            cuerpo["borrador"] = True
        respuesta = self.api(spec["creador"], "post", "/pools/", cuerpo)
        pool = Pool.objects.get(pk=respuesta["id"])
        categoria = self.categorias[spec["categoria"]]
        padre = categoria.padre.nombre if categoria.padre_id else None
        presentacion = spec["titulo"].split("—", 1)[1].strip() if "—" in spec["titulo"] else ""
        vistas = 2 if len(self.tramos) % 2 == 0 else 1
        for vista in range(vistas):
            contenido = imagenes.portada(
                spec["producto"], categoria.nombre, padre, presentacion, vista=vista
            )
            self.api(
                spec["creador"],
                "post",
                f"/pools/{pool.pk}/imagenes/",
                {
                    "imagen": SimpleUploadedFile(f"{spec['clave']}-{vista + 1}.jpg", contenido,
                                                 "image/jpeg"),
                    "orden": vista,
                },
                formato="multipart",
            )
        return pool

    def unir(self, pool, clave, cantidad, detalle=None, indice=0):
        cuerpo = {
            "cantidad": cantidad,
            "telefono": self.usuarios[clave].telefono,
            "mensaje": MENSAJES_AL_UNIRSE[indice % len(MENSAJES_AL_UNIRSE)],
        }
        if detalle:
            cuerpo["detalle"] = detalle
        self.api(clave, "post", f"/pools/{pool.pk}/unirse/", cuerpo)

    def chatear(self, pool, mensajes):
        for clave, texto in mensajes:
            self.api(clave, "post", f"/pools/{pool.pk}/mensajes/", {"texto": texto})

    def _comprobante(self, pool, clave):
        membership = Membership.objects.get(pool=pool, usuario=self.usuarios[clave])
        self.operacion += self.azar.randint(1_000, 90_000)
        contenido = imagenes.comprobante(
            pesos(pool.precio_unitario * membership.cantidad),
            self.nombre(clave),
            pool.alias_cbu or f"{pool.creador.username}.mp",
            pool.titular_cuenta or f"{pool.creador.first_name} {pool.creador.last_name}",
            timezone.localtime().strftime("%d/%m/%Y %H:%M"),
            f"{self.operacion:012d}",
        )
        self.api(
            clave,
            "post",
            f"/pools/{pool.pk}/comprobante/",
            {"comprobante": SimpleUploadedFile(f"comprobante-{clave}.png", contenido, "image/png")},
            formato="multipart",
        )
        return membership

    def _revisar(self, pool, membership, confirmar, motivo=""):
        cuerpo = {"accion": "confirmar" if confirmar else "rechazar", "motivo": motivo}
        self.api(pool.creador, "post", f"/pools/{pool.pk}/miembros/{membership.pk}/pago/", cuerpo)

    def pagar(self, pool, spec, por_defecto):
        motivo = spec.get("motivo_rechazo", "No se ve el comprobante completo.")
        for miembro in spec["miembros"]:
            clave = miembro[0]
            estado = spec.get("pagos", {}).get(clave, por_defecto)
            if estado == "pendiente":
                continue
            membership = self._comprobante(pool, clave)
            if estado == "confirmado":
                self._revisar(pool, membership, True)
            elif estado in ("rechazado", "reenviado", "reconfirmado"):
                self._revisar(pool, membership, False, motivo)
                if estado in ("reenviado", "reconfirmado"):
                    self._comprobante(pool, clave)
                if estado == "reconfirmado":
                    self._revisar(pool, membership, True)

    def bajas(self, pool, spec):
        for baja in spec.get("bajas", []):
            clave, motivo, final = baja[:3]
            respuesta = self.api(clave, "post", f"/pools/{pool.pk}/bajas/", {"motivo": motivo})
            ruta = f"/pools/{pool.pk}/bajas/{respuesta['id']}"
            if final == "rechazada":
                self.api(pool.creador, "post", f"{ruta}/resolver/",
                         {"accion": "rechazar", "motivo": baja[3]})
            elif final in ("aprobada", "devuelta", "confirmada"):
                self.api(pool.creador, "post", f"{ruta}/resolver/", {"accion": "aprobar"})
                if final in ("devuelta", "confirmada"):
                    self.api(pool.creador, "post", f"{ruta}/devolucion/")
                if final == "confirmada":
                    self.api(clave, "post", f"{ruta}/devolucion/")

    def calificar(self, pool, spec, numero):
        creador = spec["creador"]
        miembros = [m[0] for m in spec["miembros"]]
        base = spec.get("resenas", {}).get(creador, 5)
        especiales = spec.get("comentarios", {})
        usados = {p: 0 for p in datos.COMENTARIOS}

        def comentario(puntaje):
            lista = datos.COMENTARIOS[puntaje]
            texto = lista[(usados[puntaje] + numero) % len(lista)]
            usados[puntaje] += 1
            return texto

        def resena(autor, destinatario, puntaje, texto=None):
            self.api(
                autor,
                "post",
                f"/pools/{pool.pk}/resenas/",
                {
                    "destinatario": self.usuarios[destinatario].pk,
                    "puntaje": puntaje,
                    "comentario": texto if texto is not None else comentario(puntaje),
                },
            )

        for indice, miembro in enumerate(miembros):
            # El último integrante de los pools pares todavía no calificó (se ve "pendiente").
            ultimo = indice == len(miembros) - 1 and len(miembros) > 2
            if numero % 2 == 0 and ultimo and (miembro, creador) not in especiales:
                continue
            if (miembro, creador) in especiales:
                puntaje, texto = especiales[(miembro, creador)]
                resena(miembro, creador, puntaje, texto)
            else:
                puntaje = base if base != 4 else (4 if indice % 2 == 0 else 5)
                resena(miembro, creador, puntaje)
        for indice, miembro in enumerate(miembros):
            resena(creador, miembro, 4 if indice % 3 == 2 else 5)
        if len(miembros) >= 2:
            resena(miembros[0], miembros[1], 5)
            resena(miembros[1], miembros[0], 5, "¡Gracias por la buena onda!")

    def vencer(self, pool, dias):
        """Corre la fecha al pasado y deja que la app procese el vencimiento."""
        Pool.objects.filter(pk=pool.pk).update(fecha_caducidad=self.hoy - timedelta(days=dias))
        pool.refresh_from_db()
        pool.caducar(self.hoy)

    def ejecutar(self, spec, numero):
        inicio = timezone.now()
        pool = self.crear_pool(spec)
        escenario = spec["escenario"]
        for indice, miembro in enumerate(spec["miembros"]):
            clave, cantidad = miembro[0], miembro[1]
            detalle = miembro[2] if len(miembro) > 2 else None
            self.unir(pool, clave, cantidad, detalle, indice + numero)
        for clave, cantidad in spec.get("salen", []):
            self.unir(pool, clave, cantidad)
            self.api(clave, "delete", f"/pools/{pool.pk}/salir/")
        for clave, cantidad in spec.get("cambios", []):
            self.api(clave, "patch", f"/pools/{pool.pk}/mi-membresia/", {"cantidad": cantidad})
        if spec.get("editar"):
            self.api(spec["creador"], "patch", f"/pools/{pool.pk}/", spec["editar"])

        chat = spec.get("chat", [])
        mitad = (len(chat) + 1) // 2
        if escenario in ("listo", "abierto_baja", "en_curso", "finalizado", "cancelado_listo"):
            pool.refresh_from_db()
            if pool.estado != Pool.Estado.LISTO:
                raise CommandError(f"{spec['clave']}: esperaba listo y quedó {pool.estado}.")
            self.chatear(pool, chat[:mitad])
            por_defecto = "pendiente" if escenario in ("listo", "cancelado_listo") else "confirmado"
            self.pagar(pool, spec, por_defecto)
            if escenario in ("listo", "abierto_baja"):
                self.chatear(pool, chat[mitad:])
                self.bajas(pool, spec)
            elif escenario == "cancelado_listo":
                self.chatear(pool, chat[mitad:])
                self.api(pool.creador, "post", f"/pools/{pool.pk}/cancelar/")
                for clave, final in spec.get("devoluciones", {}).items():
                    solicitud = SolicitudBaja.objects.get(pool=pool, usuario=self.usuarios[clave])
                    ruta = f"/pools/{pool.pk}/bajas/{solicitud.pk}/devolucion/"
                    self.api(pool.creador, "post", ruta)
                    if final == "confirmada":
                        self.api(clave, "post", ruta)
            else:
                self.api(pool.creador, "post", f"/pools/{pool.pk}/confirmar/")
                self.bajas(pool, spec)
                self.chatear(pool, chat[mitad:])
                recepciones = (
                    [m[0] for m in spec["miembros"]]
                    if escenario == "finalizado"
                    else spec.get("recepciones", [])
                )
                for clave in recepciones:
                    self.api(clave, "post", f"/pools/{pool.pk}/recepcion/")
                if escenario == "finalizado":
                    self.api(pool.creador, "post", f"/pools/{pool.pk}/finalizar/")
                    self.calificar(pool, spec, numero)
        elif escenario in ("caducado", "reconfirmacion"):
            self.vencer(pool, spec.get("vencio_hace", 1))
            if escenario == "reconfirmacion":
                nueva = self.hoy + timedelta(days=spec["extender_dias"])
                self.api(pool.creador, "post", f"/pools/{pool.pk}/extender/",
                         {"fecha_caducidad": nueva.isoformat()})
                for clave, seguir in spec.get("respuestas", []):
                    self.api(clave, "post", f"/pools/{pool.pk}/reconfirmar/", {"seguir": seguir})
        elif escenario == "cancelado_vencido":
            self.vencer(pool, spec["vencio_hace"])
        elif escenario == "cancelado_abierto":
            self.api(pool.creador, "post", f"/pools/{pool.pk}/cancelar/")
        elif escenario == "cancelado_sin_respuesta":
            self.vencer(pool, spec["vencio_hace"])
            cancelar_caducados_sin_respuesta(self.hoy)

        pool.refresh_from_db()
        self.tramos.append((pool, inicio, timezone.now(), spec))
        return pool

    def sumar_a_reales(self):
        """Algunos usuarios demo se suman a los pools reales que siguen abiertos."""
        demo = {u.pk for u in self.usuarios.values()}
        reales = Pool.objects.filter(
            estado=Pool.Estado.ABIERTO, fecha_caducidad__gte=self.hoy
        ).exclude(creador__in=demo)
        cantidad = 0
        for pool in reales:
            for clave in datos.SUMAN_A_REALES:
                pool.refresh_from_db()
                usuario = self.usuarios[clave]
                unidades = pool.min_por_integrante
                if pool.disponible - unidades < 1 or pool.es_participante(usuario):
                    continue
                variantes = variantes_vigentes(pool)
                detalle = (
                    [{"atributos": {n: o[0] for n, o in variantes.items()}, "cantidad": unidades}]
                    if variantes
                    else None
                )
                self.unir(pool, clave, unidades, detalle, cantidad)
                cantidad += 1
                if cantidad % 3 == 0:
                    break
        self.log(f"Uniones a pools reales: {cantidad}.")

    # ───────────────────────────── tiempos ─────────────────────────────

    def repartir_tiempos(self):
        """Lleva lo hecho en segundos a una línea de tiempo de días o semanas."""
        for pool, inicio_real, fin_real, spec in self.tramos:
            inicio = self.ahora - timedelta(days=spec["hace"])
            fin = self.ahora - timedelta(days=spec["hasta"])
            duracion_real = max((fin_real - inicio_real).total_seconds(), 1)

            def mapear(momento, inicio=inicio, fin=fin, inicio_real=inicio_real,
                       duracion_real=duracion_real):
                if momento is None:
                    return None
                fraccion = min(max((momento - inicio_real).total_seconds() / duracion_real, 0), 1)
                return inicio + (fin - inicio) * fraccion

            Pool.objects.filter(pk=pool.pk).update(creado=inicio, actualizado=fin,
                                                   vistas=spec["vistas"])
            for evento in EventoPool.objects.filter(pool=pool):
                EventoPool.objects.filter(pk=evento.pk).update(creado=mapear(evento.creado))
            for mensaje in Mensaje.objects.filter(pool=pool):
                Mensaje.objects.filter(pk=mensaje.pk).update(creado=mapear(mensaje.creado))
            for resena in Resena.objects.filter(pool=pool):
                Resena.objects.filter(pk=resena.pk).update(creado=mapear(resena.creado))
            for membership in Membership.objects.filter(pool=pool):
                Membership.objects.filter(pk=membership.pk).update(
                    creado=mapear(membership.creado),
                    actualizado=mapear(membership.actualizado),
                    pago_enviado=mapear(membership.pago_enviado),
                    pago_revisado=mapear(membership.pago_revisado),
                    recepcion_confirmada=mapear(membership.recepcion_confirmada),
                    reconfirmado=mapear(membership.reconfirmado),
                )
            for solicitud in SolicitudBaja.objects.filter(pool=pool):
                SolicitudBaja.objects.filter(pk=solicitud.pk).update(
                    creado=mapear(solicitud.creado),
                    resuelto=mapear(solicitud.resuelto),
                    devuelto=mapear(solicitud.devuelto),
                    confirmado=mapear(solicitud.confirmado),
                )
            for notificacion in Notificacion.objects.filter(pool=pool):
                Notificacion.objects.filter(pk=notificacion.pk).update(
                    creado=mapear(notificacion.creado),
                    actualizado=mapear(notificacion.actualizado),
                )
            # Los pools que ya terminaron tienen la fecha de su momento, no la de hoy.
            if pool.estado in (Pool.Estado.EN_CURSO, Pool.Estado.FINALIZADO) or (
                pool.estado == Pool.Estado.CANCELADO
                and spec["escenario"] in ("cancelado_abierto", "cancelado_listo")
            ):
                fecha = (inicio + timedelta(days=spec["dias"])).date()
                Pool.objects.filter(pk=pool.pk).update(fecha_caducidad=fecha)

        # Lo viejo ya se leyó; quedan sin leer las novedades de los últimos días y,
        # como mínimo, las cuatro más recientes de cada uno (la campanita tiene número).
        for usuario in self.usuarios.values():
            recientes = list(
                Notificacion.objects.filter(usuario=usuario).values_list("pk", flat=True)[:4]
            )
            Notificacion.objects.filter(
                usuario=usuario, actualizado__lt=self.ahora - timedelta(days=3)
            ).exclude(pk__in=recientes).update(leida=True)

    # ───────────────────────────── orquestación ─────────────────────────────

    def cargar(self):
        self.cargar_usuarios()
        for numero, spec in enumerate(datos.POOLS):
            pool = self.ejecutar(spec, numero)
            self.log(f"  [{pool.estado:>14}] {pool.titulo}")
        self.sumar_a_reales()
        self.repartir_tiempos()
        resumen = ", ".join(
            f"{estado}: {Pool.objects.filter(creador__in=self.usuarios.values(), estado=estado).count()}"
            for estado in Pool.Estado.values
        )
        self.log(f"Pools de la demo por estado → {resumen}.")
        self.log(f"Listo. Ingresá con cualquier usuario demo y la clave {datos.CLAVE_DEMO}.")
