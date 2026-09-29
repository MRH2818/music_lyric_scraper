#!/usr/bin/env python3
"""
Command-Line Interface for Multilingual Synced Lyric Scraper.
Scrapes timestamped lyrics, translates foreign lyrics to English, and exports structured configurations.
"""

import argparse
import sys
import os
from typing import Optional

# Ensure standard output and standard error use UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from lyric_scraper import LyricScraper, LanguageHelper
from lyric_scraper.models import LyricTrack

console = Console(force_terminal=True, legacy_windows=False)


def print_banner():
    banner_text = (
        "[bold cyan]Lyric Scraper[/bold cyan] [dim]- Multilingual Synced Lyrics & English Translation Pipeline[/dim]"
    )
    console.print(Panel(banner_text, border_style="cyan"))


def list_languages():
    table = Table(title="Supported & Detected Languages", border_style="cyan", show_header=True)
    table.add_column("Code", style="bold yellow", width=10)
    table.add_column("Language Name", style="green")

    from lyric_scraper.language import LANGUAGE_NAMES
    for code, name in sorted(LANGUAGE_NAMES.items()):
        table.add_row(code, name)
    console.print(table)


def preview_lyrics(track: LyricTrack, max_lines: int = 12):
    has_translation = any(l.translation for l in track.lines)
    is_foreign = bool(track.detected_language and track.detected_language != "en")

    lang_title = f" ({LanguageHelper.get_language_name(track.detected_language)})" if track.detected_language else ""
    table = Table(
        title=f"Synced Lyrics Preview: [bold]{track.title}[/bold] - [cyan]{track.artist}[/cyan]{lang_title}",
        border_style="dim",
    )
    table.add_column("Time", style="bold yellow", width=12)
    table.add_column("Foreign / Original Lyric", style="white")
    if has_translation or is_foreign:
        table.add_column("English Translation", style="italic green")

    for line in track.lines[:max_lines]:
        if has_translation or is_foreign:
            table.add_row(line.start_time, line.text, line.translation or "")
        else:
            table.add_row(line.start_time, line.text)

    if len(track.lines) > max_lines:
        table.add_row("...", f"[dim]+ {len(track.lines) - max_lines} more lines[/dim]")

    console.print(table)


def handle_batch(
    scraper: LyricScraper,
    batch_file: str,
    output_dir: str,
    language: Optional[str],
    fmt: str,
    provider: Optional[str],
    translate: bool = True,
):
    if not os.path.isfile(batch_file):
        console.print(f"[bold red]Error:[/bold red] Batch file '{batch_file}' not found.")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    with open(batch_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    console.print(f"[cyan]Processing [bold]{len(lines)}[/bold] songs from batch file...[/cyan]\n")

    success_count = 0
    for idx, item in enumerate(lines, 1):
        # Support "Artist - Title" or "Title"
        if " - " in item:
            parts = item.split(" - ", 1)
            artist, title = parts[0].strip(), parts[1].strip()
        else:
            artist, title = None, item.strip()

        console.print(f"[{idx}/{len(lines)}] Searching: [bold]{title}[/bold] {f'by {artist}' if artist else ''}...")

        track = scraper.get_lyrics(
            title=title,
            artist=artist,
            language=language,
            preferred_provider=provider,
            translate=translate,
        )

        if track and track.lines:
            safe_title = "".join(c for c in f"{track.artist}_{track.title}" if c.isalnum() or c in " ._-").strip()
            out_name = f"{safe_title}.{fmt}"
            out_path = os.path.join(output_dir, out_name)
            scraper.save(track, out_path, format_type=fmt)
            lang_str = f" ({track.detected_language})" if track.detected_language else ""
            trans_str = " [with English translation]" if (track.english_plain_lyrics and track.detected_language != "en") else ""
            console.print(f"  [green][+] Saved {len(track.lines)} synced lines -> {out_path}{lang_str}{trans_str}[/green]")
            success_count += 1
        else:
            console.print(f"  [yellow][-] No synced lyrics found matching criteria.[/yellow]")

    console.print(f"\n[bold green]Batch complete: {success_count}/{len(lines)} files saved to {output_dir}[/bold green]")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape timestamped synchronized lyrics (.json, .lrc, .srt, .vtt) with automatic English translation.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("query", nargs="?", help="Song title or search query")
    parser.add_argument("-a", "--artist", help="Artist name (optional, improves precision)")
    parser.add_argument("-l", "--lang", "--language", help="Target language code (e.g. ru, es, ja, fr, de, ko, zh, it) or name")
    parser.add_argument(
        "-f", "--format",
        choices=["json", "lrc", "srt", "vtt", "txt", "eng_lrc", "bilingual_lrc"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument("-o", "--output", help="Output file path (e.g. song.json, song.lrc)")
    parser.add_argument("-s", "--search", action="store_true", help="Interactive search mode to choose from top results")
    parser.add_argument("-b", "--batch", help="Path to text file with song titles (one per line) for batch download")
    parser.add_argument("-d", "--out-dir", default="./lyrics", help="Output directory for batch downloads (default: ./lyrics)")
    parser.add_argument("-p", "--provider", choices=["lrclib", "netease", "kugou"], help="Force a specific lyric provider")
    parser.add_argument("--no-translate", action="store_true", help="Disable automatic English translation for foreign lyrics")
    parser.add_argument("--translate-to", default="en", help="Target language for translation (default: en)")
    parser.add_argument("--preview", action="store_true", help="Preview parsed synced lines and translations in the terminal")
    parser.add_argument("--list-languages", action="store_true", help="List supported language codes and names")
    parser.add_argument("--audio", "--with-audio", action="store_true", help="Also download matching synchronized audio track (.mp3)")
    parser.add_argument("--audio-dir", default="./audio_output", help="Output directory for downloaded audio (default: ./audio_output)")
    parser.add_argument("--audio-format", default="mp3", choices=["mp3", "m4a", "flac", "wav"], help="Audio format (default: mp3)")

    args = parser.parse_args()

    if args.list_languages:
        list_languages()
        sys.exit(0)

    auto_translate = not args.no_translate
    scraper = LyricScraper(auto_translate=auto_translate, translate_to=args.translate_to)

    # Batch mode
    if args.batch:
        print_banner()
        handle_batch(
            scraper=scraper,
            batch_file=args.batch,
            output_dir=args.out_dir,
            language=args.lang,
            fmt=args.format,
            provider=args.provider,
            translate=auto_translate,
        )
        sys.exit(0)

    if not args.query:
        print_banner()
        parser.print_help()
        sys.exit(1)

    lang_code = LanguageHelper.normalize_code(args.lang)
    lang_display = f" [{LanguageHelper.get_language_name(lang_code)}]" if lang_code else ""

    console.print(f"[cyan]Searching for:[/cyan] [bold]{args.query}[/bold]{f' by [bold]{args.artist}[/bold]' if args.artist else ''}{lang_display}...")

    # Interactive search or direct
    results = scraper.search(
        query=args.query,
        artist=args.artist,
        language=lang_code,
        limit=8,
        provider_names=[args.provider] if args.provider else None,
        translate=auto_translate,
    )

    if not results:
        console.print(f"[bold red]No synchronized lyrics found.[/bold red] Try omitting the artist or checking the language filter.")
        sys.exit(1)

    selected_track: LyricTrack

    if args.search or len(results) > 1 and not args.output:
        table = Table(title="Search Results", border_style="cyan", show_header=True)
        table.add_column("#", style="bold yellow", width=4)
        table.add_column("Title", style="white")
        table.add_column("Artist", style="cyan")
        table.add_column("Duration", style="magenta", width=10)
        table.add_column("Language", style="green", width=14)
        table.add_column("Lines", style="blue", width=8)
        table.add_column("Provider", style="dim", width=10)

        for i, r in enumerate(results, 1):
            dur_str = f"{int(r.duration // 60)}:{int(r.duration % 60):02d}" if r.duration > 0 else "-"
            lang_str = f"{r.detected_language} ({int(r.language_confidence*100)}%)" if r.detected_language else "N/A"
            table.add_row(
                str(i),
                r.title,
                r.artist,
                dur_str,
                lang_str,
                str(len(r.lines)),
                r.provider,
            )

        console.print(table)

        if args.search:
            choice = Prompt.ask("Select a track number to download/view", choices=[str(i) for i in range(1, len(results) + 1)], default="1")
            selected_track = results[int(choice) - 1]
        else:
            selected_track = results[0]
    else:
        selected_track = results[0]

    console.print(
        f"\n[green]Selected:[/green] [bold]{selected_track.title}[/bold] by [cyan]{selected_track.artist}[/cyan] "
        f"([blue]{len(selected_track.lines)} synced lines[/blue], Language: [yellow]{selected_track.detected_language or 'unknown'}[/yellow], Provider: [dim]{selected_track.provider}[/dim])"
    )

    # Preview
    if args.preview or not args.output:
        preview_lyrics(selected_track, max_lines=15)

    # Save or print
    if args.output:
        out_path = scraper.save(selected_track, args.output, format_type=args.format)
        console.print(f"\n[bold green][+] Successfully saved ({args.format.upper()}) -> {os.path.abspath(out_path)}[/bold green]")
    else:
        out_path = None
        console.print(f"\n[dim]Tip: Use -o <filename.{args.format}> to save directly to a file (e.g. -o song.{args.format}).[/dim]")

    if args.audio:
        from song_scraper import SongScraper
        console.print(f"\n[cyan]Downloading matching audio track and generating companion configurations...[/cyan]")
        song_scraper = SongScraper(output_format=args.audio_format, auto_translate=auto_translate)
        synced_text = scraper.format_output(selected_track, "lrc") if selected_track.lines else None
        audio_res = song_scraper.scrape_song(
            title=selected_track.title,
            artist=selected_track.artist,
            album=selected_track.album,
            duration=selected_track.duration,
            plain_lyrics=selected_track.plain_lyrics,
            synced_lrc=synced_text,
            english_lyrics=selected_track.english_plain_lyrics,
            english_synced_lrc=selected_track.english_synced_lyrics,
            detected_language=selected_track.detected_language,
            lines=[l.to_dict() for l in selected_track.lines],
            output_dir=args.audio_dir,
            embed_lyrics=True,
            companion_lrc=True,
            companion_json=True,
        )
        if audio_res.success and audio_res.audio_path:
            console.print(f"[bold green][+] Audio downloaded and synced:[/bold green] {os.path.abspath(audio_res.audio_path)}")
            if audio_res.companion_lrc_path:
                console.print(f"[bold green][+] Companion LRC created:[/bold green] {os.path.abspath(audio_res.companion_lrc_path)}")
            if audio_res.companion_json_path:
                console.print(f"[bold green][+] Companion JSON created:[/bold green] {os.path.abspath(audio_res.companion_json_path)}")
        else:
            console.print(f"[bold red][-] Audio download failed:[/bold red] {audio_res.error}")


if __name__ == "__main__":
    main()
