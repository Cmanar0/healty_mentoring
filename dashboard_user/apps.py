from django.apps import AppConfig


class DashboardUserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard_user'
    
    def ready(self):
        import dashboard_user.signals  # noqa