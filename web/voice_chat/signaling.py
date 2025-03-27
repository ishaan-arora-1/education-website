from channels.generic.websocket import AsyncWebsocketConsumer
import json

class SignalingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['classroom_id']
        self.room_group_name = f'voice_chat_{self.room_name}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept the connection
        await self.accept()
        
        # Send joined message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': self.scope['user'].id,
                'username': self.scope['user'].username
            }
        )

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Send left message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': self.scope['user'].id,
                'username': self.scope['user'].username
            }
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data['type']
        
        # Forward the message to all users in the room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'relay_message',
                'message': data,
                'sender_channel_name': self.channel_name,
                'sender_id': self.scope['user'].id
            }
        )

    async def relay_message(self, event):
        # Don't send the message back to the sender
        if self.channel_name != event['sender_channel_name']:
            message = event['message']
            await self.send(text_data=json.dumps(message))

    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user-joined',
            'userId': event['user_id'],
            'username': event['username']
        }))

    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user-left',
            'userId': event['user_id'],
            'username': event['username']
        }))
