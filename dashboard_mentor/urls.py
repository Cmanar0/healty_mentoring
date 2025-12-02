from django.urls import path
from . import views

app_name = "dashboard_mentor"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('account/', views.account, name='account'),
    path('profile/', views.profile, name='profile'),
    path('billing/', views.billing, name='billing'),
    path('my-sessions/', views.my_sessions, name='my_sessions'),
]

