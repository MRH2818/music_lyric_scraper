import pytest
from lyric_scraper.translator import LyricTranslator
from lyric_scraper.models import LyricTrack, LyricLine


def test_translator_init_and_cache():
    translator = LyricTranslator()
    assert translator.cache == {}

    # Test cache insertion
    translator.cache["ru:en:Голубой вагон"] = "Blue carriage"
    result = translator.translate_text("Голубой вагон", source_lang="ru", target_lang="en")
    assert result == "Blue carriage"


def test_translator_english_skip():
    translator = LyricTranslator()
    text = "Hello world this is a test"
    # When source is en and target is en, should skip network and return exact text
    result = translator.translate_text(text, source_lang="en", target_lang="en")
    assert result == text

    lines = ["Line 1", "Line 2"]
    batch_res = translator.translate_lines(lines, source_lang="en", target_lang="en")
    assert batch_res == lines


def test_translate_track():
    translator = LyricTranslator()
    translator.cache["ru:en:Медленно минуты уплывают в даль"] = "Slowly the minutes float away"
    translator.cache["ru:en:Встречи с ними ты уже не жди"] = "Don't wait to meet them anymore"

    track = LyricTrack(
        title="Голубой вагон",
        artist="Владимир Шаинский",
        detected_language="ru",
        lines=[
            LyricLine(start_ms=22780, end_ms=27050, text="Медленно минуты уплывают в даль", start_time="00:22.78"),
            LyricLine(start_ms=27050, end_ms=30490, text="Встречи с ними ты уже не жди", start_time="00:27.05"),
        ],
    )

    translated_track = translator.translate_track(track, target_lang="en")

    assert translated_track.lines[0].translation == "Slowly the minutes float away"
    assert translated_track.lines[1].translation == "Don't wait to meet them anymore"
    assert "Slowly the minutes float away" in translated_track.english_plain_lyrics
    assert "[00:22.78]Slowly the minutes float away" in translated_track.english_synced_lyrics


def test_translate_empty_lines():
    translator = LyricTranslator()
    lines = ["", "   ", ""]
    res = translator.translate_lines(lines, source_lang="es", target_lang="en")
    assert res == ["", "", ""]
