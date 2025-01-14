import os
import time

from django.conf import settings


def last_modified(request):
    """Add last_modified timestamp to the global template context."""
    try:
        timestamp = os.path.getmtime(settings.PA_WSGI)
        last_modified_time = time.ctime(timestamp)
    except Exception:
        last_modified_time = "Unknown"

    return {"last_modified": last_modified_time}


def logged_in_as(request):
    """Add login-as status to context for superusers."""
    # Only process for authenticated superusers
    if not request.user.is_authenticated or not request.user.is_superuser:
        return {}

    # Only return data if we're actually logged in as someone else
    logged_in_as = request.session.get("logged_in_as", {})
    if not logged_in_as:
        return {}

    return {"logged_in_as": logged_in_as}
