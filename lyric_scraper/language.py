"""
Language detection, normalization, and script inspection utilities.
"""

import re
from typing import Tuple, Optional, Dict
from langdetect import DetectorFactory, detect_langs

# Enforce deterministic results from langdetect
DetectorFactory.seed = 0

LANGUAGE_MAP: Dict[str, str] = {
    # Spanish
    "es": "es", "spa": "es", "spanish": "es", "español": "es", "espanol": "es",
    # French
    "fr": "fr", "fra": "fr", "fre": "fr", "french": "fr", "français": "fr", "francais": "fr",
    # German
    "de": "de", "deu": "de", "ger": "de", "german": "de", "deutsch": "de",
    # Japanese
    "ja": "ja", "jpn": "ja", "jp": "ja", "japanese": "ja", "日本語": "ja", "nihongo": "ja",
    # Korean
    "ko": "ko", "kor": "ko", "korean": "ko", "한국어": "ko", "hangul": "ko",
    # Chinese (Mandarin/Cantonese)
    "zh": "zh", "chi": "zh", "zho": "zh", "chinese": "zh", "中文": "zh", "mandarin": "zh", "cantonese": "zh", "zh-cn": "zh", "zh-tw": "zh",
    # Italian
    "it": "it", "ita": "it", "italian": "it", "italiano": "it",
    # Portuguese
    "pt": "pt", "por": "pt", "portuguese": "pt", "português": "pt", "portugues": "pt",
    # Russian
    "ru": "ru", "rus": "ru", "russian": "ru", "русский": "ru",
    # English
    "en": "en", "eng": "en", "english": "en",
    # Arabic
    "ar": "ar", "ara": "ar", "arabic": "ar", "العربية": "ar",
    # Dutch
    "nl": "nl", "nld": "nl", "dut": "nl", "dutch": "nl", "nederlands": "nl",
    # Turkish
    "tr": "tr", "tur": "tr", "turkish": "tr", "türkçe": "tr", "turkce": "tr",
    # Polish
    "pl": "pl", "pol": "pl", "polish": "pl", "polski": "pl",
    # Swedish
    "sv": "sv", "swe": "sv", "swedish": "sv", "svenska": "sv",
    # Greek
    "el": "el", "ell": "el", "greek": "el", "ελληνικά": "el",
    # Hindi
    "hi": "hi", "hin": "hi", "hindi": "hi", "हिन्दी": "hi",
    # Vietnamese
    "vi": "vi", "vie": "vi", "vietnamese": "vi", "tiếng việt": "vi",
    # Indonesian
    "id": "id", "ind": "id", "indonesian": "id", "bahasa indonesia": "id",
    # Ukrainian
    "uk": "uk", "ukr": "uk", "ukrainian": "uk", "українська": "uk",
}

LANGUAGE_NAMES: Dict[str, str] = {
    "es": "Spanish (Español)",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "zh": "Chinese (中文)",
    "it": "Italian (Italiano)",
    "pt": "Portuguese (Português)",
    "ru": "Russian (Русский)",
    "en": "English",
    "ar": "Arabic (العربية)",
    "nl": "Dutch (Nederlands)",
    "tr": "Turkish (Türkçe)",
    "pl": "Polish (Polski)",
    "sv": "Swedish (Svenska)",
    "el": "Greek (Ελληνικά)",
    "hi": "Hindi (हिन्दी)",
    "vi": "Vietnamese (Tiếng Việt)",
    "id": "Indonesian (Bahasa)",
    "uk": "Ukrainian (Українська)",
}


class LanguageHelper:
    """Helper for identifying, validating, and matching lyrics languages."""

    # Script regular expressions
    KOREAN_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff]")
    JAPANESE_KANA_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")
    CHINESE_HANZI_RE = re.compile(r"[\u4e00-\u9fff]")
    CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")
    ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
    GREEK_RE = re.compile(r"[\u0370-\u03ff]")
    THAI_RE = re.compile(r"[\u0e00-\u0e7f]")
    HEBREW_RE = re.compile(r"[\u0590-\u05ff]")
    DEVANAGARI_RE = re.compile(r"[\u0900-\u097f]")

    @classmethod
    def normalize_code(cls, lang_input: Optional[str]) -> Optional[str]:
        """Normalizes any input language string (name, 2-letter, 3-letter) to standard 2-letter code."""
        if not lang_input:
            return None
        cleaned = lang_input.strip().lower()
        return LANGUAGE_MAP.get(cleaned, cleaned)

    @classmethod
    def get_language_name(cls, code: str) -> str:
        """Returns human-readable name for language code."""
        norm = cls.normalize_code(code) or code
        return LANGUAGE_NAMES.get(norm, norm.upper())

    @classmethod
    def detect_script(cls, text: str) -> Optional[str]:
        """Detects language based on specific unique alphabet scripts."""
        if cls.KOREAN_RE.search(text):
            return "ko"
        if cls.JAPANESE_KANA_RE.search(text):
            return "ja"
        if cls.CYRILLIC_RE.search(text):
            return "ru"
        if cls.ARABIC_RE.search(text):
            return "ar"
        if cls.GREEK_RE.search(text):
            return "el"
        if cls.THAI_RE.search(text):
            return "th"
        if cls.HEBREW_RE.search(text):
            return "he"
        if cls.DEVANAGARI_RE.search(text):
            return "hi"
        if cls.CHINESE_HANZI_RE.search(text) and not cls.JAPANESE_KANA_RE.search(text):
            return "zh"
        return None

    @classmethod
    def detect_language(cls, text: str) -> Tuple[str, float]:
        """
        Detects language of lyric text.
        Returns: (language_code, confidence_score)
        """
        if not text or len(text.strip()) < 5:
            return "unknown", 0.0

        # 1. First check unique alphabet/scripts
        script_lang = cls.detect_script(text)
        if script_lang:
            # Script detection for Asian/Cyrillic/Arabic scripts is highly accurate
            return script_lang, 0.95

        # 2. Clean text for statistical n-gram detection
        cleaned = re.sub(r"\[.*?\]", " ", text)
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        if len(cleaned) < 8:
            return "unknown", 0.0

        try:
            predictions = detect_langs(cleaned)
            if predictions:
                best = predictions[0]
                return best.lang, best.prob
        except Exception:
            pass

        return "unknown", 0.0

    @classmethod
    def matches_target(cls, text: str, target_language: Optional[str]) -> bool:
        """
        Checks if the provided lyrics text matches the target language.
        If target_language is None, returns True.
        """
        if not target_language:
            return True

        target_norm = cls.normalize_code(target_language)
        if not target_norm:
            return True

        detected_lang, confidence = cls.detect_language(text)

        # Direct match
        if detected_lang == target_norm:
            return True

        # Special handling for Chinese variants
        if target_norm in ("zh", "zh-cn", "zh-tw") and detected_lang in ("zh", "zh-cn", "zh-tw"):
            return True

        # If confidence is low or script is ambiguous, do secondary token match
        return False
