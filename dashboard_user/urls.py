from django.urls import path
from . import views

app_name = "dashboard_user"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('account/', views.account, name='account'),
    path('my-sessions/', views.my_sessions, name='my_sessions'),
    path('session-invitation/<str:token>/', views.session_invitation, name='session_invitation'),
]

