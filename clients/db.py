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

    async def count_unused_subtopics(self, account_id: str) -> int:
        """Return how many Subtopics are unused for the given Account."""
        return await self.client.subtopic.count(
            where={"accountId": account_id, "used": False}
        )

    async def list_subtopic_titles_for_account(self, account_id: str) -> list[str]:
        rows = await self.client.subtopic.find_many(
            where={"accountId": account_id},
        )
        return [r.title for r in rows]

    async def list_used_subtopic_titles_for_account(self, account_id: str) -> list[str]:
        rows = await self.client.subtopic.find_many(
            where={"accountId": account_id, "used": True},
        )
        return [r.title for r in rows]

    async def create_subtopics_for_account(self, account_id: str, titles: list[str]) -> int:
        """Create subtopics under the account for given titles. Returns number created.
        Skips duplicates via unique title constraint.
        """
        created = 0
        for t in titles:
            try:
                await self.client.subtopic.create(
                    data={"title": t, "accountId": account_id}
                )
                created += 1
            except Exception:
                # Likely unique conflict on title; skip
                pass
        return created

    async def get_oldest_unused_subtopic(self, account_id: str):
        rows = await self.client.subtopic.find_many(
            where={"accountId": account_id, "used": False},
            order={"createdAt": "asc"},
            take=1,
        )
        return rows[0] if rows else None

    async def consume_subtopic_create_video(self, *, account_id: str, subtopic_id: str, title: str):
        """Mark subtopic as used and create a new Video linked 1:1 to it under the account.
        Returns the created Video.
        """
        # Mark subtopic used
        await self.client.subtopic.update(
            where={"id": subtopic_id},
            data={"used": True},
        )
        # Create video with relation to account and subtopic
        video = await self.client.video.create(
            data={
                "title": title,
                "accountId": account_id,
                "subtopicId": subtopic_id,
            }
        )
        return video
