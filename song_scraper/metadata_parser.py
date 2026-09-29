"""
Metadata Parser for extracting song details and duration from lyric files.
Supports .json, .lrc, .srt, .vtt, and .txt files with filename fallback.
"""

import json
import os
import re
from typing import Optional, Tuple, Dict, Any, List
from .models import SongMetadata
from lyric_scraper.parser import LRCParser
from lyric_scraper.language import LanguageHelper


class LyricFileParser:
    """
    Extracts structured SongMetadata from lyric files in various formats.
    """

    @staticmethod
    def parse_filename(filename: str) -> Tuple[str, str]:
        """
        Extracts (artist, title) from a filename.
        Handles patterns like:
          - 'Artist - Title.ext'
          - 'Artist_Title.ext'
          - 'Title.ext'
        """
        base = os.path.splitext(os.path.basename(filename))[0]

        # Check for ' - ' separator
        if " - " in base:
            parts = base.split(" - ", 1)
            return parts[0].strip(), parts[1].strip()

        # Check for single '_' separator
        if "_" in base:
            parts = base.split("_", 1)
            return parts[0].strip(), parts[1].strip()

        return "", base.strip()

    @classmethod
    def parse_file(cls, file_path: str) -> SongMetadata:
        """
        Loads and parses a lyric file, returning a populated SongMetadata.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Lyric file not found: {file_path}")

        _, ext = os.path.splitext(file_path)
        ext = ext.lower().lstrip(".")

        filename_artist, filename_title = cls.parse_filename(file_path)

        if ext == "json":
            return cls._parse_json(file_path, filename_artist, filename_title)
        elif ext == "lrc":
            return cls._parse_lrc(file_path, filename_artist, filename_title)
        elif ext in ("srt", "vtt"):
            return cls._parse_subtitles(file_path, ext, filename_artist, filename_title)
        else:
            return cls._parse_txt(file_path, filename_artist, filename_title)

    @classmethod
    def _parse_json(cls, file_path: str, fallback_artist: str, fallback_title: str) -> SongMetadata:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        title = data.get("title") or fallback_title or "Unknown Title"
        artist = data.get("artist") or fallback_artist or ""
        album = data.get("album") or ""
        duration = float(data.get("duration") or 0.0)
        provider = data.get("provider")
        source_id = str(data.get("source_id")) if data.get("source_id") else None
        detected_language = data.get("detected_language")
        language_name = data.get("language_name") or (LanguageHelper.get_language_name(detected_language) if detected_language else None)
        is_foreign = bool(data.get("is_foreign", bool(detected_language and detected_language != "en")))

        lyrics_obj = data.get("lyrics", {})
        foreign_obj = lyrics_obj.get("foreign", {}) if isinstance(lyrics_obj, dict) else {}
        english_obj = lyrics_obj.get("english", {}) if isinstance(lyrics_obj, dict) else {}

        plain_lyrics = foreign_obj.get("plain") or data.get("plain_lyrics")
        synced_lrc = foreign_obj.get("synced_lrc") or data.get("synced_lyrics")
        english_lyrics = english_obj.get("plain") or data.get("english_plain_lyrics")
        english_synced_lrc = english_obj.get("synced_lrc") or data.get("english_synced_lyrics")

        lines = data.get("lines", [])
        if duration == 0.0 and lines:
            last_line = lines[-1]
            last_ms = last_line.get("end_ms") or last_line.get("start_ms", 0)
            if last_ms > 0:
                duration = (last_ms + 4000) / 1000.0

        if not plain_lyrics and lines:
            plain_lyrics = "\n".join(l.get("foreign") or l.get("text", "") for l in lines if (l.get("foreign") or l.get("text")))

        if not english_lyrics and lines:
            eng_list = [l.get("english") or l.get("translation", "") for l in lines if (l.get("english") or l.get("translation"))]
            if eng_list:
                english_lyrics = "\n".join(eng_list)

        # Reconstruct standard LRC if needed
        if not synced_lrc and lines:
            lrc_lines = []
            for l in lines:
                start_ms = l.get("start_ms", 0)
                text = l.get("foreign") or l.get("text", "")
                time_str = LRCParser.format_time_lrc(start_ms)
                lrc_lines.append(f"{time_str}{text}")
            synced_lrc = "\n".join(lrc_lines)

        if not english_synced_lrc and lines:
            eng_lrc_lines = []
            for l in lines:
                start_ms = l.get("start_ms", 0)
                text = l.get("english") or l.get("translation")
                if text:
                    time_str = LRCParser.format_time_lrc(start_ms)
                    eng_lrc_lines.append(f"{time_str}{text}")
            if eng_lrc_lines:
                english_synced_lrc = "\n".join(eng_lrc_lines)

        return SongMetadata(
            title=title,
            artist=artist,
            album=album,
            duration=duration,
            provider=provider,
            source_id=source_id,
            plain_lyrics=plain_lyrics,
            synced_lrc=synced_lrc,
            english_lyrics=english_lyrics,
            english_synced_lrc=english_synced_lrc,
            detected_language=detected_language,
            language_name=language_name,
            is_foreign=is_foreign,
            lines=lines,
            lyric_file_path=file_path,
        )

    @classmethod
    def _parse_lrc(cls, file_path: str, fallback_artist: str, fallback_title: str) -> SongMetadata:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()

        lines, meta = LRCParser.parse_lrc(raw_text)

        title = meta.get("ti") or fallback_title or "Unknown Title"
        artist = meta.get("ar") or fallback_artist or ""
        album = meta.get("al") or ""
        duration = 0.0

        # Parse length tag [length:mm:ss]
        if "length" in meta:
            len_val = meta["length"].strip()
            if ":" in len_val:
                p = len_val.split(":")
                try:
                    duration = int(p[0]) * 60 + float(p[1])
                except ValueError:
                    pass

        # If no length tag, estimate from last lyric line
        if duration == 0.0 and lines:
            last_line = lines[-1]
            duration = (last_line.end_ms or (last_line.start_ms + 4000)) / 1000.0

        plain_lyrics = "\n".join(l.text for l in lines if l.text.strip())
        detected_lang, _ = LanguageHelper.detect_language(plain_lyrics)

        return SongMetadata(
            title=title,
            artist=artist,
            album=album,
            duration=duration,
            plain_lyrics=plain_lyrics,
            synced_lrc=raw_text,
            detected_language=detected_lang,
            is_foreign=bool(detected_lang and detected_lang != "en"),
            lines=[l.to_dict() for l in lines],
            lyric_file_path=file_path,
            extra_tags=meta,
        )

    @classmethod
    def _parse_subtitles(cls, file_path: str, ext: str, fallback_artist: str, fallback_title: str) -> SongMetadata:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        title = fallback_title or "Unknown Title"
        artist = fallback_artist or ""
        
        note_match = re.search(r"NOTE\s+Title:\s*(.*?)\s*-\s*Artist:\s*(.*)", content, re.IGNORECASE)
        if note_match:
            t, a = note_match.groups()
            if t.strip():
                title = t.strip()
            if a.strip():
                artist = a.strip()

        matches = list(re.finditer(r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})", content))
        duration = 0.0
        if matches:
            last_m = matches[-1]
            h, m, s, ms = [int(x) for x in last_m.groups()]
            duration = h * 3600 + m * 60 + s + ms / 1000.0 + 3.0

        text_lines = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.isdigit() or "-->" in line or line.startswith("WEBVTT") or line.startswith("NOTE"):
                continue
            text_lines.append(line)

        plain_lyrics = "\n".join(text_lines)
        detected_lang, _ = LanguageHelper.detect_language(plain_lyrics)

        return SongMetadata(
            title=title,
            artist=artist,
            duration=duration,
            plain_lyrics=plain_lyrics,
            detected_language=detected_lang,
            is_foreign=bool(detected_lang and detected_lang != "en"),
            lyric_file_path=file_path,
        )

    @classmethod
    def _parse_txt(cls, file_path: str, fallback_artist: str, fallback_title: str) -> SongMetadata:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            plain_lyrics = f.read().strip()

        detected_lang, _ = LanguageHelper.detect_language(plain_lyrics)

        return SongMetadata(
            title=fallback_title or "Unknown Title",
            artist=fallback_artist or "",
            duration=0.0,
            plain_lyrics=plain_lyrics,
            detected_language=detected_lang,
            is_foreign=bool(detected_lang and detected_lang != "en"),
            lyric_file_path=file_path,
        )
