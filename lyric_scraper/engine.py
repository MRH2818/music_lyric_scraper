"""
Main Lyric Scraper Engine orchestrating search, multi-provider queries,
language filtering, automatic translation, and exports.
"""

from typing import List, Optional, Dict
import os
from .models import LyricTrack
from .parser import LRCParser
from .language import LanguageHelper
from .translator import LyricTranslator
from .providers.base import BaseLyricProvider
from .providers.lrclib import LRCLIBProvider
from .providers.netease import NetEaseProvider
from .providers.kugou import KugouProvider


class LyricScraper:
    """
    Multilingual time-scraped lyric engine with automatic translation pipeline.
    """

    def __init__(self, timeout: int = 10, auto_translate: bool = True, translate_to: str = "en"):
        self.timeout = timeout
        self.auto_translate = auto_translate
        self.translate_to = translate_to
        self.translator = LyricTranslator(timeout=timeout)
        self.providers: Dict[str, BaseLyricProvider] = {
            "lrclib": LRCLIBProvider(timeout=timeout),
            "netease": NetEaseProvider(timeout=timeout),
            "kugou": KugouProvider(timeout=timeout),
        }

    def translate_track(self, track: LyricTrack, target_lang: Optional[str] = None) -> LyricTrack:
        """Translates track lines and plain lyrics to target language (default 'en')."""
        target = target_lang or self.translate_to or "en"
        return self.translator.translate_track(track, target_lang=target)

    def search(
        self,
        query: str,
        artist: Optional[str] = None,
        language: Optional[str] = None,
        limit: int = 10,
        provider_names: Optional[List[str]] = None,
        translate: Optional[bool] = None,
    ) -> List[LyricTrack]:
        """
        Searches all available providers for synchronized lyrics matching the query.
        Filters and validates candidates against the target language if specified.
        Translates foreign-language lyrics to English when translate is enabled.
        """
        all_results: List[LyricTrack] = []
        target_norm = LanguageHelper.normalize_code(language)

        selected_providers = (
            [self.providers[p] for p in provider_names if p in self.providers]
            if provider_names
            else list(self.providers.values())
        )

        for p in selected_providers:
            try:
                tracks = p.search(query=query, artist=artist, language=target_norm, limit=limit)
                for t in tracks:
                    # Verify it has actual synced lines
                    if t.lines:
                        # Language check
                        if target_norm:
                            sample = t.plain_lyrics or "\n".join(l.text for l in t.lines)
                            if not LanguageHelper.matches_target(sample, target_norm):
                                continue
                        all_results.append(t)
            except Exception:
                continue

        # Deduplicate results by (title.lower(), artist.lower(), provider)
        seen = set()
        deduped: List[LyricTrack] = []
        for t in all_results:
            key = (t.title.strip().lower(), t.artist.strip().lower(), t.provider)
            if key not in seen:
                seen.add(key)
                deduped.append(t)

        # Sort / rank results:
        # Prioritize tracks with higher language confidence and more synced lines
        def score_track(t: LyricTrack) -> float:
            score = 0.0
            if target_norm and t.detected_language == target_norm:
                score += 50.0 + (t.language_confidence * 20.0)
            if artist and artist.lower() in t.artist.lower():
                score += 30.0
            if query.lower() in t.title.lower():
                score += 20.0
            score += min(len(t.lines), 50) * 0.5
            return score

        deduped.sort(key=score_track, reverse=True)
        top_results = deduped[:limit]

        # Automatic translation
        should_translate = self.auto_translate if translate is None else translate
        if should_translate:
            for t in top_results:
                self.translate_track(t, target_lang=self.translate_to)

        return top_results

    def get_lyrics(
        self,
        title: str,
        artist: Optional[str] = None,
        language: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        translate: Optional[bool] = None,
    ) -> Optional[LyricTrack]:
        """
        Fetches the best matching synchronized lyrics track with translation.
        """
        provider_names = [preferred_provider] if preferred_provider else None
        results = self.search(
            query=title,
            artist=artist,
            language=language,
            limit=5,
            provider_names=provider_names,
            translate=translate,
        )
        return results[0] if results else None

    @classmethod
    def format_output(cls, track: LyricTrack, format_type: str = "json") -> str:
        """
        Converts a LyricTrack to the specified format: 'json', 'lrc', 'srt', 'vtt', 'txt', 'eng_lrc', or 'bilingual_lrc'.
        """
        fmt = format_type.lower().strip().lstrip(".")
        if fmt == "json":
            return LRCParser.to_json(track)
        elif fmt == "lrc":
            return LRCParser.to_lrc(track)
        elif fmt in ("eng_lrc", "english_lrc"):
            return LRCParser.to_english_lrc(track)
        elif fmt in ("bilingual_lrc", "bi_lrc"):
            return LRCParser.to_bilingual_lrc(track)
        elif fmt == "srt":
            return LRCParser.to_srt(track)
        elif fmt == "vtt":
            return LRCParser.to_vtt(track)
        elif fmt == "txt":
            return LRCParser.to_txt(track)
        else:
            raise ValueError(f"Unsupported format '{format_type}'. Supported: json, lrc, srt, vtt, txt, eng_lrc, bilingual_lrc")

    @classmethod
    def save(cls, track: LyricTrack, output_path: str, format_type: Optional[str] = None) -> str:
        """
        Saves the formatted lyrics to a file.
        Infers format from output_path extension if format_type is not provided.
        """
        if not format_type:
            _, ext = os.path.splitext(output_path)
            format_type = ext.lstrip(".") if ext else "json"

        content = cls.format_output(track, format_type)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path
