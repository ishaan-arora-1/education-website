import logging
import traceback

from django.http import Http404
from django.shortcuts import render
from django.urls import Resolver404, resolve

from .models import Course, WebRequest
from .views import send_slack_message

logger = logging.getLogger(__name__)


class GlobalExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Rewrite the hostname
        request.META["HTTP_HOST"] = "alphaonelabs.com"

        # Proceed with the request
        response = self.get_response(request)
        return response

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
        # Skip tracking for static files
        if request.path.startswith("/static/"):
            logger.debug(f"Skipping tracking for static file: {request.path}")
            return self.get_response(request)

        try:
            # Try to resolve the URL to get the view name
            resolver_match = resolve(request.path)
            logger.debug(f"Resolved URL: {request.path} to view: {resolver_match.url_name}")

            # Get client info with default empty strings
            # Get real IP from X-Forwarded-For if available
            ip_address = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
                "REMOTE_ADDR", ""
            )
            user = request.user.username if request.user.is_authenticated else ""
            agent = request.META.get("HTTP_USER_AGENT", "")
            referer = request.META.get("HTTP_REFERER", "")

            # Try to get course for course detail pages
            course = None
            if resolver_match.url_name == "course_detail":
                logger.debug(f"Processing course detail page with slug: {resolver_match.kwargs.get('slug')}")
                try:
                    course = Course.objects.get(slug=resolver_match.kwargs["slug"])
                    logger.debug(f"Found course: {course.title}")
                except Course.DoesNotExist:
                    logger.debug("Course not found, will create WebRequest without course association")
                    # Don't return here, continue to create WebRequest without course

            # Get the response first
            response = self.get_response(request)
            logger.debug(f"Response status code: {response.status_code}")

            # Only track successful responses and 404s
            if response.status_code < 500:
                # Create or update web request
                web_request, created = WebRequest.objects.get_or_create(
                    ip_address=ip_address,
                    user=user,
                    agent=agent,
                    path=request.path,
                    course=course,
                    defaults={"referer": referer, "count": 1},
                )

                if not created:
                    web_request.count += 1
                    web_request.referer = referer  # Update referer
                    web_request.save()
                    logger.debug(f"Updated existing web request, new count: {web_request.count}")
                else:
                    logger.debug("Created new web request")

            return response

        except (Http404, Resolver404) as e:
            # Let Django handle 404 errors
            logger.debug(f"Caught 404 error: {str(e)}")
            return self.get_response(request)
        except Exception as e:
            # For any other errors, let Django handle them
            logger.error(f"Unexpected error in middleware: {str(e)}")
            return self.get_response(request)


class WaitingRoomValidationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Only validate if coming from waiting room
        if 'waiting_room_data' not in request.session:
            return None
        
        # Only validate on course creation POST
        if request.method != 'POST' or view_func.__name__ != 'CourseCreateView':
            return None
        
        # Get waiting room data
        waiting_room_data = request.session['waiting_room_data']
        
        # Validate subject and topics
        subject_match = (
            request.POST.get('subject', '').strip().lower() == 
            waiting_room_data['subject']
        )
        
        submitted_topics = {
            t.strip().lower() 
            for t in request.POST.get('topics', '').split(',')
            if t.strip()
        }
        topics_match = submitted_topics.issuperset(waiting_room_data['topics'])
        
        if not (subject_match and topics_match):
            messages.error(
                request, 
                "Course must match waiting room's subject and include all requested topics."
            )
            return redirect('course_create')
        
        # Clear waiting room data after validation
        del request.session['waiting_room_data']
        return None
