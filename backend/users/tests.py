from django.conf import settings


def test_auth_user_model():
    assert settings.AUTH_USER_MODEL == "users.User"
