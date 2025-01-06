from web.views import index, github_update, about, learn, teach
from django.contrib import admin
from django.urls import path, include
from captcha import urls as captcha_urls

urlpatterns = [
    path("", index, name="index"),
    path("about/", about, name="about"),
    path("learn/", learn, name="learn"),
    path("teach/", teach, name="teach"),
    path("github_update/", github_update, name="github_update"),
    path("admin/", admin.site.urls),
    path("captcha/", include(captcha_urls)),
]
