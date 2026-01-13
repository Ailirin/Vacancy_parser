from django.utils.deprecation import MiddlewareMixin


class DisableCSRFForAPI(MiddlewareMixin):
    """
    Middleware для отключения CSRF проверки для API endpoints.
    CSRF защита отключается только для путей, начинающихся с '/api/'.
    """
    
    def process_request(self, request):
        # Отключаем CSRF проверку для API endpoints
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None

