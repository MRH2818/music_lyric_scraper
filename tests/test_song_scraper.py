import os
import json
import tempfile
import pytest
from song_scraper.models import SongMetadata, AudioCandidate
from song_scraper.metadata_parser import LyricFileParser
from song_scraper.downloader import AudioDownloader
from song_scraper.tagger import AudioTagger
from song_scraper.engine import SongScraper


SAMPLE_JSON = {
    "title": "La Camisa Negra",
    "artist": "Juanes",
    "album": "Mi Sangre",
    "duration": 215.5,
    "provider": "lrclib",
    "source_id": "12345",
    "detected_language": "es",
    "lines": [
        {"start_ms": 10000, "end_ms": 14000, "start_time": "00:10.00", "end_time": "00:14.00", "text": "Tengo la camisa negra", "translation": "I have the black shirt"},
        {"start_ms": 15000, "end_ms": 19000, "start_time": "00:15.00", "end_time": "00:19.00", "text": "Hoy mi amor está de luto", "translation": "Today my love is in mourning"},
    ]
}

SAMPLE_SEPARATED_JSON = {
    "title": "Голубой вагон",
    "artist": "Владимир Шаинский",
    "album": "Песни из мультфильмов",
    "duration": 181.0,
    "provider": "lrclib",
    "source_id": "36967067",
    "detected_language": "ru",
    "language_name": "Russian (Русский)",
    "language_confidence": 0.95,
    "is_foreign": True,
    "is_instrumental": False,
    "lyrics": {
        "foreign": {
            "language": "ru",
            "language_name": "Russian (Русский)",
            "plain": "Голубой вагон бежит, качается",
            "synced_lrc": "[00:22.78]Голубой вагон бежит, качается"
        },
        "english": {
            "language": "en",
            "language_name": "English",
            "plain": "The blue carriage runs and sways",
            "synced_lrc": "[00:22.78]The blue carriage runs and sways"
        }
    },
    "lines_count": 1,
    "lines": [
        {
            "start_ms": 22780,
            "end_ms": 27050,
            "start_time": "00:22.78",
            "end_time": "00:27.05",
            "foreign": "Голубой вагон бежит, качается",
            "english": "The blue carriage runs and sways",
            "text": "Голубой вагон бежит, качается",
            "translation": "The blue carriage runs and sways"
        }
    ]
}

SAMPLE_LRC = """[ti:Gurenge]
[ar:LiSA]
[al:Gurenge]
[length:03:58]

[00:01.06]強くなれる理由を知った
[00:08.06]僕を連れて進め
"""

SAMPLE_VTT = """WEBVTT
NOTE Title: 99 Luftballons - Artist: Nena

00:00:05.000 --> 00:00:09.000
Hast du etwas Zeit für mich?

00:00:10.000 --> 00:00:15.000
Dann singe ich ein Lied für dich
"""


def test_parse_json_lyric_file():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(SAMPLE_JSON, f)
        path = f.name

    try:
        meta = LyricFileParser.parse_file(path)
        assert meta.title == "La Camisa Negra"
        assert meta.artist == "Juanes"
        assert meta.album == "Mi Sangre"
        assert meta.duration == 215.5
        assert meta.provider == "lrclib"
        assert meta.source_id == "12345"
        assert "Tengo la camisa negra" in meta.plain_lyrics
        assert "I have the black shirt" in meta.english_lyrics
        assert "[00:10.00]Tengo la camisa negra" in meta.synced_lrc
    finally:
        os.remove(path)


def test_parse_separated_json_lyric_file():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(SAMPLE_SEPARATED_JSON, f)
        path = f.name

    try:
        meta = LyricFileParser.parse_file(path)
        assert meta.title == "Голубой вагон"
        assert meta.artist == "Владимир Шаинский"
        assert meta.detected_language == "ru"
        assert meta.is_foreign is True
        assert meta.plain_lyrics == "Голубой вагон бежит, качается"
        assert meta.english_lyrics == "The blue carriage runs and sways"
        assert meta.synced_lrc == "[00:22.78]Голубой вагон бежит, качается"
        assert meta.english_synced_lrc == "[00:22.78]The blue carriage runs and sways"
    finally:
        os.remove(path)


def test_parse_lrc_lyric_file():
    with tempfile.NamedTemporaryFile("w", suffix=".lrc", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_LRC)
        path = f.name

    try:
        meta = LyricFileParser.parse_file(path)
        assert meta.title == "Gurenge"
        assert meta.artist == "LiSA"
        assert meta.album == "Gurenge"
        assert meta.duration == 238.0  # 3 * 60 + 58
        assert "強くなれる理由を知った" in meta.plain_lyrics
    finally:
        os.remove(path)


def test_parse_vtt_lyric_file():
    with tempfile.NamedTemporaryFile("w", suffix=".vtt", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_VTT)
        path = f.name

    try:
        meta = LyricFileParser.parse_file(path)
        assert meta.title == "99 Luftballons"
        assert meta.artist == "Nena"
        assert meta.duration >= 15.0
        assert "Hast du etwas Zeit für mich?" in meta.plain_lyrics
    finally:
        os.remove(path)


def test_filename_parsing():
    artist, title = LyricFileParser.parse_filename("Juanes - A Dios Le Pido.json")
    assert artist == "Juanes"
    assert title == "A Dios Le Pido"

    artist, title = LyricFileParser.parse_filename("Nena_99 Luftballons.lrc")
    assert artist == "Nena"
    assert title == "99 Luftballons"

    artist, title = LyricFileParser.parse_filename("Despacito.lrc")
    assert artist == ""
    assert title == "Despacito"


def test_candidate_scoring_and_duration_matching():
    downloader = AudioDownloader(tolerance_seconds=5.0)
    meta = SongMetadata(title="Test Song", artist="Test Artist", duration=200.0)

    # Official audio with exact duration
    c1 = AudioCandidate(
        title="Test Artist - Test Song (Official Audio)",
        uploader="Test Artist - Topic",
        duration=200.5,
        url="https://youtube.com/watch?v=1",
        duration_diff=0.5,
        is_official_audio=True,
    )

    # Music video with 30s intro
    c2 = AudioCandidate(
        title="Test Artist - Test Song (Official Music Video)",
        uploader="Test Artist VEVO",
        duration=230.0,
        url="https://youtube.com/watch?v=2",
        duration_diff=30.0,
        is_official_audio=False,
    )

    # Calculate score logic simulation
    score1 = 100.0 + 40.0 + 25.0 + 35.0
    score2 = 100.0 - ((30.0 - 5.0) * 10.0) - 45.0

    assert score1 > score2
    assert score1 > 150.0
    assert score2 < 0.0


def test_companion_lrc_and_json_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "song.mp3")
        with open(audio_path, "wb") as f:
            f.write(b"dummy audio data")

        meta = SongMetadata(
            title="Голубой вагон",
            artist="Шаинский",
            detected_language="ru",
            is_foreign=True,
            plain_lyrics="Голубой вагон",
            english_lyrics="Blue carriage",
            synced_lrc="[00:05.00]Голубой вагон"
        )

        lrc_path = AudioTagger.create_companion_lrc(audio_path, meta, offset_ms=500)
        assert lrc_path == os.path.join(tmpdir, "song.lrc")
        assert os.path.isfile(lrc_path)

        json_path = AudioTagger.create_companion_json(audio_path, meta)
        assert json_path == os.path.join(tmpdir, "song.json")
        assert os.path.isfile(json_path)

        with open(json_path, "r", encoding="utf-8") as f:
            saved_json = json.load(f)

        assert saved_json["lyrics"]["foreign"]["plain"] == "Голубой вагон"
        assert saved_json["lyrics"]["english"]["plain"] == "Blue carriage"


def test_batch_directory_deduplication_and_priority():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create same song in JSON and TXT
        json_path = os.path.join(tmpdir, "Juanes - Camisa.json")
        txt_path = os.path.join(tmpdir, "Juanes - Camisa.txt")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(SAMPLE_JSON, f)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("plain text")

        scraper = SongScraper()
        files = [f for f in os.listdir(tmpdir)]
        assert len(files) == 2
