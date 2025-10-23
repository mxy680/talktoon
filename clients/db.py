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