from django.urls import path

from .views import ActivateView, LoginView, RegisterView, TokenRefreshView


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path(
        "activate/<str:uid>/<str:token>/",
        ActivateView.as_view(),
        name="activate",
    ),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]