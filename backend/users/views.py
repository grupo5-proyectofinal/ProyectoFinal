from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from pools.models import Resena
from pools.serializers import ResenaSerializer

from .serializers import (
    AdminUserSerializer,
    AdminUserUpdateSerializer,
    BajaEmailsSerializer,
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
    enviar_verificacion,
)

# Mínimo de caracteres para buscar perfiles: evita listar a todos con "a".
BUSQUEDA_MINIMA = 2


class PasswordResetRateThrottle(AnonRateThrottle):
    scope = "password_reset"


class VerificacionEmailRateThrottle(AnonRateThrottle):
    scope = "verificacion_email"


def _tokens(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        # Sin autologin: la cuenta queda pendiente hasta confirmar el email.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save(email_verificado=False)
        enviar_verificacion(user)
        return Response(
            {
                "user": ProfileSerializer(user, context=self.get_serializer_context()).data,
                "verificacion_pendiente": True,
                "detail": f"Te enviamos un mail a {user.email} para confirmar tu cuenta.",
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


class BajaEmailsView(generics.CreateAPIView):
    """Baja de las notificaciones por mail desde el link del correo (sin sesión)."""

    serializer_class = BajaEmailsSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": "Listo: ya no te vamos a mandar notificaciones por mail. "
                "Podés volver a activarlas desde Notificaciones."
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


class UsuarioPerfilPublicoView(generics.RetrieveAPIView):
    """Perfil público de un usuario: sin PII; `pools_en_comun` relativo a quien pide."""

    permission_classes = (AllowAny,)
    serializer_class = UsuarioPerfilPublicoSerializer
    queryset = get_user_model().objects.all()


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
    filter_backends = (DjangoFilterBackend,)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return RegisterSerializer
        return AdminUserSerializer

    def get_queryset(self):
        return get_user_model().objects.all().order_by("-id")

    def create(self, request, *args, **kwargs):
        # Alta reutilizando el registro, pero sin autologin: no se emiten tokens
        # y la respuesta es el perfil admin (sin password). is_staff queda False
        # porque RegisterSerializer no lo expone en sus fields.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = AdminUserSerializer(user, context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED)


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAdminUser,)
    queryset = get_user_model().objects.all()
    http_method_names = ("get", "patch", "head", "options")

    def get_serializer_class(self):
        if self.request.method == "GET":
            return AdminUserSerializer
        return AdminUserUpdateSerializer
