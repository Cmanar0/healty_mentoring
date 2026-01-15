from django.urls import path
from . import views

app_name = "dashboard_admin"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<str:batch_id>/delete/', views.notification_delete, name='notification_delete'),
    path('notifications/search-users/', views.notification_search_users, name='notification_search_users'),
    path('blog/', views.blog, name='blog'),
    path('tickets/', views.tickets, name='tickets'),
    path('statistics/', views.statistics, name='statistics'),
]

