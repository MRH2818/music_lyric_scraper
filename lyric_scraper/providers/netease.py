"""
NetEase Cloud Music provider for synced lyrics and line translations.
Outstanding coverage for East Asian (Japanese, Korean, Chinese) & global music.
"""

from typing import List, Optional, Dict
import requests
from .base import BaseLyricProvider
from ..models import LyricTrack, LyricLine
from ..parser import LRCParser
from ..language import LanguageHelper


class NetEaseProvider(BaseLyricProvider):
    name = "netease"
    SEARCH_URL = "https://music.163.com/api/search/get/web"
    LYRIC_URL = "https://music.163.com/api/song/lyric"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://music.163.com/",
            "Cookie": "appver=2.0.2",
        }

    def _fetch_lyrics_data(self, song_id: int) -> Optional[dict]:
        try:
            params = {
                "os": "pc",
                "id": str(song_id),
                "lv": "-1",
                "kv": "-1",
                "tv": "-1",
            }
            resp = requests.get(
                self.LYRIC_URL,
                params=params,
                headers=self.headers,
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return resp.json()
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
        search_term = f"{query} {artist}".strip() if artist else query

        try:
            params = {
                "s": search_term,
                "type": "1",  # 1 = Song
                "offset": "0",
                "total": "true",
                "limit": str(limit * 2),
            }
            resp = requests.get(
                self.SEARCH_URL,
                params=params,
                headers=self.headers,
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            songs = data.get("result", {}).get("songs", [])

            for s in songs:
                song_id = s.get("id")
                if not song_id:
                    continue

                title = s.get("name", "")
                artists_list = [a.get("name", "") for a in s.get("artists", [])]
                artist_name = ", ".join(filter(None, artists_list))
                album_name = s.get("album", {}).get("name", "")
                duration_sec = (s.get("duration") or 0) / 1000.0

                lyric_data = self._fetch_lyrics_data(song_id)
                if not lyric_data:
                    continue

                raw_lrc = lyric_data.get("lrc", {}).get("lyric", "")
                if not raw_lrc or not raw_lrc.strip():
                    continue

                # Parse primary synced lyrics
                lines, _ = LRCParser.parse_lrc(raw_lrc, duration=duration_sec)
                if not lines:
                    continue

                # Parse optional translation lyrics
                t_lrc = lyric_data.get("tlyric", {}).get("lyric", "")
                if t_lrc:
                    t_lines, _ = LRCParser.parse_lrc(t_lrc, duration=duration_sec)
                    t_map = {l.start_ms: l.text for l in t_lines if l.text.strip()}
                    for line in lines:
                        # Match closest timestamp
                        if line.start_ms in t_map:
                            line.translation = t_map[line.start_ms]

                full_text = "\n".join(l.text for l in lines)
                detected_lang, conf = LanguageHelper.detect_language(full_text)

                if LanguageHelper.matches_target(full_text, language):
                    track = LyricTrack(
                        title=title,
                        artist=artist_name,
                        album=album_name,
                        duration=duration_sec,
                        provider=self.name,
                        source_id=str(song_id),
                        synced_lyrics=raw_lrc,
                        plain_lyrics=full_text,
                        lines=lines,
                        detected_language=detected_lang,
                        language_confidence=conf,
                        is_instrumental=False,
                    )
                    tracks.append(track)
                    if len(tracks) >= limit:
                        break

        except Exception:
            pass

        return tracks

    def get_lyrics_by_id(self, track_id: str) -> Optional[LyricTrack]:
        try:
            song_id = int(track_id)
            lyric_data = self._fetch_lyrics_data(song_id)
            if not lyric_data:
                return None

            raw_lrc = lyric_data.get("lrc", {}).get("lyric", "")
            if not raw_lrc:
                return None

            lines, _ = LRCParser.parse_lrc(raw_lrc)
            full_text = "\n".join(l.text for l in lines)
            detected_lang, conf = LanguageHelper.detect_language(full_text)

            return LyricTrack(
                title=f"Track {track_id}",
                artist="",
                duration=0.0,
                provider=self.name,
                source_id=str(track_id),
                synced_lyrics=raw_lrc,
                plain_lyrics=full_text,
                lines=lines,
                detected_language=detected_lang,
                language_confidence=conf,
            )
        except Exception:
            pass
        return None
