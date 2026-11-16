import pytest


@pytest.fixture(autouse=True)
def _hasher_rapido(settings):
    """PBKDF2 (el hasher real) cuesta ~0,2 s por contraseña y la suite crea y
    verifica miles. En tests basta un hasher barato; la seguridad en producción no cambia."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def _expiracion_en_cada_lectura(settings):
    """En producción las lecturas procesan vencimientos a lo sumo cada 60 s; los tests
    esperan que ocurra en cada lectura."""
    settings.EXPIRACION_PEREZOSA_SEGUNDOS = 0

