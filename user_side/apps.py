from django.apps import AppConfig


class UserSideConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_side'
class AdminPanelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_panel'

    def ready(self):
        import user_side.signals