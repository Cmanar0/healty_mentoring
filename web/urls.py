from django.urls import path
from . import views
app_name = "web"
urlpatterns = [
    path("", views.landing, name="landing"),
    path("mentors/", views.mentors, name="mentors"),
    path("terms/", views.terms, name="terms"),
    path("mentor/<int:user_id>/", views.mentor_profile_detail, name="mentor_profile_detail"),
]
