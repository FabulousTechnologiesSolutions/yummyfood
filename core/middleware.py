from django.utils.deprecation import MiddlewareMixin


class RequestLoggingMiddleware(MiddlewareMixin):
    """Pass-through stub; request logging added in a later phase."""

    def process_request(self, request):
        return None
