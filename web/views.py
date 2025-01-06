import os

import time
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import requests
import subprocess


def index(request):
    last_modified_time = get_wsgi_last_modified_time()
    return render(request, "index.html", {"last_modified_time": last_modified_time})


@csrf_exempt
def github_update(request):
    send_slack_message("New commit pulled:")
    current_directory = os.path.dirname(os.path.abspath(__file__))
    parent_directory = os.path.dirname(current_directory)
    try:
        subprocess.run(["chmod", "+x", f"{parent_directory}/setup.sh"])
        os.system(f"bash {parent_directory}/setup.sh")

        current_time = time.time()
        os.utime(settings.PA_WSGI, (current_time, current_time))

        return HttpResponse("Repository updated successfully")
    except Exception:
        return HttpResponse(f"Deploy error see logs.")


def send_slack_message(message):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if webhook_url:
        payload = {"text": message}
        try:
            requests.post(webhook_url, json=payload)
            pass
        except Exception as e:
            print(f"Failed to send Slack message: {e}")


def get_wsgi_last_modified_time():
    try:
        return time.ctime(os.path.getmtime(settings.PA_WSGI))
    except Exception:
        return "Unknown"
