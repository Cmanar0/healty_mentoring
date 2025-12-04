from django.urls import path
from . import views
app_name = "web"
urlpatterns = [
    path("", views.landing, name="landing"),
    path("mentors/", views.mentors, name="mentors"),
    path("mentors/search/", views.mentor_search_suggestions, name="mentor_search_suggestions"),
    path("mentors/load-more/", views.mentors_load_more, name="mentors_load_more"),
    path("landing/mentors/", views.landing_mentors_load, name="landing_mentors_load"),
    path("terms/", views.terms, name="terms"),
    path("privacy/", views.privacy, name="privacy"),
    path("mentor/<int:user_id>/", views.mentor_profile_detail, name="mentor_profile_detail"),
]
