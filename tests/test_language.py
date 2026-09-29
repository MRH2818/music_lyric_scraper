import pytest
from lyric_scraper.language import LanguageHelper


def test_language_normalization():
    assert LanguageHelper.normalize_code("Spanish") == "es"
    assert LanguageHelper.normalize_code("español") == "es"
    assert LanguageHelper.normalize_code("FR") == "fr"
    assert LanguageHelper.normalize_code("japanese") == "ja"
    assert LanguageHelper.normalize_code("日本語") == "ja"
    assert LanguageHelper.normalize_code("German") == "de"
    assert LanguageHelper.normalize_code("korean") == "ko"
    assert LanguageHelper.normalize_code("chinese") == "zh"


def test_script_detection():
    # Japanese kana
    assert LanguageHelper.detect_script("強くなれる理由を知った 僕を連れて進め") == "ja"
    # Korean Hangul
    assert LanguageHelper.detect_script("동해 물과 백두산이 마르고 닳도록") == "ko"
    # Russian Cyrillic
    assert LanguageHelper.detect_script("Пусть бегут неуклюже пешеходы по лужам") == "ru"
    # Arabic
    assert LanguageHelper.detect_script("حبيبي يا نور العين يا ساكن خيالي") == "ar"
    # Chinese Hanzi (without kana)
    assert LanguageHelper.detect_script("夜空中最亮的星 能否听清 那仰望的人 心底的孤独和叹息") == "zh"


def test_language_matching():
    # Spanish lyrics
    es_lyrics = """
    Tengo la camisa negra
    Hoy mi amor está de luto
    Hoy tengo en el alma una pena
    Y es por culpa de tu embrujo
    """
    assert LanguageHelper.matches_target(es_lyrics, "es") is True
    assert LanguageHelper.matches_target(es_lyrics, "fr") is False

    # French lyrics
    fr_lyrics = """
    Non, rien de rien
    Non, je ne regrette rien
    Ni le bien qu'on m'a fait
    Ni le mal, tout ça m'est bien égal
    """
    assert LanguageHelper.matches_target(fr_lyrics, "fr") is True
    assert LanguageHelper.matches_target(fr_lyrics, "de") is False

    # German lyrics
    de_lyrics = """
    Hast du etwas Zeit für mich?
    Dann singe ich ein Lied für dich
    Von 99 Luftballons
    Auf ihrem Weg zum Horizont
    """
    assert LanguageHelper.matches_target(de_lyrics, "de") is True
    assert LanguageHelper.matches_target(de_lyrics, "es") is False
