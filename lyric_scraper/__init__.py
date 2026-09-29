"""
Lyric Scraper - Multilingual Time-Scraped Synced Lyrics Engine
"""

from .models import LyricLine, LyricTrack
from .parser import LRCParser
from .language import LanguageHelper
from .translator import LyricTranslator
from .engine import LyricScraper

__version__ = "1.1.0"
__all__ = [
    "LyricLine",
    "LyricTrack",
    "LRCParser",
    "LanguageHelper",
    "LyricTranslator",
    "LyricScraper",
]
