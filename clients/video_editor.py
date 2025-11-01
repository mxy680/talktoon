from __future__ import annotations

from typing import List, Dict, Optional


class VideoEditor:
    def __init__(self) -> None:
        self._session: Optional[Dict[str, object]] = None

    def begin(self, *, topic: str, subtopic: Optional[str], script: List[Dict[str, str]]) -> Dict[str, object]:
        self._session = {
            "topic": topic,
            "subtopic": subtopic,
            "script": script,
        }
        return {
            "topic": topic,
            "subtopic": subtopic,
            "line_count": len(script) if isinstance(script, list) else 0,
            "ready": True,
        }

    def add_asset(self, path: str) -> None:
        if not self._session:
            return

    def export_preview(self, path: str) -> None:
        if not self._session:
            return

    def export_final(self, path: str) -> None:
        if not self._session:
            return
