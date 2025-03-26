
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Using re_path instead of path for WebSocket routing
    re_path(r'ws/classroom/(?P<classroom_id>\d+)/$', consumers.ClassroomConsumer.as_asgi()),
]
