from django.urls import path
from . import views
app_name = "dashboard"
urlpatterns = [
    path("", views.index, name="index"),
    path("mentor/", views.mentor_dashboard, name="mentor_dashboard"),
    path("user/", views.user_dashboard, name="user_dashboard"),
    path("account/", views.account, name="account"),
]
