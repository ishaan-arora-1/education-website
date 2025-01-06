import os

import time
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import requests
import subprocess
from django import forms
from captcha.fields import CaptchaField
from django.core.mail import send_mail


def index(request):
    last_modified_time = get_wsgi_last_modified_time()
    return render(request, "index.html", {"last_modified_time": last_modified_time})


@csrf_exempt
def github_update(request):
    send_slack_message("New commit pulled from GitHub")
    root_directory = os.path.abspath(os.sep)
    try:
        subprocess.run(["chmod", "+x", f"{root_directory}/setup.sh"])
        os.system(f"bash {root_directory}/setup.sh")
        send_slack_message("CHMOD success")

        current_time = time.time()
        os.utime(settings.PA_WSGI, (current_time, current_time))
        send_slack_message("Repository updated successfully")
        return HttpResponse("Repository updated successfully")
    except Exception as e:
        print(f"Deploy error: {e}")
        send_slack_message(f"Deploy error: {e}")
        return HttpResponse("Deploy error see logs.")


def send_slack_message(message):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("Warning: SLACK_WEBHOOK_URL not configured")
        return

    payload = {
        "text": f"```{message}```"  # Format as code block for better readability
    }
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()  # Raise exception for bad status codes
    except Exception as e:
        print(f"Failed to send Slack message: {e}")


def get_wsgi_last_modified_time():
    try:
        return time.ctime(os.path.getmtime(settings.PA_WSGI))
    except Exception:
        return "Unknown"


class LearnForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    subject = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea)
    captcha = CaptchaField()


class TeachForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    expertise = forms.CharField(max_length=200)
    experience = forms.CharField(widget=forms.Textarea)
    captcha = CaptchaField()


def about(request):
    return render(request, "about.html")


def learn(request):
    if request.method == "POST":
        form = LearnForm(request.POST)
        if form.is_valid():
            # Process form data
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]

            # Compose the email content
            email_subject = f"New Learning Inquiry: {subject}"
            email_message = (
                f"Hello Admin,\n\n"
                f"You've received a new learning inquiry:\n\n"
                f"Name: {name}\n"
                f"Email: {email}\n"
                f"Subject: {subject}\n"
                f"Message:\n{message}\n\n"
                f"Regards,\nAlpha One Labs"
            )

            # Send the email
            send_mail(
                email_subject,
                email_message,
                settings.EMAIL_FROM,  # From email (configured in settings)
                [settings.EMAIL_FROM],  # Replace with the recipient's email
                fail_silently=False,
            )

            return HttpResponse(
                "Thank you for your interest in learning! We've received your inquiry."
            )
    else:
        form = LearnForm()
    return render(request, "learn.html", {"form": form})


def teach(request):
    if request.method == "POST":
        form = TeachForm(request.POST)
        if form.is_valid():
            # Process form data
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            expertise = form.cleaned_data["expertise"]
            experience = form.cleaned_data["experience"]

            # Compose the email content
            email_subject = f"New Teaching Inquiry from {name}"
            email_message = (
                f"Hello Admin,\n\n"
                f"You've received a new teaching inquiry:\n\n"
                f"Name: {name}\n"
                f"Email: {email}\n"
                f"Expertise: {expertise}\n"
                f"Experience:\n{experience}\n\n"
                f"Regards,\nAlpha One Labs"
            )

            # Send the email
            send_mail(
                email_subject,
                email_message,
                settings.EMAIL_FROM,  # From email (configured in settings)
                [settings.EMAIL_FROM],  # Replace with the recipient's email
                fail_silently=False,
            )

            return HttpResponse(
                "Thank you for your interest in teaching! We've received your inquiry."
            )
    else:
        form = TeachForm()
    return render(request, "teach.html", {"form": form})
