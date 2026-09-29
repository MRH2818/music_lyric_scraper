"""
Data models for synchronized lyrics and track metadata.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class LyricLine:
    start_ms: int
    end_ms: int
    text: str
    translation: Optional[str] = None
    start_time: str = ""  # formatted mm:ss.xx
    end_time: str = ""    # formatted mm:ss.xx

    def __post_init__(self):
        if not self.start_time:
            self.start_time = self._format_time(self.start_ms)
        if not self.end_time and self.end_ms > 0:
            self.end_time = self._format_time(self.end_ms)

    @staticmethod
    def _format_time(ms: int) -> str:
        if ms < 0:
            ms = 0
        total_seconds = ms / 1000.0
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:05.2f}"

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "foreign": self.text,
            "english": self.translation or "",
            "text": self.text,
        }
        if self.translation:
            data["translation"] = self.translation
        return data


@dataclass
class LyricTrack:
    title: str
    artist: str
    album: str = ""
    duration: float = 0.0  # seconds
    provider: str = ""
    source_id: str = ""
    synced_lyrics: str = ""  # raw LRC content (foreign)
    plain_lyrics: str = ""   # raw plain lyrics (foreign)
    english_synced_lyrics: str = ""  # english translated synced LRC
    english_plain_lyrics: str = ""   # english translated plain lyrics
    lines: List[LyricLine] = field(default_factory=list)
    detected_language: str = ""
    language_confidence: float = 0.0
    is_instrumental: bool = False

    def to_dict(self) -> Dict[str, Any]:
        is_foreign = bool(self.detected_language and self.detected_language != "en")
        foreign_plain = self.plain_lyrics or "\n".join(l.text for l in self.lines if l.text.strip())
        foreign_synced = self.synced_lyrics
        english_plain = self.english_plain_lyrics or "\n".join(l.translation for l in self.lines if l.translation)
        english_synced = self.english_synced_lyrics

        from .language import LanguageHelper
        lang_name = LanguageHelper.get_language_name(self.detected_language) if self.detected_language else "Unknown"

        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "duration": self.duration,
            "provider": self.provider,
            "source_id": self.source_id,
            "detected_language": self.detected_language,
            "language_name": lang_name,
            "language_confidence": round(self.language_confidence, 3),
            "is_foreign": is_foreign,
            "is_instrumental": self.is_instrumental,
            "lyrics": {
                "foreign": {
                    "language": self.detected_language or "unknown",
                    "language_name": lang_name,
                    "plain": foreign_plain,
                    "synced_lrc": foreign_synced,
                },
                "english": {
                    "language": "en",
                    "language_name": "English",
                    "plain": english_plain,
                    "synced_lrc": english_synced,
                },
            },
            "lines_count": len(self.lines),
            "lines": [line.to_dict() for line in self.lines],
        }
