import os
from datetime import datetime

from django.conf import settings


def last_modified(request):
    """Add last_modified timestamp to the global template context."""
    try:
        # Use the project's root directory modification time
        timestamp = os.path.getmtime(settings.BASE_DIR)
        last_modified_time = datetime.fromtimestamp(timestamp)
    except Exception:
        last_modified_time = "Unknown"

    return {"last_modified": last_modified_time}
