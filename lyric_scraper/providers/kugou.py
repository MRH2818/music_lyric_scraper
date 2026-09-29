"""
Kugou synced lyrics provider.
"""

import base64
from typing import List, Optional
import requests
from .base import BaseLyricProvider
from ..models import LyricTrack
from ..parser import LRCParser
from ..language import LanguageHelper


class KugouProvider(BaseLyricProvider):
    name = "kugou"
    SEARCH_URL = "http://mobilecdn.kugou.com/api/v3/search/song"
    LYRIC_SEARCH_URL = "http://krcs.kugou.com/search"
    LYRIC_DOWNLOAD_URL = "http://krcs.kugou.com/download"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    def _fetch_lrc(self, song_hash: str, duration_sec: float) -> Optional[str]:
        try:
            params = {
                "ver": "1",
                "man": "yes",
                "client": "mobi",
                "keyword": "",
                "duration": str(int(duration_sec * 1000)),
                "hash": song_hash,
            }
            resp = requests.get(self.LYRIC_SEARCH_URL, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code != 200:
                return None

            candidates = resp.json().get("candidates", [])
            if not candidates:
                return None

            first = candidates[0]
            lyric_id = first.get("id")
            access_key = first.get("accesskey")
            if not lyric_id or not access_key:
                return None

            dl_params = {
                "ver": "1",
                "client": "mobi",
                "id": str(lyric_id),
                "accesskey": str(access_key),
                "fmt": "lrc",
                "charset": "utf8",
            }
            dl_resp = requests.get(self.LYRIC_DOWNLOAD_URL, params=dl_params, headers=self.headers, timeout=self.timeout)
            if dl_resp.status_code == 200:
                encoded = dl_resp.json().get("content", "")
                if encoded:
                    raw_bytes = base64.b64decode(encoded)
                    return raw_bytes.decode("utf-8", errors="ignore")
        except Exception:
            pass
        return None

    def search(
        self,
        query: str,
        artist: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 10,
    ) -> List[LyricTrack]:
        tracks: List[LyricTrack] = []
        search_kw = f"{query} {artist}".strip() if artist else query

        try:
            params = {
                "format": "json",
                "keyword": search_kw,
                "page": "1",
                "pagesize": str(limit * 2),
                "showtype": "1",
            }
            resp = requests.get(self.SEARCH_URL, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code != 200:
                return []

            song_list = resp.json().get("data", {}).get("info", [])
            for s in song_list:
                song_hash = s.get("hash", "")
                duration_sec = float(s.get("duration") or 0.0)
                song_name = s.get("songname", "")
                singer_name = s.get("singername", "")
                album_name = s.get("album_name", "")

                raw_lrc = self._fetch_lrc(song_hash, duration_sec)
                if not raw_lrc or not raw_lrc.strip():
                    continue

                lines, _ = LRCParser.parse_lrc(raw_lrc, duration=duration_sec)
                if not lines:
                    continue

                full_text = "\n".join(l.text for l in lines)
                detected_lang, conf = LanguageHelper.detect_language(full_text)

                if LanguageHelper.matches_target(full_text, language):
                    track = LyricTrack(
                        title=song_name or query,
                        artist=singer_name or (artist or ""),
                        album=album_name,
                        duration=duration_sec,
                        provider=self.name,
                        source_id=song_hash,
                        synced_lyrics=raw_lrc,
                        plain_lyrics=full_text,
                        lines=lines,
                        detected_language=detected_lang,
                        language_confidence=conf,
                    )
                    tracks.append(track)
                    if len(tracks) >= limit:
                        break
        except Exception:
            pass

        return tracks

    def get_lyrics_by_id(self, track_id: str) -> Optional[LyricTrack]:
        return None
