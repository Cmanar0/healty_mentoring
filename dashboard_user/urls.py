from django.urls import path
from . import views

app_name = "dashboard_user"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('account/', views.account, name='account'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('support/', views.support_view, name='support'),
    path('my-sessions/', views.my_sessions, name='my_sessions'),
    path('my-sessions/get-sessions/', views.get_sessions_paginated, name='get_sessions_paginated'),
    path('mentors/', views.mentors_list, name='mentors_list'),
    path('session-invitation/<str:token>/', views.session_invitation, name='session_invitation'),
    path('session-management/', views.session_management, name='session_management'),
    path('book-session/', views.book_session, name='book_session'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/', views.notification_detail, name='notification_detail'),
    path('notifications/<int:notification_id>/mark-read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', views.notification_mark_all_read, name='notification_mark_all_read'),
    path('notifications/<int:notification_id>/modal/', views.notification_modal_detail, name='notification_modal_detail'),
]

