import traceback

from django.shortcuts import render

from .views import send_slack_message


class GlobalExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        from django.conf import settings

        # Only handle exceptions in production
        if not settings.DEBUG:
            error_message = f"ERROR: {str(exception)}\n\nTraceback:\n{traceback.format_exc()}\n\nPath: {request.path}"
            send_slack_message(error_message)
            return render(request, "500.html", status=500)

        # In debug mode, let Django handle the exception normally
        return None
        # In debug mode, let Django handle the exception normally
        return None
