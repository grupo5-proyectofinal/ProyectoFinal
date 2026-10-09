from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UpdateProfileSerializer,
)


class PasswordResetRateThrottle(AnonRateThrottle):
    scope = "password_reset"


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": ProfileSerializer(user, context=self.get_serializer_context()).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
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
