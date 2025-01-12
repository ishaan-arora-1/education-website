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

        # Print exception details to console
        print("\n=== Exception Details ===")
        print(f"Exception Type: {type(exception).__name__}")
        print(f"Exception Message: {str(exception)}")
        print("\nTraceback:")
        traceback.print_exc()
        print("=====================\n")

        tb = traceback.format_exc()
        error_message = f"ERROR: {str(exception)}\n\n" f"Traceback:\n{tb}\n\n" f"Path: {request.path}"

        if settings.DEBUG:
            context = {
                "error_message": error_message,
                "exception": exception,
                "traceback": tb,
            }
            return render(request, "500.html", context, status=500)
        else:
            send_slack_message(error_message)
            return render(request, "500.html", status=500)

        return None
