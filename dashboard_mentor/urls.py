from django.urls import path
from . import views
from general import views as general_views

app_name = "dashboard_mentor"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('account/', views.account, name='account'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('support/', views.support_view, name='support'),
    path('billing/', views.billing, name='billing'),
    path('my-sessions/', views.my_sessions, name='my_sessions'),
    path('my-sessions/get-availability/', views.get_availability, name='get_availability'),
    path('my-sessions/check-collisions/', views.check_availability_collisions, name='check_availability_collisions'),
    path('my-sessions/save-availability/', views.save_availability, name='save_availability'),
    path('my-sessions/client-suggestions/', views.client_suggestions, name='client_suggestions'),
    path('my-sessions/delete-availability-slot/', views.delete_availability_slot, name='delete_availability_slot'),
    path('clients/', views.clients_list, name='clients_list'),
    path('clients/<int:client_id>/', views.client_detail, name='client_detail'),
    path('clients/<int:client_id>/request-review/', views.request_review, name='request_review'),
    path('invite-client/', views.invite_client, name='invite_client'),
    path('my-sessions/invite-session/', views.invite_session, name='invite_session'),
    path('my-sessions/schedule-session/', views.schedule_session, name='schedule_session'),
    path('my-sessions/remind-session/', views.remind_session, name='remind_session'),
    path('my-sessions/refund-session/', views.refund_session, name='refund_session'),
    path('my-sessions/session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('my-sessions/get-sessions/', views.get_sessions_paginated, name='get_sessions_paginated'),
    path('dashboard/upcoming-sessions/', views.get_dashboard_upcoming_sessions, name='get_dashboard_upcoming_sessions'),
    path('clients/<int:relationship_id>/resend/', views.resend_client_invitation, name='resend_client_invitation'),
    path('clients/<int:relationship_id>/delete/', views.delete_client_relationship, name='delete_client_relationship'),
    path('notifications/', general_views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/', general_views.notification_detail, name='notification_detail'),
    path('notifications/<int:notification_id>/mark-read/', general_views.notification_mark_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', general_views.notification_mark_all_read, name='notification_mark_all_read'),
    path('notifications/<int:notification_id>/modal/', general_views.notification_modal_detail, name='notification_modal_detail'),
    path('tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/create/', views.blog_create, name='blog_create'),
    path('blog/<int:post_id>/edit/', views.blog_edit, name='blog_edit'),
    path('blog/<int:post_id>/delete/', views.blog_delete, name='blog_delete'),
    path('profile/reviews/', views.reviews_management, name='reviews_management'),
    path('reviews/<int:review_id>/reply/', views.review_reply, name='review_reply'),
    path('reviews/secure/<str:uidb64>/<str:token>/', views.view_reviews_secure, name='view_reviews_secure'),
]

