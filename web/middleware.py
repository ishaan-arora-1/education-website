import traceback
from django.http import HttpResponse
from .views import send_slack_message


class GlobalExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        # Format the error message with traceback
        error_message = f"ERROR: {str(exception)}\n\nTraceback:\n{traceback.format_exc()}\n\nPath: {request.path}"

        # Send to Slack
        send_slack_message(error_message)

        # Return a generic error response
        return HttpResponse(
            "An error occurred. Our team has been notified.", status=500
        )
