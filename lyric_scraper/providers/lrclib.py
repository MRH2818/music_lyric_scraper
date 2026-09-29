"""
LRCLIB provider for synchronized lyrics.
LRCLIB is a public, open-source crowdsourced lyrics database.
"""

from typing import List, Optional
import requests
from .base import BaseLyricProvider
from ..models import LyricTrack
from ..parser import LRCParser
from ..language import LanguageHelper


class LRCLIBProvider(BaseLyricProvider):
    name = "lrclib"
    BASE_URL = "https://lrclib.net/api"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "LyricScraper/1.0 (Language Learning Tool)",
            "Accept": "application/json",
        }

    def _convert_item(self, item: dict) -> Optional[LyricTrack]:
        synced = item.get("syncedLyrics") or ""
        plain = item.get("plainLyrics") or ""
        duration = float(item.get("duration") or 0.0)

        # Parse synced lines
        lines, _ = LRCParser.parse_lrc(synced, duration=duration)

        sample_text = plain or ("\n".join(l.text for l in lines))
        detected_lang, conf = LanguageHelper.detect_language(sample_text)

        return LyricTrack(
            title=item.get("trackName") or "",
            artist=item.get("artistName") or "",
            album=item.get("albumName") or "",
            duration=duration,
            provider=self.name,
            source_id=str(item.get("id") or ""),
            synced_lyrics=synced,
            plain_lyrics=plain,
            lines=lines,
            detected_language=detected_lang,
            language_confidence=conf,
            is_instrumental=bool(item.get("instrumental", False)),
        )

    def search(
        self,
        query: str,
        artist: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 10,
    ) -> List[LyricTrack]:
        tracks: List[LyricTrack] = []
        try:
            params = {}
            if artist:
                params["track_name"] = query
                params["artist_name"] = artist
            else:
                params["q"] = query

            resp = requests.get(
                f"{self.BASE_URL}/search",
                params=params,
                headers=self.headers,
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            if isinstance(data, list):
                for item in data[:limit * 2]:
                    track = self._convert_item(item)
                    if track and (track.synced_lyrics or track.lines):
                        if LanguageHelper.matches_target(track.plain_lyrics or track.synced_lyrics, language):
                            tracks.append(track)
                            if len(tracks) >= limit:
                                break

        except Exception:
            pass

        return tracks

    def get_lyrics_by_id(self, track_id: str) -> Optional[LyricTrack]:
        try:
            resp = requests.get(
                f"{self.BASE_URL}/get/{track_id}",
                headers=self.headers,
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                item = resp.json()
                return self._convert_item(item)
        except Exception:
            pass
        return None
