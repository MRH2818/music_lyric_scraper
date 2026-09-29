"""
Parser and format converters for synchronized lyrics (LRC, SRT, VTT, JSON, TXT).
"""

import json
import re
from typing import List, Tuple, Optional, Dict, Any, Union
from .models import LyricLine, LyricTrack


class LRCParser:
    """
    Parses LRC strings with high tolerance for various timestamp styles,
    multi-timestamps per line, and metadata tags.
    """

    # Regex for standard [mm:ss.xx] or [mm:ss.xxx] or [hh:mm:ss.xx]
    TIMESTAMP_REGEX = re.compile(
        r"\[(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]"
    )
    METADATA_REGEX = re.compile(r"^\[([a-zA-Z]+):(.*)\]$")

    @classmethod
    def parse_timestamp(cls, match: re.Match) -> int:
        """Converts matched timestamp parts into milliseconds."""
        hours_str, minutes_str, seconds_str, millis_str = match.groups()
        hours = int(hours_str) if hours_str else 0
        minutes = int(minutes_str) if minutes_str else 0
        seconds = int(seconds_str) if seconds_str else 0

        if millis_str:
            if len(millis_str) == 1:
                ms = int(millis_str) * 100
            elif len(millis_str) == 2:
                ms = int(millis_str) * 10
            else:
                ms = int(millis_str[:3])
        else:
            ms = 0

        total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + ms
        return total_ms

    @classmethod
    def parse_lrc(cls, lrc_text: str, duration: float = 0.0) -> Tuple[List[LyricLine], Dict[str, str]]:
        """
        Parses raw LRC string into a sorted list of LyricLine objects and metadata dict.
        """
        if not lrc_text or not lrc_text.strip():
            return [], {}

        metadata: Dict[str, str] = {}
        parsed_entries: List[Tuple[int, str]] = []

        lines = lrc_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if metadata tag (e.g. [ar: Artist])
            meta_match = cls.METADATA_REGEX.match(line)
            if meta_match and not cls.TIMESTAMP_REGEX.search(line):
                tag_name, tag_val = meta_match.groups()
                metadata[tag_name.lower().strip()] = tag_val.strip()
                continue

            # Find all timestamps on this line
            matches = list(cls.TIMESTAMP_REGEX.finditer(line))
            if not matches:
                continue

            # Extract the actual lyric text by stripping timestamp brackets
            cleaned_text = cls.TIMESTAMP_REGEX.sub("", line).strip()

            for m in matches:
                start_ms = cls.parse_timestamp(m)
                parsed_entries.append((start_ms, cleaned_text))

        # Sort entries chronologically
        parsed_entries.sort(key=lambda x: x[0])

        # Convert to LyricLine with computed end_ms
        lyric_lines: List[LyricLine] = []
        total_duration_ms = int(duration * 1000) if duration > 0 else 0

        for i, (start_ms, text) in enumerate(parsed_entries):
            # Compute end_ms based on next line's start_ms
            if i + 1 < len(parsed_entries):
                next_start = parsed_entries[i + 1][0]
                # If next line is very far away, cap the display duration to 7 seconds
                end_ms = min(next_start, start_ms + 7000)
                if end_ms <= start_ms:
                    end_ms = start_ms + 3000
            else:
                # Last line
                if total_duration_ms > start_ms:
                    end_ms = min(total_duration_ms, start_ms + 6000)
                else:
                    end_ms = start_ms + 4000

            lyric_lines.append(
                LyricLine(
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=text,
                )
            )

        return lyric_lines, metadata

    @staticmethod
    def format_time_lrc(ms: int) -> str:
        """Formats ms as [mm:ss.xx]"""
        if ms < 0:
            ms = 0
        total_seconds = ms / 1000.0
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"[{minutes:02d}:{seconds:05.2f}]"

    @staticmethod
    def format_time_srt(ms: int) -> str:
        """Formats ms as hh:mm:ss,xxx"""
        if ms < 0:
            ms = 0
        total_seconds = ms // 1000
        millis = ms % 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    @staticmethod
    def format_time_vtt(ms: int) -> str:
        """Formats ms as hh:mm:ss.xxx"""
        if ms < 0:
            ms = 0
        total_seconds = ms // 1000
        millis = ms % 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"

    @classmethod
    def to_lrc(cls, track: LyricTrack) -> str:
        """Generates standard .lrc file text with original foreign lyrics."""
        headers = []
        if track.title:
            headers.append(f"[ti:{track.title}]")
        if track.artist:
            headers.append(f"[ar:{track.artist}]")
        if track.album:
            headers.append(f"[al:{track.album}]")
        if track.duration > 0:
            dur_mins = int(track.duration // 60)
            dur_secs = int(track.duration % 60)
            headers.append(f"[length:{dur_mins:02d}:{dur_secs:02d}]")

        lines_str = []
        for line in track.lines:
            time_tag = cls.format_time_lrc(line.start_ms)
            lines_str.append(f"{time_tag}{line.text}")

        content = ""
        if headers:
            content += "\n".join(headers) + "\n\n"
        content += "\n".join(lines_str)
        return content

    @classmethod
    def to_english_lrc(cls, track: LyricTrack) -> str:
        """Generates synced English translation .lrc file text."""
        headers = []
        if track.title:
            headers.append(f"[ti:{track.title} (English Translation)]")
        if track.artist:
            headers.append(f"[ar:{track.artist}]")
        if track.album:
            headers.append(f"[al:{track.album}]")

        lines_str = []
        for line in track.lines:
            time_tag = cls.format_time_lrc(line.start_ms)
            text = line.translation if line.translation else line.text
            lines_str.append(f"{time_tag}{text}")

        content = ""
        if headers:
            content += "\n".join(headers) + "\n\n"
        content += "\n".join(lines_str)
        return content

    @classmethod
    def to_bilingual_lrc(cls, track: LyricTrack) -> str:
        """Generates bilingual synchronized .lrc file text with both foreign and English text."""
        headers = []
        if track.title:
            headers.append(f"[ti:{track.title}]")
        if track.artist:
            headers.append(f"[ar:{track.artist}]")

        lines_str = []
        for line in track.lines:
            time_tag = cls.format_time_lrc(line.start_ms)
            text = line.text
            if line.translation and line.translation.strip() != line.text.strip():
                text = f"{line.text} ({line.translation})"
            lines_str.append(f"{time_tag}{text}")

        content = ""
        if headers:
            content += "\n".join(headers) + "\n\n"
        content += "\n".join(lines_str)
        return content

    @classmethod
    def to_srt(cls, track: LyricTrack) -> str:
        """Generates standard .srt subtitle file text with foreign lyrics and English translation."""
        srt_blocks = []
        counter = 1
        for line in track.lines:
            if not line.text.strip():
                continue
            start_fmt = cls.format_time_srt(line.start_ms)
            end_fmt = cls.format_time_srt(line.end_ms)
            text = line.text
            if line.translation and line.translation.strip() != line.text.strip():
                text = f"{text}\n({line.translation})"
            srt_blocks.append(f"{counter}\n{start_fmt} --> {end_fmt}\n{text}\n")
            counter += 1
        return "\n".join(srt_blocks)

    @classmethod
    def to_vtt(cls, track: LyricTrack) -> str:
        """Generates standard WebVTT .vtt subtitle file text."""
        vtt_blocks = ["WEBVTT", f"NOTE Title: {track.title} - Artist: {track.artist}\n"]
        for line in track.lines:
            if not line.text.strip():
                continue
            start_fmt = cls.format_time_vtt(line.start_ms)
            end_fmt = cls.format_time_vtt(line.end_ms)
            text = line.text
            if line.translation and line.translation.strip() != line.text.strip():
                text = f"{text}\n({line.translation})"
            vtt_blocks.append(f"{start_fmt} --> {end_fmt}\n{text}\n")
        return "\n".join(vtt_blocks)

    @classmethod
    def to_json(cls, track: LyricTrack, indent: int = 2) -> str:
        """Generates structured JSON representation with separated foreign and english lyrics."""
        return json.dumps(track.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, data_or_str: Union[str, dict]) -> LyricTrack:
        """Parses a structured JSON configuration back into a LyricTrack."""
        data = json.loads(data_or_str) if isinstance(data_or_str, str) else data_or_str

        title = data.get("title", "")
        artist = data.get("artist", "")
        album = data.get("album", "")
        duration = float(data.get("duration", 0.0))
        provider = data.get("provider", "")
        source_id = str(data.get("source_id", ""))
        detected_language = data.get("detected_language", "")
        language_confidence = float(data.get("language_confidence", 0.0))
        is_instrumental = bool(data.get("is_instrumental", False))

        # Check nested lyrics dict or legacy top-level keys
        lyrics_obj = data.get("lyrics", {})
        foreign_obj = lyrics_obj.get("foreign", {}) if isinstance(lyrics_obj, dict) else {}
        english_obj = lyrics_obj.get("english", {}) if isinstance(lyrics_obj, dict) else {}

        plain_lyrics = foreign_obj.get("plain") or data.get("plain_lyrics", "")
        synced_lyrics = foreign_obj.get("synced_lrc") or data.get("synced_lyrics", "")
        english_plain = english_obj.get("plain") or data.get("english_plain_lyrics", "")
        english_synced = english_obj.get("synced_lrc") or data.get("english_synced_lyrics", "")

        raw_lines = data.get("lines", [])
        parsed_lines: List[LyricLine] = []
        for l in raw_lines:
            start_ms = l.get("start_ms", 0)
            end_ms = l.get("end_ms", 0)
            text = l.get("foreign") or l.get("text", "")
            translation = l.get("english") or l.get("translation")
            start_time = l.get("start_time", "")
            end_time = l.get("end_time", "")
            parsed_lines.append(
                LyricLine(
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=text,
                    translation=translation,
                    start_time=start_time,
                    end_time=end_time,
                )
            )

        return LyricTrack(
            title=title,
            artist=artist,
            album=album,
            duration=duration,
            provider=provider,
            source_id=source_id,
            synced_lyrics=synced_lyrics,
            plain_lyrics=plain_lyrics,
            english_synced_lyrics=english_synced,
            english_plain_lyrics=english_plain,
            lines=parsed_lines,
            detected_language=detected_language,
            language_confidence=language_confidence,
            is_instrumental=is_instrumental,
        )

    @classmethod
    def to_txt(cls, track: LyricTrack) -> str:
        """Generates clean plain text lyrics (foreign, with English translation if available)."""
        lines = []
        for line in track.lines:
            if line.text.strip():
                if line.translation and line.translation.strip() != line.text.strip():
                    lines.append(f"{line.text} — {line.translation}")
                else:
                    lines.append(line.text)
        if lines:
            return "\n".join(lines)
        return track.plain_lyrics.strip() if track.plain_lyrics else ""
