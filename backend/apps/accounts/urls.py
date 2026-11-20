from django.urls import path
from . import views
from .jwt_views import NiCatTokenObtainPairView, NiCatTokenRefreshView

urlpatterns = [
    path("auth/register/", views.register, name="auth-register"),
    path("auth/login/", NiCatTokenObtainPairView.as_view(), name="auth-login"),
    path("auth/refresh/", NiCatTokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", views.logout_view, name="auth-logout"),
    path("me/", views.me, name="me"),
]
