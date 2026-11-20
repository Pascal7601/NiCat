from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers
User = get_user_model()

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(max_length=6000, trim_whitespace=False)


class ProfileSerializer(serializers.ModelSerializer):
    can_review_written = serializers.SerializerMethodField()

    def get_can_review_written(self, obj):
        return bool(
            obj.is_active
            and obj.is_staff
            and obj.has_perm(
                "attempts.review_written_answers"
            )
        )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "date_joined",
            "can_review_written",
        )
        read_only_fields = fields

