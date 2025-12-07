from django.urls import path, include
from . import views

app_name = "general"

urlpatterns = [
    path("", views.index, name="index"),
    path("mark-manual-displayed/", views.mark_manual_displayed, name="mark_manual_displayed"),
    path("update-timezone/", views.update_timezone, name="update_timezone"),
    path("mentor/", include(("dashboard_mentor.urls", "dashboard_mentor"))),
    path("user/", include("dashboard_user.urls")),
]
