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
