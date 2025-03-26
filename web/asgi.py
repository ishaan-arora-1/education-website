import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')

# Important: This needs to be before importing routing
django_asgi_app = get_asgi_application()

# Import routing after setting up Django
import web.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                web.routing.websocket_urlpatterns
            )
        )
    ),
})

# Make the application available for Daphne/Uvicorn/Hypercorn
asgi_application = application
