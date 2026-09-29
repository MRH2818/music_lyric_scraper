"""
Audio Tagger & Companion File Generator.
Embeds ID3 metadata tags, unsynchronized foreign/English lyrics, and exports companion synchronized .lrc and .json files.
"""

import os
import json
from typing import Optional
from .models import SongMetadata, DownloadResult


class AudioTagger:
    """
    Tags audio files with metadata and lyrics, and manages companion synced lyric and json configuration files.
    """

    @classmethod
    def tag_audio_file(
        cls,
        audio_path: str,
        meta: SongMetadata,
        embed_lyrics: bool = True,
    ) -> bool:
        """
        Embeds title, artist, album, and unsynchronized lyrics into the audio file.
        Supports MP3, M4A, FLAC, and OGG formats.
        """
        if not os.path.isfile(audio_path):
            return False

        _, ext = os.path.splitext(audio_path)
        ext = ext.lower().lstrip(".")

        try:
            if ext == "mp3":
                cls._tag_mp3(audio_path, meta, embed_lyrics)
            elif ext in ("m4a", "mp4"):
                cls._tag_m4a(audio_path, meta, embed_lyrics)
            elif ext == "flac":
                cls._tag_flac(audio_path, meta, embed_lyrics)
            elif ext == "ogg":
                cls._tag_ogg(audio_path, meta, embed_lyrics)
            return True
        except Exception:
            return False

    @staticmethod
    def _format_embedded_lyrics(meta: SongMetadata) -> str:
        """Formats clean bilingual or single-language lyrics for embedding."""
        if meta.plain_lyrics and meta.english_lyrics and meta.is_foreign:
            # Build bilingual format
            return f"--- {meta.language_name or 'Original'} Lyrics ---\n{meta.plain_lyrics}\n\n--- English Translation ---\n{meta.english_lyrics}"
        return meta.plain_lyrics or meta.english_lyrics or ""

    @staticmethod
    def _tag_mp3(audio_path: str, meta: SongMetadata, embed_lyrics: bool):
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, USLT, COMM, ID3NoHeaderError

        try:
            tags = ID3(audio_path)
        except ID3NoHeaderError:
            tags = ID3()

        if meta.title:
            tags["TIT2"] = TIT2(encoding=3, text=meta.title)
        if meta.artist:
            tags["TPE1"] = TPE1(encoding=3, text=meta.artist)
        if meta.album:
            tags["TALB"] = TALB(encoding=3, text=meta.album)

        if embed_lyrics:
            combined_lyrics = AudioTagger._format_embedded_lyrics(meta)
            if combined_lyrics:
                tags["USLT::eng"] = USLT(
                    encoding=3,
                    lang="eng",
                    desc="Lyrics",
                    text=combined_lyrics,
                )
            if meta.english_lyrics and meta.is_foreign:
                tags["USLT:Translation:eng"] = USLT(
                    encoding=3,
                    lang="eng",
                    desc="English Translation",
                    text=meta.english_lyrics,
                )

        tags.save(audio_path)

    @staticmethod
    def _tag_m4a(audio_path: str, meta: SongMetadata, embed_lyrics: bool):
        from mutagen.mp4 import MP4

        audio = MP4(audio_path)
        if meta.title:
            audio["\xa9nam"] = [meta.title]
        if meta.artist:
            audio["\xa9ART"] = [meta.artist]
        if meta.album:
            audio["\xa9alb"] = [meta.album]
        if embed_lyrics:
            combined = AudioTagger._format_embedded_lyrics(meta)
            if combined:
                audio["\xa9lyr"] = [combined]
        audio.save()

    @staticmethod
    def _tag_flac(audio_path: str, meta: SongMetadata, embed_lyrics: bool):
        from mutagen.flac import FLAC

        audio = FLAC(audio_path)
        if meta.title:
            audio["TITLE"] = meta.title
        if meta.artist:
            audio["ARTIST"] = meta.artist
        if meta.album:
            audio["ALBUM"] = meta.album
        if embed_lyrics:
            combined = AudioTagger._format_embedded_lyrics(meta)
            if combined:
                audio["LYRICS"] = combined
            if meta.english_lyrics:
                audio["TRANSLATION_EN"] = meta.english_lyrics
        audio.save()

    @staticmethod
    def _tag_ogg(audio_path: str, meta: SongMetadata, embed_lyrics: bool):
        from mutagen.oggvorbis import OggVorbis

        audio = OggVorbis(audio_path)
        if meta.title:
            audio["TITLE"] = meta.title
        if meta.artist:
            audio["ARTIST"] = meta.artist
        if meta.album:
            audio["ALBUM"] = meta.album
        if embed_lyrics:
            combined = AudioTagger._format_embedded_lyrics(meta)
            if combined:
                audio["LYRICS"] = combined
        audio.save()

    @classmethod
    def create_companion_lrc(
        cls,
        audio_path: str,
        meta: SongMetadata,
        offset_ms: int = 0,
        bilingual: bool = False,
    ) -> Optional[str]:
        """
        Creates a companion .lrc file right alongside the audio file with the same base name.
        Ensures media players (VLC, Poweramp, Walkman) automatically load synchronized lyrics.
        """
        lrc_text = (meta.synced_lrc or "").strip()
        if not lrc_text:
            return None

        base, _ = os.path.splitext(audio_path)
        companion_path = f"{base}.lrc"

        # Add or update [offset: +/-ms] tag if non-zero
        if offset_ms != 0:
            if "[offset:" in lrc_text:
                import re
                lrc_text = re.sub(r"\[offset:[^\]]*\]", f"[offset:{offset_ms}]", lrc_text)
            else:
                lrc_text = f"[offset:{offset_ms}]\n" + lrc_text

        with open(companion_path, "w", encoding="utf-8") as f:
            f.write(lrc_text)

        return companion_path

    @classmethod
    def create_companion_json(
        cls,
        audio_path: str,
        meta: SongMetadata,
    ) -> Optional[str]:
        """
        Creates a companion .json configuration file alongside the audio file,
        containing full song metadata and cleanly separated foreign and English lyrics.
        """
        base, _ = os.path.splitext(audio_path)
        companion_path = f"{base}.json"

        data = meta.to_dict()
        with open(companion_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return companion_path
