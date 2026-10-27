from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from video_app.api.media_urls import development_media_patterns


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('auth_app.api.urls')),
    path("api/", include("video_app.api.urls")),
]

urlpatterns += development_media_patterns()