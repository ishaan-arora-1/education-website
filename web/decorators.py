from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse


def teacher_required(view_func):
    """
    Decorator for views that checks that the user is a teacher.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse("account_login"))
        if not hasattr(request.user, "profile") or not request.user.profile.is_teacher:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def student_required(view_func):
    """
    Decorator for views that checks that the user is a student.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse("login"))
        if not hasattr(request.user, "student"):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped_view
