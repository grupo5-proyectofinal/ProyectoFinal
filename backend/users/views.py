from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from notificaciones import correo
from pools.models import Resena
from pools.serializers import ResenaSerializer

from .baja import dar_de_baja, pools_que_impiden_baja
from .serializers import (
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    BajaCuentaSerializer,
    BajaEmailsSerializer,
    CorregirIdentidadSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    ReenviarVerificacionSerializer,
    RegisterSerializer,
    UpdateProfileSerializer,
    UsuarioBusquedaSerializer,
    UsuarioPerfilPublicoSerializer,
    VerificarEmailSerializer,
    enviar_mail_restablecer,
    enviar_verificacion,
)
from .throttling import (
    limpiar_fallos_login,
    login_bloqueado,
    registrar_fallo_login,
)

# Mínimo de caracteres para buscar perfiles: evita listar a todos con "a".
BUSQUEDA_MINIMA = 2


class IPRateThrottle(SimpleRateThrottle):
    """Límite por IP que no se saltea con un token válido."""

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class PasswordResetRateThrottle(IPRateThrottle):
    scope = "password_reset"


class VerificacionEmailRateThrottle(IPRateThrottle):
    scope = "verificacion_email"


def _tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class LoginRateThrottle(IPRateThrottle):
    """Límite por IP de todos los pedidos de login (acertados o no)."""

    scope = "login"


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = (LoginRateThrottle,)

    def post(self, request, *args, **kwargs):
        # El límite por cuenta cuenta solo los fallos: una contraseña correcta
        # nunca queda bloqueada por los intentos de otra persona. El contador
        # se consulta después del fallo y se limpia al entrar bien.
        identificador = str(request.data.get("email") or "").strip()
        try:
            response = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            if identificador:
                registrar_fallo_login(identificador)
                if login_bloqueado(identificador):
                    raise Throttled()
            raise
        if response.status_code == 200 and identificador:
            limpiar_fallos_login(identificador)
        return response


class RegistroRateThrottle(IPRateThrottle):
    scope = "registro"


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (RegistroRateThrottle,)

    def create(self, request, *args, **kwargs):
        # Sin autologin: se ingresa después con usuario (o email) y contraseña.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verificar = settings.VERIFICACION_EMAIL_OBLIGATORIA
        # Con la verificación apagada la cuenta queda habilitada al crearse.
        user = serializer.save(email_verificado=not verificar)
        if verificar:
            enviar_verificacion(user)
            detail = f"Te enviamos un mail a {user.email} para confirmar tu cuenta."
        else:
            detail = (
                "Tu cuenta está creada. Ya podés iniciar sesión con tu usuario "
                "o email y tu contraseña."
            )
        return Response(
            {
                "user": ProfileSerializer(user, context=self.get_serializer_context()).data,
                "verificacion_pendiente": verificar,
                "detail": detail,
            },
            status=status.HTTP_201_CREATED,
        )


class VerificarEmailView(generics.CreateAPIView):
    """Confirma el email con el link del mail y deja la sesión iniciada."""

    serializer_class = VerificarEmailSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "user": ProfileSerializer(user, context=self.get_serializer_context()).data,
                **_tokens(user),
            }
        )


class ReenviarVerificacionView(generics.CreateAPIView):
    serializer_class = ReenviarVerificacionSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (VerificacionEmailRateThrottle,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": "Si la cuenta existe y está pendiente, te enviamos un nuevo "
                "enlace de verificación."
            }
        )


def _correo_enmascarado(email):
    """j***@dominio.com: alcanza para reconocer la cuenta sin exponerla."""
    nombre, _, dominio = (email or "").partition("@")
    if not nombre or not dominio:
        return "***"
    return f"{nombre[:1]}***@{dominio}"


class BajaEmailsView(generics.CreateAPIView):
    """Baja de las notificaciones por mail desde el link del correo (sin sesión)."""

    serializer_class = BajaEmailsSerializer
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        # La pantalla muestra a qué cuenta pertenece el enlace antes de confirmar.
        usuario = correo.usuario_de_baja(request.query_params.get("token", ""))
        if usuario is None:
            return Response(
                {"detail": "El enlace para darte de baja no es válido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"email": _correo_enmascarado(usuario.email)})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        return Response(
            {
                "detail": "Listo: ya no te vamos a mandar notificaciones por mail. "
                "Podés volver a activarlas desde Notificaciones.",
                "email": _correo_enmascarado(usuario.email),
            }
        )


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "patch", "head", "options")

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ProfileSerializer
        return UpdateProfileSerializer

    def get_object(self):
        return self.request.user


class BajaCuentaThrottle(UserRateThrottle):
    # Pide la contraseña: sin límite serviría para adivinarla con una sesión robada.
    scope = "baja_cuenta"


class BajaCuentaView(generics.GenericAPIView):
    """Da de baja la cuenta propia (anonimiza; ver users/baja.py).

    No se puede con pools activos (que organiza o a los que está unido): se
    devuelven en `pools` para que el usuario sepa cuáles cerrar o abandonar.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = BajaCuentaSerializer
    throttle_classes = (BajaCuentaThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            usuario = get_user_model().objects.select_for_update().get(pk=request.user.pk)
            activos = pools_que_impiden_baja(usuario)
            if activos:
                return Response(
                    {
                        "detail": (
                            "Antes de eliminar tu cuenta tenés que cerrar o salir de "
                            "tus pools activos."
                        ),
                        "pools": [
                            {
                                "id": p["id"],
                                "titulo": p["titulo"],
                                "estado": p["estado"],
                                "organizador": p["creador_id"] == usuario.pk,
                            }
                            for p in activos
                        ],
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            dar_de_baja(usuario)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CorregirIdentidadThrottle(UserRateThrottle):
    # Pide la contraseña: el límite evita usarla como oráculo con una sesión robada.
    scope = "corregir_identidad"


class CorregirIdentidadView(generics.GenericAPIView):
    """Corrige el DNI o el email de la cuenta, con la contraseña actual.

    Si cambia el email, la cuenta vuelve a quedar sin verificar, se manda el
    link al nuevo domicilio y se renuevan los tokens de la sesión actual.
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = CorregirIdentidadSerializer
    throttle_classes = (CorregirIdentidadThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                usuario, email_cambiado = serializer.save()
        except IntegrityError:
            return Response(
                {"detail": "Ese DNI o email ya está en uso."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = {
            "detail": (
                f"Guardamos el cambio. Te enviamos un mail a {usuario.email} para confirmarlo."
                if email_cambiado
                else "DNI actualizado."
            ),
            "email_cambiado": email_cambiado,
            "user": ProfileSerializer(usuario, context=self.get_serializer_context()).data,
        }
        if email_cambiado:
            # La sesión actual sigue: se invalidan los refresh viejos y se emiten
            # tokens nuevos para que el cambio de email no cierre la app.
            pendientes = OutstandingToken.objects.filter(user=usuario).exclude(
                blacklistedtoken__isnull=False
            )
            BlacklistedToken.objects.bulk_create(
                [BlacklistedToken(token=token) for token in pendientes],
                ignore_conflicts=True,
            )
            refresh = RefreshToken.for_user(usuario)
            data["access"] = str(refresh.access_token)
            data["refresh"] = str(refresh)
        return Response(data)


class UsuarioPerfilPublicoView(generics.RetrieveAPIView):
    """Perfil público de un usuario: sin PII; `pools_en_comun` relativo a quien pide."""

    permission_classes = (AllowAny,)
    serializer_class = UsuarioPerfilPublicoSerializer
    # Las cuentas dadas de baja no tienen perfil público.
    queryset = get_user_model().objects.filter(is_active=True)


class UsuarioBusquedaView(generics.ListAPIView):
    """Búsqueda pública de perfiles por nombre de usuario (`?q=`).

    Solo por `username`, que es lo que el perfil público muestra: buscar por
    nombre, email o DNI permitiría deducir datos que el perfil no expone.
    """

    permission_classes = (AllowAny,)
    serializer_class = UsuarioBusquedaSerializer

    def get_queryset(self):
        termino = self.request.query_params.get("q", "").strip()
        usuarios = get_user_model().objects.filter(is_active=True)
        if len(termino) < BUSQUEDA_MINIMA:
            return usuarios.none()
        return usuarios.filter(username__icontains=termino).order_by("username")


class UsuarioResenasView(generics.ListAPIView):
    """Reseñas que recibió un usuario, lo más nuevo primero (paginado)."""

    permission_classes = (AllowAny,)
    serializer_class = ResenaSerializer

    def get_queryset(self):
        usuario = get_object_or_404(get_user_model(), pk=self.kwargs["pk"])
        return Resena.objects.filter(destinatario=usuario).select_related("autor", "pool")


class PasswordResetRequestView(generics.CreateAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (PasswordResetRateThrottle,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Respuesta neutra: misma para cuenta existente o no (sin enumeración).
        return Response(
            {
                "detail": "Si el email corresponde a una cuenta, te enviamos un "
                "enlace para restablecer la contraseña."
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(generics.CreateAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Contraseña actualizada. Ya podés iniciar sesión."},
            status=status.HTTP_200_OK,
        )


class UsuarioFilter(filters.FilterSet):
    q = filters.CharFilter(method="filtrar_q")
    is_active = filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = get_user_model()
        fields = ()

    def filtrar_q(self, queryset, name, value):
        return queryset.filter(
            Q(email__icontains=value)
            | Q(username__icontains=value)
            | Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
        )


class AdminUserListView(generics.ListCreateAPIView):
    permission_classes = (IsAdminUser,)
    filterset_class = UsuarioFilter
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "date_joined",
        "id",
    )
    ordering = ("-id",)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return RegisterSerializer
        return AdminUserSerializer

    def get_queryset(self):
        return get_user_model().objects.all()

    def create(self, request, *args, **kwargs):
        # Alta reutilizando el registro, pero sin autologin: no se emiten tokens
        # y la respuesta es el perfil admin (sin password). is_staff queda False
        # porque RegisterSerializer no lo expone en sus fields.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = AdminUserSerializer(user, context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED)


class AdminRestablecerClaveThrottle(UserRateThrottle):
    scope = "admin_restablecer_clave"


class AdminRestablecerClaveView(generics.GenericAPIView):
    """El staff le manda a un usuario el mail para definir una contraseña nueva.

    No ve ni elige la contraseña: el usuario la define con el link del mail, igual
    que en "Olvidé mi contraseña".
    """

    permission_classes = (IsAdminUser,)
    throttle_classes = (AdminRestablecerClaveThrottle,)
    queryset = get_user_model().objects.all()

    def post(self, request, *args, **kwargs):
        usuario = self.get_object()
        if not usuario.is_active:
            return Response(
                {"detail": "La cuenta está desactivada: activala antes de restablecer la contraseña."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        enviar_mail_restablecer(usuario)
        return Response({"detail": f"Le enviamos a {usuario.email} el mail para restablecer la contraseña."})


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAdminUser,)
    queryset = get_user_model().objects.all()
    http_method_names = ("get", "patch", "head", "options")

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AdminUserSerializer
        return AdminUserUpdateSerializer
