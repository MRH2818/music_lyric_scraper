"""
High-Level Song Scraper Engine.
Coordinates metadata parsing, audio scraping, duration verification, tagging, and companion LRC/JSON generation.
"""

import os
from typing import List, Optional, Dict, Any

from .models import SongMetadata, DownloadResult
from .metadata_parser import LyricFileParser
from .downloader import AudioDownloader
from .tagger import AudioTagger
from lyric_scraper.translator import LyricTranslator


class SongScraper:
    """
    Scrapes full audio tracks corresponding to specific lyric files with translation support.
    """

    def __init__(
        self,
        output_format: str = "mp3",
        bitrate: str = "192k",
        tolerance_seconds: float = 6.0,
        auto_translate: bool = True,
    ):
        self.output_format = output_format
        self.bitrate = bitrate
        self.tolerance_seconds = tolerance_seconds
        self.auto_translate = auto_translate
        self.translator = LyricTranslator() if auto_translate else None
        self.downloader = AudioDownloader(
            output_format=output_format,
            bitrate=bitrate,
            tolerance_seconds=tolerance_seconds,
        )

    def _ensure_translations(self, meta: SongMetadata):
        """If metadata is for a foreign language song without English translations, translate it."""
        if self.auto_translate and self.translator and meta.is_foreign and not meta.english_lyrics:
            if meta.plain_lyrics:
                meta.english_lyrics = self.translator.translate_text(meta.plain_lyrics, source_lang=meta.detected_language or "auto", target_lang="en")

    def scrape_from_lyric_file(
        self,
        lyric_path: str,
        output_dir: Optional[str] = None,
        output_path: Optional[str] = None,
        embed_lyrics: bool = True,
        companion_lrc: bool = True,
        companion_json: bool = True,
        offset_ms: int = 0,
    ) -> DownloadResult:
        """
        Scrapes and tags the audio track corresponding to a specific lyric file.
        """
        meta = LyricFileParser.parse_file(lyric_path)
        self._ensure_translations(meta)

        res = self.downloader.download_for_metadata(
            meta=meta,
            output_path=output_path,
            output_dir=output_dir,
        )

        if res.success and res.audio_path:
            # Tag the audio file
            AudioTagger.tag_audio_file(
                audio_path=res.audio_path,
                meta=meta,
                embed_lyrics=embed_lyrics,
            )

            # Export companion LRC
            if companion_lrc:
                comp_path = AudioTagger.create_companion_lrc(
                    audio_path=res.audio_path,
                    meta=meta,
                    offset_ms=offset_ms,
                )
                res.companion_lrc_path = comp_path

            # Export companion JSON configuration
            if companion_json:
                json_path = AudioTagger.create_companion_json(
                    audio_path=res.audio_path,
                    meta=meta,
                )
                res.companion_json_path = json_path

        return res

    def scrape_batch_from_directory(
        self,
        lyrics_dir: str,
        output_dir: Optional[str] = None,
        embed_lyrics: bool = True,
        companion_lrc: bool = True,
        companion_json: bool = True,
        offset_ms: int = 0,
        recursive: bool = False,
    ) -> List[DownloadResult]:
        """
        Scrapes audio tracks for all lyric files found inside a directory.
        """
        if not os.path.isdir(lyrics_dir):
            raise NotADirectoryError(f"Directory not found: {lyrics_dir}")

        supported_exts = {".json", ".lrc", ".srt", ".vtt", ".txt"}
        candidate_files: List[str] = []

        if recursive:
            for root, _, files in os.walk(lyrics_dir):
                for f in files:
                    if os.path.splitext(f)[1].lower() in supported_exts:
                        candidate_files.append(os.path.join(root, f))
        else:
            for f in os.listdir(lyrics_dir):
                full_path = os.path.join(lyrics_dir, f)
                if os.path.isfile(full_path) and os.path.splitext(f)[1].lower() in supported_exts:
                    candidate_files.append(full_path)

        # Deduplicate files by base song name, giving precedence to .json -> .lrc -> .srt -> .vtt -> .txt
        priority = {".json": 1, ".lrc": 2, ".srt": 3, ".vtt": 4, ".txt": 5}
        grouped: Dict[str, str] = {}

        for path in candidate_files:
            base, ext = os.path.splitext(os.path.basename(path))
            ext = ext.lower()
            if base not in grouped:
                grouped[base] = path
            else:
                existing_ext = os.path.splitext(grouped[base])[1].lower()
                if priority.get(ext, 99) < priority.get(existing_ext, 99):
                    grouped[base] = path

        results: List[DownloadResult] = []
        for file_path in grouped.values():
            try:
                res = self.scrape_from_lyric_file(
                    lyric_path=file_path,
                    output_dir=output_dir,
                    embed_lyrics=embed_lyrics,
                    companion_lrc=companion_lrc,
                    companion_json=companion_json,
                    offset_ms=offset_ms,
                )
                results.append(res)
            except Exception as e:
                results.append(
                    DownloadResult(
                        success=False,
                        metadata=SongMetadata(title=os.path.basename(file_path)),
                        error=str(e),
                    )
                )

        return results

    def scrape_song(
        self,
        title: str,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        duration: float = 0.0,
        plain_lyrics: Optional[str] = None,
        synced_lrc: Optional[str] = None,
        english_lyrics: Optional[str] = None,
        english_synced_lrc: Optional[str] = None,
        detected_language: Optional[str] = None,
        lines: Optional[List[Dict[str, Any]]] = None,
        output_dir: Optional[str] = None,
        output_path: Optional[str] = None,
        embed_lyrics: bool = True,
        companion_lrc: bool = True,
        companion_json: bool = True,
        offset_ms: int = 0,
    ) -> DownloadResult:
        """
        Directly scrapes audio given song metadata parameters without needing an existing file on disk.
        """
        is_foreign = bool(detected_language and detected_language != "en")
        meta = SongMetadata(
            title=title,
            artist=artist or "",
            album=album or "",
            duration=duration,
            plain_lyrics=plain_lyrics,
            synced_lrc=synced_lrc,
            english_lyrics=english_lyrics,
            english_synced_lrc=english_synced_lrc,
            detected_language=detected_language,
            is_foreign=is_foreign,
            lines=lines or [],
        )
        self._ensure_translations(meta)

        res = self.downloader.download_for_metadata(
            meta=meta,
            output_path=output_path,
            output_dir=output_dir,
        )

        if res.success and res.audio_path:
            AudioTagger.tag_audio_file(
                audio_path=res.audio_path,
                meta=meta,
                embed_lyrics=embed_lyrics,
            )

            if companion_lrc:
                comp_path = AudioTagger.create_companion_lrc(
                    audio_path=res.audio_path,
                    meta=meta,
                    offset_ms=offset_ms,
                )
                res.companion_lrc_path = comp_path

            if companion_json:
                json_path = AudioTagger.create_companion_json(
                    audio_path=res.audio_path,
                    meta=meta,
                )
                res.companion_json_path = json_path

        return res
