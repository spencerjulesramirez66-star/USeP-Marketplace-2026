from channels.generic.websocket import AsyncJsonWebsocketConsumer
import logging

logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        self.group_name = f'marketplace_user_{user.pk}'
        logger.info('Realtime notifications connected: user=%s group=%s', user.pk, self.group_name)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def message_notification(self, event):
        logger.info('Realtime notification delivered to user group %s', self.group_name)
        await self.send_json(event['payload'])
