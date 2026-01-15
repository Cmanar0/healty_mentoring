from django.urls import path, include
from . import views
import dashboard_mentor.urls
import dashboard_user.urls
import dashboard_admin.urls

app_name = "general"

urlpatterns = [
    path("", views.index, name="index"),
    path("mark-manual-displayed/", views.mark_manual_displayed, name="mark_manual_displayed"),
    path("update-timezone/", views.update_timezone, name="update_timezone"),
    path("mentor/", include((dashboard_mentor.urls, "dashboard_mentor"))),
    path("user/", include((dashboard_user.urls, "dashboard_user"), namespace="dashboard_user")),
    path("admin/", include((dashboard_admin.urls, "dashboard_admin"), namespace="dashboard_admin")),
]
