"""
Base abstract class for lyric providers.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..models import LyricTrack


class BaseLyricProvider(ABC):
    """Abstract interface for synchronized lyric providers."""

    name: str = "base"

    @abstractmethod
    def search(
        self,
        query: str,
        artist: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 10,
    ) -> List[LyricTrack]:
        """
        Searches for tracks matching query.
        Returns a list of LyricTrack candidates.
        """
        pass

    @abstractmethod
    def get_lyrics_by_id(self, track_id: str) -> Optional[LyricTrack]:
        """
        Fetches full synchronized lyrics for a specific track ID.
        """
        pass
