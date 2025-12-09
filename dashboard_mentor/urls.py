from django.urls import path
from . import views
from general import views as general_views

app_name = "dashboard_mentor"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('account/', views.account, name='account'),
    path('profile/', views.profile, name='profile'),
    path('billing/', views.billing, name='billing'),
    path('my-sessions/', views.my_sessions, name='my_sessions'),
    path('my-sessions/save-availability/', views.save_availability, name='save_availability'),
    path('clients/', views.clients_list, name='clients_list'),
    path('invite-client/', views.invite_client, name='invite_client'),
    path('clients/<int:relationship_id>/resend/', views.resend_client_invitation, name='resend_client_invitation'),
    path('clients/<int:relationship_id>/delete/', views.delete_client_relationship, name='delete_client_relationship'),
    path('notifications/', general_views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/', general_views.notification_detail, name='notification_detail'),
    path('notifications/<int:notification_id>/mark-read/', general_views.notification_mark_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', general_views.notification_mark_all_read, name='notification_mark_all_read'),
    path('notifications/<int:notification_id>/modal/', general_views.notification_modal_detail, name='notification_modal_detail'),
]

