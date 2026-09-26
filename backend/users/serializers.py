from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


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
        )
