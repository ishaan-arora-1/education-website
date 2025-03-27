from django.urls import re_path
from . import signaling

websocket_urlpatterns = [
    re_path(r'ws/voice/(?P<classroom_id>\w+)/$', signaling.SignalingConsumer.as_asgi()),
]
