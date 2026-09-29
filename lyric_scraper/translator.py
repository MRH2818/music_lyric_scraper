"""
Automatic lyrics translation engine for foreign-language songs.
Supports batch line translation, in-memory caching, and multi-service fallbacks.
"""

import re
from typing import List, Optional, Dict
import requests
from .models import LyricTrack, LyricLine
from .language import LanguageHelper


class LyricTranslator:
    """
    Translates foreign-language lyrics to English (or any specified target language).
    """

    def __init__(self, timeout: int = 8):
        self.timeout = timeout
        self.cache: Dict[str, str] = {}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _translate_google_gtx(self, text: str, source_lang: str = "auto", target_lang: str = "en") -> Optional[str]:
        """Translates text using Google Translate web service."""
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": source_lang or "auto",
                "tl": target_lang,
                "dt": "t",
                "q": text,
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    translated_chunks = [segment[0] for segment in data[0] if isinstance(segment, list) and segment and segment[0]]
                    return "".join(translated_chunks)
        except Exception:
            pass
        return None

    def _translate_mymemory(self, text: str, source_lang: str = "auto", target_lang: str = "en") -> Optional[str]:
        """Fallback translation using MyMemory API."""
        try:
            sl = source_lang if source_lang and source_lang != "auto" else "autodetect"
            url = "https://api.mymemory.translated.net/get"
            params = {
                "q": text[:500],  # MyMemory limit per request
                "langpair": f"{sl}|{target_lang}",
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                trans = data.get("responseData", {}).get("translatedText")
                if trans:
                    return trans
        except Exception:
            pass
        return None

    def translate_text(self, text: str, source_lang: Optional[str] = "auto", target_lang: str = "en") -> str:
        """
        Translates a single string. Uses cache when available.
        """
        if not text or not text.strip():
            return ""

        clean_text = text.strip()
        cache_key = f"{source_lang}:{target_lang}:{clean_text}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # If already English and target is English, return original
        if source_lang == "en" and target_lang == "en":
            return clean_text

        translated = self._translate_google_gtx(clean_text, source_lang=source_lang or "auto", target_lang=target_lang)
        if not translated:
            translated = self._translate_mymemory(clean_text, source_lang=source_lang or "auto", target_lang=target_lang)

        result = (translated.strip() if translated else clean_text)
        self.cache[cache_key] = result
        return result

    def translate_lines(
        self,
        lines: List[str],
        source_lang: Optional[str] = "auto",
        target_lang: str = "en",
    ) -> List[str]:
        """
        Translates a list of lyric lines efficiently using batching.
        """
        if not lines:
            return []

        # If source is English and target is English, skip translation
        if source_lang == "en" and target_lang == "en":
            return list(lines)

        # Separate uncached non-empty lines for batch request
        results: List[Optional[str]] = [None] * len(lines)
        to_translate_indices: List[int] = []
        to_translate_texts: List[str] = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                results[i] = ""
                continue
            cache_key = f"{source_lang}:{target_lang}:{stripped}"
            if cache_key in self.cache:
                results[i] = self.cache[cache_key]
            else:
                to_translate_indices.append(i)
                to_translate_texts.append(stripped)

        if to_translate_texts:
            # Batch translate in chunks of 40 lines to avoid URL/payload limits
            chunk_size = 40
            for offset in range(0, len(to_translate_texts), chunk_size):
                chunk_indices = to_translate_indices[offset : offset + chunk_size]
                chunk_texts = to_translate_texts[offset : offset + chunk_size]

                # Use newline join with boundary protection
                combined = "\n".join(chunk_texts)
                batch_trans = self._translate_google_gtx(combined, source_lang=source_lang or "auto", target_lang=target_lang)

                if batch_trans:
                    translated_split = batch_trans.split("\n")
                    if len(translated_split) == len(chunk_texts):
                        for idx, orig_text, trans_line in zip(chunk_indices, chunk_texts, translated_split):
                            cleaned_trans = trans_line.strip()
                            results[idx] = cleaned_trans
                            self.cache[f"{source_lang}:{target_lang}:{orig_text}"] = cleaned_trans
                        continue

                # If batch splitting failed or mismatched, translate individually
                for idx, orig_text in zip(chunk_indices, chunk_texts):
                    trans = self.translate_text(orig_text, source_lang=source_lang, target_lang=target_lang)
                    results[idx] = trans

        return [r if r is not None else lines[i] for i, r in enumerate(results)]

    def translate_track(self, track: LyricTrack, target_lang: str = "en") -> LyricTrack:
        """
        Translates all lines and plain lyrics in a LyricTrack, generating english synced LRC.
        """
        src_lang = track.detected_language or "auto"

        # Check if translation is needed
        if src_lang == "en" and target_lang == "en":
            for line in track.lines:
                if not line.translation:
                    line.translation = line.text
            track.english_plain_lyrics = track.plain_lyrics or "\n".join(l.text for l in track.lines)
            track.english_synced_lyrics = track.synced_lyrics
            return track

        # Extract texts from lines
        line_texts = [line.text for line in track.lines]
        translated_lines = self.translate_lines(line_texts, source_lang=src_lang, target_lang=target_lang)

        # Assign back to lines and build english synced LRC
        eng_lrc_lines = []
        for line, trans in zip(track.lines, translated_lines):
            line.translation = trans
            if trans:
                eng_lrc_lines.append(f"{line.start_time}{trans}" if line.start_time.startswith("[") else f"[{line.start_time}]{trans}")

        # English plain lyrics
        track.english_plain_lyrics = "\n".join(translated_lines)
        track.english_synced_lyrics = "\n".join(eng_lrc_lines)

        return track
