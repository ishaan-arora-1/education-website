from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from .utils import send_slack_message


@receiver(user_signed_up)
def notify_slack_on_signup(request, user, **kwargs):
    """Send a Slack notification when a new user signs up"""
    is_teacher = getattr(user.profile, "is_teacher", False)
    user_type = "Teacher" if is_teacher else "Student"

    message = (
        f"🎉 New {user_type} Signup!\n" f"*Name:* {user.get_full_name() or user.email}\n" f"*Email:* {user.email}\n"
    )

    send_slack_message(message)
