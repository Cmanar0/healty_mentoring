from django.urls import path
from . import views

app_name = "dashboard_user"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('account/', views.account, name='account'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('my-sessions/', views.my_sessions, name='my_sessions'),
    path('my-sessions/get-sessions/', views.get_sessions_paginated, name='get_sessions_paginated'),
    path('mentors/', views.mentors_list, name='mentors_list'),
    path('session-invitation/<str:token>/', views.session_invitation, name='session_invitation'),
    path('session-management/', views.session_management, name='session_management'),
    path('book-session/', views.book_session, name='book_session'),
]

