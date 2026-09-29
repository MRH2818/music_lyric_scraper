import pytest
import json
from lyric_scraper.parser import LRCParser
from lyric_scraper.models import LyricTrack, LyricLine


SAMPLE_LRC = """[ti:Test Song]
[ar:Test Artist]
[al:Test Album]
[length:03:45]

[00:12.34]First line of lyrics
[00:15.50]Second line of lyrics
[00:20.00][00:25.00]Repeated chorus line
[00:30.123]Line with 3 millisecond digits
"""


def test_parse_lrc():
    lines, meta = LRCParser.parse_lrc(SAMPLE_LRC, duration=225.0)

    assert meta["ti"] == "Test Song"
    assert meta["ar"] == "Test Artist"
    assert len(lines) == 5

    # Chronologically sorted
    assert lines[0].start_ms == 12340
    assert lines[0].text == "First line of lyrics"
    assert lines[0].start_time == "00:12.34"

    assert lines[1].start_ms == 15500
    assert lines[1].text == "Second line of lyrics"

    # Multi-timestamp line should appear at 20.00 and 25.00
    assert lines[2].start_ms == 20000
    assert lines[2].text == "Repeated chorus line"
    assert lines[3].start_ms == 25000
    assert lines[3].text == "Repeated chorus line"

    # 3 millisecond digits
    assert lines[4].start_ms == 30123
    assert lines[4].text == "Line with 3 millisecond digits"


def test_to_lrc():
    track = LyricTrack(
        title="Oye Como Va",
        artist="Santana",
        lines=[
            LyricLine(start_ms=10000, end_ms=13000, text="Oye como va"),
            LyricLine(start_ms=14000, end_ms=17000, text="Mi ritmo"),
        ],
    )
    lrc_out = LRCParser.to_lrc(track)
    assert "[ti:Oye Como Va]" in lrc_out
    assert "[ar:Santana]" in lrc_out
    assert "[00:10.00]Oye como va" in lrc_out
    assert "[00:14.00]Mi ritmo" in lrc_out


def test_to_english_and_bilingual_lrc():
    track = LyricTrack(
        title="Голубой вагон",
        artist="Шаинский",
        lines=[
            LyricLine(start_ms=22780, end_ms=27050, text="Голубой вагон", translation="Blue carriage"),
        ],
    )
    eng_lrc = LRCParser.to_english_lrc(track)
    assert "[00:22.78]Blue carriage" in eng_lrc

    bi_lrc = LRCParser.to_bilingual_lrc(track)
    assert "[00:22.78]Голубой вагон (Blue carriage)" in bi_lrc


def test_to_srt():
    track = LyricTrack(
        title="Song",
        artist="Artist",
        lines=[
            LyricLine(start_ms=12300, end_ms=15800, text="Subtitle line", translation="English translation"),
        ],
    )
    srt_out = LRCParser.to_srt(track)
    assert "1" in srt_out
    assert "00:00:12,300 --> 00:00:15,800" in srt_out
    assert "Subtitle line" in srt_out
    assert "(English translation)" in srt_out


def test_to_vtt():
    track = LyricTrack(
        title="Song",
        artist="Artist",
        lines=[
            LyricLine(start_ms=12300, end_ms=15800, text="Subtitle line", translation="English translation"),
        ],
    )
    vtt_out = LRCParser.to_vtt(track)
    assert "WEBVTT" in vtt_out
    assert "00:00:12.300 --> 00:00:15.800" in vtt_out
    assert "Subtitle line" in vtt_out
    assert "(English translation)" in vtt_out


def test_to_json_separated_lyrics():
    track = LyricTrack(
        title="Голубой вагон",
        artist="Владимир Шаинский",
        detected_language="ru",
        language_confidence=0.95,
        lines=[
            LyricLine(start_ms=22780, end_ms=27050, text="Голубой вагон бежит", translation="The blue carriage runs"),
        ],
        plain_lyrics="Голубой вагон бежит",
        synced_lyrics="[00:22.78]Голубой вагон бежит",
        english_plain_lyrics="The blue carriage runs",
        english_synced_lyrics="[00:22.78]The blue carriage runs",
    )
    json_str = LRCParser.to_json(track)
    data = json.loads(json_str)

    assert data["title"] == "Голубой вагон"
    assert data["artist"] == "Владимир Шаинский"
    assert data["detected_language"] == "ru"
    assert data["is_foreign"] is True

    # Check separated lyrics object
    assert "lyrics" in data
    assert data["lyrics"]["foreign"]["language"] == "ru"
    assert data["lyrics"]["foreign"]["plain"] == "Голубой вагон бежит"
    assert data["lyrics"]["foreign"]["synced_lrc"] == "[00:22.78]Голубой вагон бежит"

    assert data["lyrics"]["english"]["language"] == "en"
    assert data["lyrics"]["english"]["plain"] == "The blue carriage runs"
    assert data["lyrics"]["english"]["synced_lrc"] == "[00:22.78]The blue carriage runs"

    # Check line fields
    assert len(data["lines"]) == 1
    assert data["lines"][0]["foreign"] == "Голубой вагон бежит"
    assert data["lines"][0]["english"] == "The blue carriage runs"
    assert data["lines"][0]["text"] == "Голубой вагон бежит"
    assert data["lines"][0]["translation"] == "The blue carriage runs"

    # Test roundtrip with from_json
    reconstructed = LRCParser.from_json(data)
    assert reconstructed.title == "Голубой вагон"
    assert reconstructed.detected_language == "ru"
    assert reconstructed.lines[0].text == "Голубой вагон бежит"
    assert reconstructed.lines[0].translation == "The blue carriage runs"
    assert reconstructed.english_plain_lyrics == "The blue carriage runs"
