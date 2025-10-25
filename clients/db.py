from __future__ import annotations

from typing import Iterable, Optional

from prisma import Prisma


class DB:
    def __init__(self) -> None:             
        self.client = Prisma()

    async def connect(self) -> None:
        if not self.client.is_connected():
            await self.client.connect()

    async def disconnect(self) -> None:
        if self.client.is_connected():
            await self.client.disconnect()

    async def ensure_topic(self, title: str):
        """Return existing Topic by title or create it."""
        existing = await self.client.topic.find_unique(where={"title": title})
        if existing is not None:
            return existing
        return await self.client.topic.create(data={"title": title})

    async def ensure_account_for_topic(self, topic_title: str):
        """Ensure an Account exists that is linked to the given Topic title.
        Returns the Account record.
        """
        topic = await self.ensure_topic(topic_title)
        # topicId is unique on Account
        account = await self.client.account.find_unique(
            where={"topicId": topic.id}
        )
        if account is not None:
            return account
        return await self.client.account.create(data={"topicId": topic.id})
