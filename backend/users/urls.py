from django.urls import path
from rest_framework_simplejwt.views import TokenBlacklistView, TokenRefreshView

from .views import (
    AdminRestablecerClaveView,
    AdminUserDetailView,
    AdminUserListView,
    BajaEmailsView,
    LoginView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ReenviarVerificacionView,
    RegisterView,
    UsuarioBusquedaView,
    UsuarioPerfilPublicoView,
    UsuarioResenasView,
    VerificarEmailView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    # El field es "email" porque User.USERNAME_FIELD = "email".
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Cierra la sesión del lado del servidor: el refresh queda en la blacklist.
    path("auth/logout/", TokenBlacklistView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/verificar-email/", VerificarEmailView.as_view(), name="verificar_email"),
    path(
        "auth/verificar-email/reenviar/",
        ReenviarVerificacionView.as_view(),
        name="reenviar_verificacion",
    ),
    path("auth/baja-emails/", BajaEmailsView.as_view(), name="baja_emails"),
    path("usuarios/", UsuarioBusquedaView.as_view(), name="usuario_busqueda"),
    path(
        "usuarios/<int:pk>/resenas/",
        UsuarioResenasView.as_view(),
        name="usuario_resenas",
    ),
    path(
        "usuarios/<int:pk>/",
        UsuarioPerfilPublicoView.as_view(),
        name="usuario_perfil",
    ),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="password_reset"),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("admin/usuarios/", AdminUserListView.as_view(), name="admin_usuario_lista"),
    path(
        "admin/usuarios/<int:pk>/",
        AdminUserDetailView.as_view(),
        name="admin_usuario_detalle",
    ),
    path(
        "admin/usuarios/<int:pk>/restablecer-clave/",
        AdminRestablecerClaveView.as_view(),
        name="admin_usuario_restablecer_clave",
    ),
]
