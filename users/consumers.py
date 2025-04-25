import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Project

logger = logging.getLogger(__name__)

class ToolConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for tool execution notifications.
    """

    async def connect(self):
        """
        Called when the WebSocket is handshaking.
        """
        self.user = self.scope["user"]

        # Anonymous users can't connect
        if isinstance(self.user, AnonymousUser):
            logger.warning("Anonymous user tried to connect to tool WebSocket")
            await self.close()
            return

        # Get the project ID from the URL route
        self.project_id = self.scope['url_route']['kwargs']['project_id']

        # Check if the user has access to this project
        if not await self.user_has_project_access(self.project_id):
            logger.warning(f"User {self.user.username} tried to access project {self.project_id} without permission")
            await self.close()
            return

        # Set the group name
        self.group_name = f"tools_{self.project_id}"

        # Join the group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Accept the connection
        await self.accept()
        logger.info(f"User {self.user.username} connected to tool WebSocket for project {self.project_id}")

    async def disconnect(self, close_code):
        """
        Called when the WebSocket closes.
        """
        # Leave the group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        logger.info(f"User {self.user.username} disconnected from tool WebSocket for project {self.project_id}")

    async def receive(self, text_data):
        """
        Called when we receive a message from the client.
        """
        # We don't expect to receive messages from the client
        pass

    async def tool_executed(self, event):
        """
        Called when a tool is executed.
        """
        # Send the notification to the client
        await self.send(text_data=json.dumps({
            'type': 'tool_executed',
            'tool_name': event['tool_name'],
            'result': event['result']
        }))

    async def reasoning_step(self, event):
        """
        Called when a reasoning step is started, completed, or failed.
        """
        # Send the notification to the client
        await self.send(text_data=json.dumps({
            'type': 'reasoning_step',
            'session_id': event['session_id'],
            'step': event['step']
        }))

    @database_sync_to_async
    def user_has_project_access(self, project_id):
        """
        Check if the user has access to the project.
        """
        try:
            return Project.objects.filter(id=project_id, user=self.user).exists()
        except Exception as e:
            logger.exception(f"Error checking project access: {str(e)}")
            return False
