"""JWT login and refresh endpoints with an explicit Next.js-facing contract."""
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import ProfileSerializer


class LoginThrottle(AnonRateThrottle):
    rate = "5/min"


class NiCatTokenObtainSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = ProfileSerializer(self.user).data
        return data


class NiCatTokenObtainPairView(TokenObtainPairView):
    serializer_class = NiCatTokenObtainSerializer
    throttle_classes = (LoginThrottle,)


class NiCatTokenRefreshView(TokenRefreshView):
    throttle_classes = (LoginThrottle,)
