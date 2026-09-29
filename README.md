# Multilingual Synced Lyric & Song Audio Scraper Toolkit

A fast, lightweight, and robust **Python 3 CLI and library** designed for music lovers, karaoke setups, audio-text alignment pipelines, and language learners.

1. **Scrapes, synchronizes, translates, formats, and exports timestamped lyrics** (`.lrc`, `.srt`, `.vtt`, `.json`, `.txt`, `.eng_lrc`, `.bilingual_lrc`) across 20+ languages.
2. **Scrapes and synchronizes studio-quality song audio** (`.mp3`, `.m4a`, `.flac`, `.wav`, `.ogg`) matching lyric files, with **duration-matching safeguards against music video intros/dialogue**.
3. **Embeds metadata & lyrics** into audio ID3 tags and generates companion `.lrc` and `.json` files.

---

## Table of Contents

- [Key Features](#key-features)
- [Project Architecture](#project-architecture)
- [Installation & Setup](#installation--setup)
- [CLI Reference: Lyric Scraper (`cli.py`)](#cli-reference-lyric-scraper-clipy)
  - [Full Argument Reference](#cli-arguments-clipy)
  - [Usage Examples](#cli-examples-clipy)
- [CLI Reference: Song Audio Scraper (`song_cli.py`)](#cli-reference-song-audio-scraper-song_clipy)
  - [Full Argument Reference](#cli-arguments-song_clipy)
  - [Usage Examples](#cli-examples-song_clipy)
- [Supported Formats & Specifications](#supported-formats--specifications)
- [Python API Usage](#python-api-usage)
  - [1. Lyric Scraper Engine](#1-lyric-scraper-engine)
  - [2. Song Scraper & Audio Synchronizer](#2-song-scraper--audio-synchronizer)
  - [3. Batch Directory Audio Processing](#3-batch-directory-audio-processing)
  - [4. Parsing Lyric Files Manually](#4-parsing-lyric-files-manually)
- [Running Tests](#running-tests)
- [License](#license)

---

## Key Features

- **Multi-Source Lyric Aggregation**: Fetches from **LRCLIB**, **NetEase Cloud Music**, and **Kugou** with zero API keys required.
- **Foreign Lyric Translation**: Built-in translation pipeline for foreign songs to English (or any specified target language) with in-memory caching and fallback providers (Google Translate GTX & MyMemory API).
- **Audio Matching Safeguards**: Duration-matching filter rejects music videos with non-musical dialogue or extended intros/outros and prioritizes studio/album cuts.
- **Direct Studio Stream Fallback**: Pulls exact studio master tracks when available from streaming providers.
- **Automatic Tagging & ID3 Embedding**:
  - MP3: ID3v2 tags (`TIT2`, `TPE1`, `TALB`, `USLT` synced/unsynced).
  - M4A/MP4: Apple iTunes atoms (`©nam`, `©ART`, `©alb`, `©lyr`).
  - FLAC / OGG: Vorbis comments (`TITLE`, `ARTIST`, `ALBUM`, `LYRICS`, `TRANSLATION_EN`).
- **Companion Files Generator**:
  - Automatically exports same-named `.lrc` alongside audio tracks for immediate lyrics display in VLC, Poweramp, Walkman, Foobar2000, etc. Supports `[offset: +/-ms]` adjustments.
  - Automatically exports structured companion `.json` configuration files.
- **Extensive Export Formats**:
  - `.lrc` - Standard synchronized lyrics (`[mm:ss.xx]`).
  - `.srt` - SubRip subtitle format with start and end millisecond timestamps.
  - `.vtt` - WebVTT format for HTML5 web players (`<track>`).
  - `.json` - Structured JSON schema with milliseconds, timestamps, and line text.
  - `.txt` - Clean plain text lyrics.
  - `eng_lrc` - Synchronized English translation LRC.
  - `bilingual_lrc` - Original foreign lyric line with inline English translation.

---

## Project Architecture

```
friendly-newton/
├── cli.py                     # Lyric Scraper CLI interface
├── song_cli.py                # Song Audio Scraper CLI interface
├── sample_songs.txt           # Sample batch file for batch operations
├── requirements.txt           # Project dependencies
├── lyric_scraper/             # Synced lyrics extraction package
│   ├── engine.py              # Main LyricScraper coordinating providers & translation
│   ├── language.py            # Language detection, normalization & script inspection
│   ├── models.py              # LyricLine and LyricTrack data classes
│   ├── parser.py              # LRC, SRT, VTT, JSON, TXT parsers & formatters
│   ├── translator.py          # Translation engine (Google GTX + MyMemory)
│   └── providers/             # Lyric providers (LRCLIB, NetEase, Kugou)
├── song_scraper/              # Audio scraping & synchronization package
│   ├── downloader.py          # yt-dlp wrapper with duration matching & studio priority
│   ├── engine.py              # SongScraper coordinator
│   ├── metadata_parser.py     # Parser for .json, .lrc, .srt, .vtt, .txt lyric files
│   ├── models.py              # SongMetadata, AudioCandidate, DownloadResult
│   └── tagger.py              # Mutagen audio tagger & companion LRC/JSON generator
└── tests/                     # Unit and integration test suite
```

---

## Installation & Setup

### Prerequisites
- Python 3.9+ (Python 3.10+ recommended)
- `ffmpeg` (recommended in PATH for yt-dlp audio format conversion)

### 1. Clone & Setup Virtual Environment

**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## CLI Reference: Lyric Scraper (`cli.py`)

Run via script or module:
```bash
python cli.py [query] [options]
# or
python -m lyric_scraper [query] [options]
```

### CLI Arguments (`cli.py`)

| Argument | Description | Default |
|---|---|---|
| `query` | Song title or search query (positional) | None |
| `-a`, `--artist` | Artist name to narrow search precision | None |
| `-l`, `--lang`, `--language` | Language code (e.g. `es`, `ja`, `fr`, `de`, `ko`, `zh`, `ru`) or name | None |
| `-f`, `--format` | Output format: `json`, `lrc`, `srt`, `vtt`, `txt`, `eng_lrc`, `bilingual_lrc` | `json` |
| `-o`, `--output` | Destination output file path (e.g., `song.lrc`) | None (Terminal preview) |
| `-s`, `--search` | Interactive mode to select from top matches | Disabled |
| `-b`, `--batch` | Path to text file containing song list (one per line) | None |
| `-d`, `--out-dir` | Output directory for batch downloads | `./lyrics` |
| `-p`, `--provider` | Force specific provider: `lrclib`, `netease`, `kugou` | Auto (best match) |
| `--no-translate` | Disable automatic translation of foreign lyrics | Translation enabled |
| `--translate-to` | Target language code for translation | `en` |
| `--preview` | Show parsed lyrics and English translations in terminal | Auto if no `-o` |
| `--list-languages` | List all supported language codes and full names | - |
| `--audio`, `--with-audio` | Also download matching synchronized studio audio | Disabled |
| `--audio-dir` | Output directory for downloaded audio | `./audio_output` |
| `--audio-format` | Audio format when downloading with `--audio`: `mp3`, `m4a`, `flac`, `wav` | `mp3` |

### CLI Examples (`cli.py`)

#### 1. Search and Save Lyrics to File
```bash
# Save Spanish synchronized lyrics as standard LRC
python cli.py "La Camisa Negra" -a "Juanes" -l es -f lrc -o juanes.lrc

# Save bilingual LRC (Original text + English translation)
python cli.py "Homura" -a "LiSA" -l ja -f bilingual_lrc -o homura_bilingual.lrc

# Save subtitles as WebVTT or SRT
python cli.py "99 Luftballons" -a "Nena" -l de -f vtt -o nena.vtt
python cli.py "Non, je ne regrette rien" -a "Edith Piaf" -l fr -f srt -o piaf.srt
```

#### 2. Interactive Search Mode
```bash
# Interactively preview candidates and pick the best match
python cli.py --search "Plastic Love" --lang ja
```

#### 3. Single Command: Lyrics + Matching Studio Audio
```bash
# Downloads synchronized lyrics and matching audio (.mp3) with embedded tags & companion LRC
python cli.py "A Dios Le Pido" --artist "Juanes" --lang es --audio -o juanes.lrc --audio-dir ./audio_output/
```

#### 4. Batch Download Lyrics from a Song List
```bash
# Batch file format: "Artist - Title" or "Title" on each line
python cli.py --batch sample_songs.txt -f json -d ./lyrics_batch/
```

#### 5. List Supported Languages
```bash
python cli.py --list-languages
```

---

## CLI Reference: Song Audio Scraper (`song_cli.py`)

Scrapes studio audio matching an existing lyric file, a directory of lyric files, or a direct song query.

```bash
python song_cli.py [target] [options]
```

### CLI Arguments (`song_cli.py`)

| Argument | Description | Default |
|---|---|---|
| `target` | Path to a lyric file (`.json`, `.lrc`, `.srt`, `.vtt`, `.txt`), directory of lyric files, or a song title query | None |
| `-a`, `--artist` | Artist name (when specifying song title directly) | None |
| `--dir`, `--lyrics-dir` | Directory containing lyric files for batch audio scraping | None |
| `-d`, `--out-dir` | Output directory for downloaded audio | `./audio_output` |
| `-o`, `--output` | Exact destination audio file path (e.g., `song.mp3`) | Auto-named |
| `-f`, `--format` | Audio format: `mp3`, `m4a`, `flac`, `wav`, `ogg` | `mp3` |
| `-b`, `--bitrate` | Bitrate quality: `128k`, `192k`, `256k`, `320k` | `192k` |
| `--tolerance` | Maximum allowed duration difference in seconds between lyrics and audio | `6.0` |
| `--offset` | Millisecond offset to add to companion LRC (`+500` or `-300`) | `0` |
| `--no-embed-lyrics` | Skip embedding lyrics into ID3 / container tags | Embed enabled |
| `--no-companion-lrc` | Do not generate companion `.lrc` file beside audio | Generate enabled |
| `--no-companion-json` | Do not generate companion `.json` configuration beside audio | Generate enabled |
| `--no-translate` | Disable foreign-to-English translation | Translation enabled |

### CLI Examples (`song_cli.py`)

#### 1. Download Audio Matching a Lyric File
```bash
# From a JSON lyric file (uses metadata, duration & lines)
python song_cli.py lyrics_batch/Juanes_A\ Dios\ Le\ Pido.json -d ./audio_output/

# From an LRC file
python song_cli.py output/juanes.lrc -d ./audio_output/
```

#### 2. Batch Download Audio for All Lyric Files in a Directory
```bash
python song_cli.py --dir ./lyrics_batch/ -d ./audio_output/
```

#### 3. Custom Bitrate, Format, and Timestamp Offset
```bash
# Download 320k MP3 with a +250ms timestamp offset in companion LRC
python song_cli.py song.json -f mp3 -b 320k --offset 250 -d ./audio_output/

# Lossless FLAC download
python song_cli.py song.lrc -f flac -d ./audio_output/
```

#### 4. Direct Song Search & Audio Download
```bash
python song_cli.py "La Camisa Negra" -a "Juanes" -f mp3 -b 320k -d ./audio_output/
```

---

## Supported Formats & Specifications

### Lyric Output Formats

| Format | Extension | Notes |
|---|---|---|
| **JSON** | `.json` | Full structured output with milliseconds, timestamps, text, translations, and metadata. |
| **LRC** | `.lrc` | Standard synchronized lyrics (`[mm:ss.xx] Lyric text`). |
| **Bilingual LRC** | `.bilingual_lrc` | Standard LRC with English translation inline: `[mm:ss.xx] Foreign (English)`. |
| **English LRC** | `.eng_lrc` | Translated LRC with synchronized English lines only. |
| **SRT** | `.srt` | SubRip subtitle format with millisecond `-->` timestamps and bilingual translation. |
| **WebVTT** | `.vtt` | Standard HTML5 WebVTT video track format. |
| **TXT** | `.txt` | Plain text lyrics without timestamps. |

### Audio Container Formats

| Format | Extension | Tagging Mechanism | Supported Tags |
|---|---|---|---|
| **MP3** | `.mp3` | ID3v2.4 (`mutagen.id3`) | `TIT2` (Title), `TPE1` (Artist), `TALB` (Album), `USLT` (Lyrics & Translation) |
| **M4A / AAC** | `.m4a` | MP4 Atoms (`mutagen.mp4`) | `©nam`, `©ART`, `©alb`, `©lyr` |
| **FLAC** | `.flac` | Vorbis Comment (`mutagen.flac`) | `TITLE`, `ARTIST`, `ALBUM`, `LYRICS`, `TRANSLATION_EN` |
| **OGG** | `.ogg` | Vorbis Comment (`mutagen.oggvorbis`) | `TITLE`, `ARTIST`, `ALBUM`, `LYRICS` |
| **WAV** | `.wav` | Standard PCM Audio | Uncompressed wave stream |

---

## Python API Usage

### 1. Lyric Scraper Engine
```python
from lyric_scraper import LyricScraper

scraper = LyricScraper(auto_translate=True, translate_to="en")

# Search and fetch synchronized lyric track
track = scraper.get_lyrics(title="A Dios Le Pido", artist="Juanes", language="es")

if track:
    print(f"Title: {track.title}")
    print(f"Language: {track.detected_language} (confidence: {track.language_confidence})")
    print(f"Synced lines count: {len(track.lines)}")

    # Export to different formats
    scraper.save(track, "juanes.json", format_type="json")
    scraper.save(track, "juanes.lrc", format_type="lrc")
    scraper.save(track, "juanes_bilingual.lrc", format_type="bilingual_lrc")
    scraper.save(track, "juanes.srt", format_type="srt")
    scraper.save(track, "juanes.vtt", format_type="vtt")
```

### 2. Song Scraper & Audio Synchronizer
```python
from song_scraper import SongScraper

scraper = SongScraper(output_format="mp3", bitrate="320k", tolerance_seconds=5.0)

# Scrape audio matching a specific lyric file
result = scraper.scrape_from_lyric_file(
    lyric_path="lyrics_batch/Juanes_A Dios Le Pido.json",
    output_dir="./audio_output",
    embed_lyrics=True,
    companion_lrc=True,
    companion_json=True,
    offset_ms=0,
)

if result.success:
    print(f"Downloaded Audio: {result.audio_path}")
    print(f"Companion LRC: {result.companion_lrc_path}")
    print(f"Companion JSON: {result.companion_json_path}")
    print(f"Audio Duration: {result.duration:.2f}s (Diff: {result.duration_diff:.2f}s)")
```

### 3. Batch Directory Audio Processing
```python
from song_scraper import SongScraper

scraper = SongScraper(output_format="mp3", bitrate="192k")
results = scraper.scrape_batch_from_directory(
    lyrics_dir="./lyrics_batch",
    output_dir="./audio_output",
    embed_lyrics=True,
    companion_lrc=True,
)

for res in results:
    status = "SUCCESS" if res.success else f"FAILED: {res.error}"
    print(f"{res.metadata.title} - {res.metadata.artist}: {status}")
```

### 4. Parsing Lyric Files Manually
```python
from song_scraper import LyricFileParser

meta = LyricFileParser.parse_file("song.lrc")
print(f"Title: {meta.title}, Artist: {meta.artist}, Duration: {meta.duration}s")
print(f"Detected Language: {meta.detected_language}")
```

---

## Running Tests

To run the complete test suite:

```bash
# Windows
.\.venv\Scripts\python.exe -m pytest

# Linux / macOS
python3 -m pytest
```

---

## License

MIT License. Designed and maintained for open-source audio and language learning workflows.
