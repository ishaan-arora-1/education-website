# Create new file: web/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class ClassroomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.classroom_id = self.scope['url_route']['kwargs']['classroom_id']
        self.classroom_group_name = f'classroom_{self.classroom_id}'

        # Add the user to the classroom group
        await self.channel_layer.group_add(
            self.classroom_group_name,
            self.channel_name
        )

        await self.accept()
        
        # Send a connection confirmation message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to classroom WebSocket',
            'classroom_id': self.classroom_id
        }))

    async def disconnect(self, close_code):
        # Log the disconnection with the close code
        print(f'WebSocket disconnected with code {close_code} for classroom {self.classroom_id}')
        
        # Remove the user from the classroom group
        await self.channel_layer.group_discard(
            self.classroom_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Receive message from WebSocket client
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')
            
            # Handle ping messages for connection testing
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'message': 'Server is alive'
                }))
                return
                
            # Handle different message types
            elif message_type == 'seat_update':
                # Broadcast seat update to the classroom group
                await self.channel_layer.group_send(
                    self.classroom_group_name,
                    {
                        'type': 'seat_update',
                        'seat_id': data.get('seat_id'),
                        'status': data.get('status'),
                        'student_id': data.get('student_id'),
                        'student_name': data.get('student_name')
                    }
                )
            elif message_type == 'hand_raise':
                # Broadcast hand raise to the classroom group
                await self.channel_layer.group_send(
                    self.classroom_group_name,
                    {
                        'type': 'hand_raise',
                        'seat_id': data.get('seat_id'),
                        'raised': data.get('raised'),
                        'student_name': data.get('student_name')
                    }
                )
            elif message_type == 'speaking_update':
                # Broadcast speaking status update
                await self.channel_layer.group_send(
                    self.classroom_group_name,
                    {
                        'type': 'speaking_update',
                        'seat_id': data.get('seat_id'),
                        'is_speaking': data.get('is_speaking'),
                        'student_name': data.get('student_name')
                    }
                )
            elif message_type == 'update_round':
                # Broadcast update round status
                await self.channel_layer.group_send(
                    self.classroom_group_name,
                    {
                        'type': 'update_round',
                        'status': data.get('status'),
                        'current_student': data.get('current_student'),
                        'time_remaining': data.get('time_remaining'),
                        'completed_students': data.get('completed_students')
                    }
                )
            elif message_type == 'shared_content':
                # Broadcast shared content update
                await self.channel_layer.group_send(
                    self.classroom_group_name,
                    {
                        'type': 'shared_content',
                        'seat_id': data.get('seat_id'),
                        'content_type': data.get('content_type'),
                        'content_url': data.get('content_url'),
                        'student_name': data.get('student_name')
                    }
                )
                # Broadcast hand raise to the classroom group
                await self.channel_layer.group_send(
                    self.classroom_group_name,
                    {
                        'type': 'hand_raise',
                        'seat_id': data.get('seat_id'),
                        'raised': data.get('raised', True),
                        'student_name': data.get('student_name')
                    }
                )
        except json.JSONDecodeError:
            # Handle invalid JSON
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            # Handle other exceptions
            print(f'WebSocket error: {str(e)}')
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error processing message: {str(e)}'
            }))


    async def seat_update(self, event):
        # Send seat update to WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'seat_update',
            'seat_id': event['seat_id'],
            'status': event['status'],
            'student_id': event['student_id'],
            'student_name': event['student_name']
        }))

    async def hand_raise(self, event):
        # Send hand raise update to WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'hand_raise',
            'seat_id': event['seat_id'],
            'raised': event['raised'],
            'student_name': event['student_name']
        }))

    async def speaking_update(self, event):
        # Send speaking status update to WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'speaking_update',
            'seat_id': event['seat_id'],
            'is_speaking': event['is_speaking'],
            'student_name': event['student_name']
        }))

    async def update_round(self, event):
        # Send update round status to WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'update_round',
            'status': event['status'],
            'current_student': event['current_student'],
            'time_remaining': event['time_remaining'],
            'completed_students': event['completed_students']
        }))

    async def shared_content(self, event):
        # Send shared content update to WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'shared_content',
            'seat_id': event['seat_id'],
            'content_type': event['content_type'],
            'content_url': event['content_url'],
            'student_name': event['student_name']
        }))
        
    async def content_shared(self, event):
        # Send content shared update to WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'content_shared',
            'student_name': event['student_name'],
            'content_type': event['content_type'],
            'description': event.get('description', ''),
            'content_url': event.get('content_url', '')
        }))
