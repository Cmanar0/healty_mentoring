from django.urls import path, include
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("mentor/", include("dashboard_mentor.urls")),
    path("user/", include("dashboard_user.urls")),
]
