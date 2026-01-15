from django.urls import path
from . import views

app_name = "dashboard_admin"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/list/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/', views.notification_detail, name='notification_detail'),
    path('notifications/<int:notification_id>/mark-read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', views.notification_mark_all_read, name='notification_mark_all_read'),
    path('notifications/<int:notification_id>/modal/', views.notification_modal_detail, name='notification_modal_detail'),
    path('notifications/<str:batch_id>/delete/', views.notification_delete, name='notification_delete'),
    path('notifications/bulk-delete/', views.notification_bulk_delete, name='notification_bulk_delete'),
    path('notifications/search-users/', views.notification_search_users, name='notification_search_users'),
    path('blog/', views.blog, name='blog'),
    path('tickets/', views.tickets, name='tickets'),
    path('tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('statistics/', views.statistics, name='statistics'),
]

