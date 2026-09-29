"""
Provider package exports.
"""

from .base import BaseLyricProvider
from .lrclib import LRCLIBProvider
from .netease import NetEaseProvider
from .kugou import KugouProvider

__all__ = [
    "BaseLyricProvider",
    "LRCLIBProvider",
    "NetEaseProvider",
    "KugouProvider",
]
