"""
Data models for Song Scraper.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class SongMetadata:
    """
    Metadata extracted from a lyric file (.json, .lrc, .srt, .vtt, .txt)
    or song naming convention.
    """
    title: str
    artist: str = ""
    album: str = ""
    duration: float = 0.0  # expected duration in seconds
    provider: Optional[str] = None
    source_id: Optional[str] = None
    plain_lyrics: Optional[str] = None
    synced_lrc: Optional[str] = None
    english_lyrics: Optional[str] = None
    english_synced_lrc: Optional[str] = None
    detected_language: Optional[str] = None
    language_name: Optional[str] = None
    is_foreign: bool = False
    lines: List[Dict[str, Any]] = field(default_factory=list)
    lyric_file_path: Optional[str] = None
    extra_tags: Dict[str, str] = field(default_factory=dict)

    @property
    def query_string(self) -> str:
        if self.artist and self.artist.lower() not in self.title.lower():
            return f"{self.artist} - {self.title}"
        return self.title

    def to_dict(self) -> Dict[str, Any]:
        """Exports clean JSON configuration separating foreign and English lyrics."""
        is_foreign = self.is_foreign or bool(self.detected_language and self.detected_language != "en")
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "duration": self.duration,
            "provider": self.provider,
            "source_id": self.source_id,
            "detected_language": self.detected_language,
            "language_name": self.language_name,
            "is_foreign": is_foreign,
            "lyrics": {
                "foreign": {
                    "language": self.detected_language or "unknown",
                    "plain": self.plain_lyrics or "",
                    "synced_lrc": self.synced_lrc or "",
                },
                "english": {
                    "language": "en",
                    "plain": self.english_lyrics or "",
                    "synced_lrc": self.english_synced_lrc or "",
                },
            },
            "lines_count": len(self.lines),
            "lines": self.lines,
        }


@dataclass
class AudioCandidate:
    """
    Candidate audio track found during search.
    """
    title: str
    uploader: str
    duration: float
    url: str
    duration_diff: float = 0.0
    is_official_audio: bool = False
    score: float = 0.0
    source: str = "youtube"


@dataclass
class DownloadResult:
    """
    Result of a song audio scrape/download operation.
    """
    success: bool
    metadata: SongMetadata
    audio_path: Optional[str] = None
    companion_lrc_path: Optional[str] = None
    companion_json_path: Optional[str] = None
    duration: float = 0.0
    expected_duration: float = 0.0
    duration_diff: float = 0.0
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    error: Optional[str] = None
