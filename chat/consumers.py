import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        if not await self.can_access_conversation():
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json.get("message", "").strip()

        if not message_content:
            return

        message = await self.save_message(message_content)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message_content,
                "sender_id": self.user.id,
                "sender_name": await self.get_sender_name(),
                "timestamp": message.created_at.strftime("%b %d, %I:%M %p"),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender_id": event["sender_id"],
            "sender_name": event["sender_name"],
            "timestamp": event["timestamp"],
            "is_mine": event["sender_id"] == self.user.id,
        }))

    @database_sync_to_async
    def can_access_conversation(self):
        from .models import Conversation
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return self.user in [conversation.worker, conversation.employer]
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content):
        from .models import Conversation, Message
        conversation = Conversation.objects.get(id=self.conversation_id)
        return Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content
        )

    @database_sync_to_async
    def get_sender_name(self):
        if self.user.role == "worker":
            try:
                return self.user.worker_profile.full_name
            except:
                return self.user.phone_number
        elif self.user.role == "employer":
            try:
                return self.user.employer_profile.company_name
            except:
                return self.user.phone_number
        return self.user.phone_number
