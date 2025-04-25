from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/tools/(?P<project_id>\d+)/$', consumers.ToolConsumer.as_asgi()),
]
