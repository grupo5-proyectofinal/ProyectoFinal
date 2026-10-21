from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import (
    PasswordResetTokenGenerator,
    default_token_generator,
)
from django.db.models import Avg, Count
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from notificaciones import correo
from pools.models import Pool, Resena

User = get_user_model()


class VerificacionEmailTokenGenerator(PasswordResetTokenGenerator):
    """Token del link de verificación: distinto al de restablecer (otro salt) y de
    un solo uso, porque el hash cambia cuando la cuenta queda verificada."""

    key_salt = "poolshop.users.VerificacionEmailTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.email_verificado}{timestamp}"


verificacion_token_generator = VerificacionEmailTokenGenerator()


def _uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def _usuario_de_uid(uidb64):
    try:
        return User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return None


def _vigencia():
    dias = max(round(settings.PASSWORD_RESET_TIMEOUT / 86400), 1)
    return "1 día" if dias == 1 else f"{dias} días"


def _enviar_mail_reset(user):
    token = default_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL}/restablecer?uid={_uid(user)}&token={token}"
    correo.enviar([correo.armar(
        user,
        "Restablecé tu contraseña",
        "restablecer",
        {"boton_url": link, "boton_texto": "Definir contraseña nueva"},
    )])


def enviar_verificacion(user):
    """Mail con el link para confirmar el email (transaccional: sale siempre)."""
    token = verificacion_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL}/verificar-email?uid={_uid(user)}&token={token}"
    correo.enviar([correo.armar(
        user,
        "Confirmá tu email para activar tu cuenta de PoolShop",
        "verificar_email",
        {"boton_url": link, "boton_texto": "Confirmar mi email", "vigencia": _vigencia()},
    )])


def _enviar_bienvenida(user):
    correo.enviar([correo.armar(
        user,
        "¡Bienvenido/a a PoolShop!",
        "bienvenida",
        {"boton_url": f"{settings.FRONTEND_URL}/pools", "boton_texto": "Explorar pools"},
    )])


def _enviar_clave_cambiada(user):
    ahora = timezone.localtime().strftime("%d/%m/%Y a las %H:%M")
    correo.enviar([correo.armar(
        user,
        "Tu contraseña de PoolShop cambió",
        "clave_cambiada",
        {
            "fecha": ahora,
            "boton_url": f"{settings.FRONTEND_URL}/recuperar",
            "boton_texto": "No fui yo: restablecer",
        },
    )])


# Qué avisos recibe el usuario y si además le llegan por mail (las edita en /auth/me/).
PREFERENCIAS_NOTIFICACION = (
    "notificar_estados",
    "notificar_mensajes",
    "notificar_miembros",
    "notificar_por_email",
)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "dni",
            "telefono",
            "genero",
            "direccion",
            "ciudad",
            "foto",
            "password",
            "password2",
        )

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password2": "Las contraseñas no coinciden."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "dni",
            "telefono",
            "genero",
            "direccion",
            "ciudad",
            "foto",
            "is_staff",
            "email_verificado",
            *PREFERENCIAS_NOTIFICACION,
        )
        read_only_fields = fields


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "telefono",
            "genero",
            "direccion",
            "ciudad",
            "foto",
            *PREFERENCIAS_NOTIFICACION,
        )


class UsuarioPerfilPublicoSerializer(serializers.ModelSerializer):
    """Perfil público: solo datos no sensibles + pools en común con quien pide."""

    antiguedad = serializers.SerializerMethodField()
    pools_en_comun = serializers.SerializerMethodField()
    pools_creados = serializers.SerializerMethodField()
    pools_unidos = serializers.SerializerMethodField()
    puntaje_promedio = serializers.SerializerMethodField()
    cantidad_resenas = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "foto",
            "ciudad",
            "antiguedad",
            "pools_en_comun",
            "pools_creados",
            "pools_unidos",
            "puntaje_promedio",
            "cantidad_resenas",
        )
        read_only_fields = fields

    def _resumen_resenas(self, obj):
        """Promedio y cantidad de reseñas recibidas, en una sola consulta por perfil."""
        if not hasattr(obj, "_resumen_resenas"):
            obj._resumen_resenas = Resena.objects.filter(destinatario=obj).aggregate(
                promedio=Avg("puntaje"), cantidad=Count("id")
            )
        return obj._resumen_resenas

    def get_puntaje_promedio(self, obj):
        promedio = self._resumen_resenas(obj)["promedio"]
        return round(float(promedio), 1) if promedio is not None else None

    def get_cantidad_resenas(self, obj):
        return self._resumen_resenas(obj)["cantidad"]

    def get_antiguedad(self, obj):
        return obj.date_joined.date().isoformat()

    def get_pools_creados(self, obj):
        return obj.pools_creados.count()

    def get_pools_unidos(self, obj):
        return obj.memberships.count()

    def get_pools_en_comun(self, obj):
        """Pools en los que participan tanto `obj` como quien pide (o [])."""
        request = self.context.get("request")
        quien = getattr(request, "user", None)
        if quien is None or not quien.is_authenticated or quien.id == obj.id:
            return []
        en_comun = self._ids_participante(obj) & self._ids_participante(quien)
        return list(
            Pool.objects.filter(id__in=en_comun)
            .order_by("titulo")
            .values("id", "titulo")
        )

    @staticmethod
    def _ids_participante(user):
        creados = set(user.pools_creados.values_list("id", flat=True))
        unidos = set(user.memberships.values_list("pool_id", flat=True))
        return creados | unidos


class UsuarioBusquedaSerializer(serializers.ModelSerializer):
    """Resultado de la búsqueda de perfiles: los mismos datos que el perfil público."""

    class Meta:
        model = User
        fields = ("id", "username", "foto", "ciudad")
        read_only_fields = fields


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "dni",
            "telefono",
            "genero",
            "direccion",
            "ciudad",
            "foto",
            "is_active",
            "is_staff",
        )
        read_only_fields = fields


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "telefono",
            "genero",
            "direccion",
            "ciudad",
            "foto",
            "is_active",
        )

    def validate_is_active(self, value):
        # Self-lockout: un admin no puede desactivar su propia cuenta. El
        # BooleanField ya coaccionó el input, así que `value` es bool.
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        if (
            actor is not None
            and self.instance is not None
            and self.instance.pk == actor.pk
            and value is False
        ):
            raise serializers.ValidationError("No podés desactivar tu propia cuenta.")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    # Sin EmailField: un email malformado no debe romper la neutralidad; se trata
    # como "no existe" (200 sin envío). La búsqueda es case-insensitive.
    email = serializers.CharField()

    def save(self, **kwargs):
        # No hay instancia que crear; se envía el mail (si la cuenta existe) y se
        # devuelve el usuario o None. La vista ignora el retorno.
        user = User.objects.filter(email__iexact=self.validated_data["email"]).first()
        if user is not None:
            _enviar_mail_reset(user)
        return user


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password2": "Las contraseñas no coinciden."}
            )
        user = self._obtener_usuario(attrs["uid"])
        if user is None or not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError(
                {"detail": "El enlace de restablecimiento es inválido o expiró."}
            )
        attrs["user"] = user
        return attrs

    def _obtener_usuario(self, uidb64):
        return _usuario_de_uid(uidb64)

    def create(self, validated_data):
        # set_password cambia el hash -> el token usado queda inválido (un solo uso).
        # Usar el link del mail prueba que el email es suyo: queda verificado.
        user = validated_data["user"]
        user.set_password(validated_data["password"])
        user.email_verificado = True
        user.save()
        _enviar_clave_cambiada(user)
        return user


class EmailNoVerificado(exceptions.APIException):
    status_code = 403
    default_detail = (
        "Tenés que confirmar tu email antes de ingresar. Revisá tu casilla "
        "(también spam) o pedí otro enlace."
    )
    default_code = "email_no_verificado"


class LoginSerializer(TokenObtainPairSerializer):
    """Login por email que además exige el email verificado (403 si falta)."""

    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.email_verificado:
            raise EmailNoVerificado()
        return data


class VerificarEmailSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = _usuario_de_uid(attrs["uid"])
        if user is None or not verificacion_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError(
                {"detail": "El enlace de verificación es inválido, venció o ya fue usado."}
            )
        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.email_verificado = True
        user.save(update_fields=["email_verificado"])
        _enviar_bienvenida(user)
        return user


class ReenviarVerificacionSerializer(serializers.Serializer):
    # Mismo criterio que el reset: respuesta neutra, sin enumerar cuentas.
    email = serializers.CharField()

    def save(self, **kwargs):
        user = User.objects.filter(
            email__iexact=self.validated_data["email"], email_verificado=False
        ).first()
        if user is not None:
            enviar_verificacion(user)
        return user


class BajaEmailsSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate_token(self, value):
        user = correo.usuario_de_baja(value)
        if user is None:
            raise serializers.ValidationError("El enlace para darte de baja no es válido.")
        return user

    def save(self, **kwargs):
        user = self.validated_data["token"]
        user.notificar_por_email = False
        user.save(update_fields=["notificar_por_email"])
        return user
