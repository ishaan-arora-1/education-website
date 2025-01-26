import traceback

from django.shortcuts import render
from django.urls import Resolver404, resolve

from .models import WebRequest
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


class WebRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            # Get identifying information for the client
            ip_address = request.META.get("REMOTE_ADDR")
            user = request.user.username if request.user.is_authenticated else None
            agent = request.META.get("HTTP_USER_AGENT")
            referer = request.META.get("HTTP_REFERER")

            # Try to get existing web request for this client and path
            web_request = WebRequest.objects.filter(
                path=request.path, ip_address=ip_address, user=user, agent=agent
            ).first()

            # Check if this is a course detail page to associate the course
            course = None
            try:
                resolved = resolve(request.path)
                if resolved.url_name == "course_detail":
                    course_slug = resolved.kwargs.get("slug")
                    if course_slug:
                        from .models import Course

                        course = Course.objects.get(slug=course_slug)
            except (Resolver404, Course.DoesNotExist):
                pass

            if web_request:
                # Increment count for existing request
                web_request.count += 1
                web_request.save()
            else:
                # Create new web request entry
                WebRequest.objects.create(
                    path=request.path,
                    ip_address=ip_address,
                    user=user,
                    agent=agent,
                    referer=referer,
                    course=course,
                    count=1,
                )
        except Exception as e:
            # Log the error but don't interrupt the response
            print(f"Error in WebRequestMiddleware: {str(e)}")

        return response
