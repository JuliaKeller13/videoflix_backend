from django.urls import path

from .views import ActivateView, RegisterView

urlpatterns = [
    path('register/',
        RegisterView.as_view(),
        name='register'),
    path(
        "activate/<str:uid>/<str:token>/",
        ActivateView.as_view(),
        name="activate",
    ),
]
