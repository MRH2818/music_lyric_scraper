#!/usr/bin/env python3
"""
Command-Line Interface for Song Scraper.
Scrapes and downloads audio files matching specific lyric files or metadata,
with automatic foreign-language translation and companion JSON/LRC export.
"""

import argparse
import sys
import os
from typing import List, Optional

# Ensure standard output and standard error use UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from song_scraper import SongScraper, LyricFileParser, SongMetadata, DownloadResult

console = Console(force_terminal=True, legacy_windows=False)


def print_banner():
    banner_text = (
        "[bold cyan]Song Scraper & Audio Synchronizer[/bold cyan]\n"
        "[dim]Download studio audio matching lyric files with foreign/English translation & JSON export[/dim]"
    )
    console.print(Panel(banner_text, border_style="cyan"))


def format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "-"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def display_result_row(table: Table, res: DownloadResult):
    lyric_dur = format_duration(res.expected_duration)
    audio_dur = format_duration(res.duration)

    if res.expected_duration > 0 and res.duration > 0:
        diff = res.duration_diff
        sign = "+" if res.duration >= res.expected_duration else "-"
        diff_str = f"{sign}{diff:.1f}s"
        if diff <= 1.5:
            match_status = "[bold green]Exact Studio[/bold green]"
        elif diff <= 6.0:
            match_status = "[green]Close Match[/green]"
        else:
            match_status = f"[yellow]Diff {diff_str}[/yellow]"
    else:
        diff_str = "-"
        match_status = "[cyan]Downloaded[/cyan]"

    out_file = os.path.basename(res.audio_path) if res.audio_path else "-"
    lang_info = res.metadata.detected_language or "-"
    if res.metadata.english_lyrics and res.metadata.is_foreign:
        lang_info += " [EN✓]"

    table.add_row(
        res.metadata.title,
        res.metadata.artist or "-",
        lang_info,
        lyric_dur,
        audio_dur,
        diff_str,
        match_status if res.success else "[red]Error[/red]",
        out_file,
    )


def handle_batch_directory(
    scraper: SongScraper,
    lyrics_dir: str,
    output_dir: str,
    embed_lyrics: bool,
    companion_lrc: bool,
    companion_json: bool,
    offset_ms: int,
):
    if not os.path.isdir(lyrics_dir):
        console.print(f"[bold red]Error:[/bold red] Lyrics directory '{lyrics_dir}' not found.")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    console.print(f"[cyan]Scanning lyric files in [bold]{lyrics_dir}[/bold]...[/cyan]")

    results = scraper.scrape_batch_from_directory(
        lyrics_dir=lyrics_dir,
        output_dir=output_dir,
        embed_lyrics=embed_lyrics,
        companion_lrc=companion_lrc,
        companion_json=companion_json,
        offset_ms=offset_ms,
    )

    if not results:
        console.print(f"[yellow]No supported lyric files (.json, .lrc, .srt, .vtt, .txt) found in {lyrics_dir}[/yellow]")
        return

    table = Table(title="Batch Audio Download Summary", border_style="cyan", show_header=True)
    table.add_column("Title", style="white")
    table.add_column("Artist", style="cyan")
    table.add_column("Lang", style="yellow", width=10)
    table.add_column("Lyric Dur", style="magenta", width=10)
    table.add_column("Audio Dur", style="blue", width=10)
    table.add_column("Diff", style="yellow", width=8)
    table.add_column("Sync Match", width=14)
    table.add_column("Output File", style="green")

    success_count = 0
    for res in results:
        display_result_row(table, res)
        if res.success:
            success_count += 1

    console.print(table)
    console.print(f"\n[bold green]Complete: {success_count}/{len(results)} songs saved to {output_dir}[/bold green]")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape and download audio tracks matching lyric files with translation safeguards and JSON export.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Path to a lyric file (.json, .lrc, .srt, .vtt, .txt), a directory of lyric files, or a song title",
    )
    parser.add_argument("-a", "--artist", help="Artist name (when providing song title directly)")
    parser.add_argument(
        "--dir", "--lyrics-dir",
        dest="lyrics_dir",
        help="Path to directory containing lyric files to batch scrape",
    )
    parser.add_argument(
        "-d", "--out-dir",
        default="./audio_output",
        help="Output directory for downloaded audio (default: ./audio_output)",
    )
    parser.add_argument("-o", "--output", help="Specific output audio file path (e.g. song.mp3)")
    parser.add_argument(
        "-f", "--format",
        choices=["mp3", "m4a", "flac", "wav", "ogg"],
        default="mp3",
        help="Audio format (default: mp3)",
    )
    parser.add_argument(
        "-b", "--bitrate",
        choices=["128k", "192k", "256k", "320k"],
        default="192k",
        help="Audio bitrate (default: 192k)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=6.0,
        help="Max duration difference tolerance in seconds (default: 6.0)",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Offset in milliseconds to adjust companion lyric timestamps (e.g. +500 or -300)",
    )
    parser.add_argument(
        "--no-embed-lyrics",
        action="store_true",
        help="Do not embed lyrics into audio ID3 tags",
    )
    parser.add_argument(
        "--no-companion-lrc",
        action="store_true",
        help="Do not generate companion .lrc file alongside audio",
    )
    parser.add_argument(
        "--no-companion-json",
        action="store_true",
        help="Do not generate companion .json configuration file alongside audio",
    )
    parser.add_argument(
        "--no-translate",
        action="store_true",
        help="Disable automatic translation of foreign lyrics to English",
    )

    args = parser.parse_args()

    print_banner()

    auto_translate = not args.no_translate
    scraper = SongScraper(
        output_format=args.format,
        bitrate=args.bitrate,
        tolerance_seconds=args.tolerance,
        auto_translate=auto_translate,
    )

    embed_lyrics = not args.no_embed_lyrics
    companion_lrc = not args.no_companion_lrc
    companion_json = not args.no_companion_json

    # Batch directory mode via --dir
    if args.lyrics_dir:
        handle_batch_directory(
            scraper=scraper,
            lyrics_dir=args.lyrics_dir,
            output_dir=args.out_dir,
            embed_lyrics=embed_lyrics,
            companion_lrc=companion_lrc,
            companion_json=companion_json,
            offset_ms=args.offset,
        )
        return

    if not args.target:
        parser.print_help()
        sys.exit(1)

    target_path = args.target

    # If target is a directory
    if os.path.isdir(target_path):
        handle_batch_directory(
            scraper=scraper,
            lyrics_dir=target_path,
            output_dir=args.out_dir,
            embed_lyrics=embed_lyrics,
            companion_lrc=companion_lrc,
            companion_json=companion_json,
            offset_ms=args.offset,
        )
        return

    # If target is a file
    if os.path.isfile(target_path):
        console.print(f"[cyan]Parsing lyric file:[/cyan] [bold]{target_path}[/bold]")
        try:
            meta = LyricFileParser.parse_file(target_path)
            lang_str = f" [Language: {meta.detected_language}]" if meta.detected_language else ""
            console.print(
                f"  Found metadata: [bold]{meta.title}[/bold] by [cyan]{meta.artist or 'Unknown'}[/cyan]{lang_str} "
                f"(Expected duration: [magenta]{format_duration(meta.duration)}[/magenta])"
            )
        except Exception as e:
            console.print(f"[bold red]Failed to parse lyric file:[/bold red] {e}")
            sys.exit(1)

        console.print(f"[cyan]Searching and downloading matching audio track...[/cyan]")
        res = scraper.scrape_from_lyric_file(
            lyric_path=target_path,
            output_dir=args.out_dir,
            output_path=args.output,
            embed_lyrics=embed_lyrics,
            companion_lrc=companion_lrc,
            companion_json=companion_json,
            offset_ms=args.offset,
        )
    else:
        # Target is a song title query
        console.print(f"[cyan]Searching audio for query:[/cyan] [bold]{target_path}[/bold]{f' by [cyan]{args.artist}[/cyan]' if args.artist else ''}")
        res = scraper.scrape_song(
            title=target_path,
            artist=args.artist,
            output_dir=args.out_dir,
            output_path=args.output,
            embed_lyrics=embed_lyrics,
            companion_lrc=companion_lrc,
            companion_json=companion_json,
            offset_ms=args.offset,
        )

    if res.success and res.audio_path:
        table = Table(title="Download Result", border_style="cyan", show_header=True)
        table.add_column("Title", style="white")
        table.add_column("Artist", style="cyan")
        table.add_column("Lang", style="yellow", width=10)
        table.add_column("Lyric Dur", style="magenta", width=10)
        table.add_column("Audio Dur", style="blue", width=10)
        table.add_column("Diff", style="yellow", width=8)
        table.add_column("Sync Match", width=14)
        table.add_column("Output File", style="green")

        display_result_row(table, res)
        console.print(table)

        console.print(f"\n[bold green][+] Audio saved successfully:[/bold green] {os.path.abspath(res.audio_path)}")
        if res.companion_lrc_path:
            console.print(f"[bold green][+] Companion synced LRC:[/bold green] {os.path.abspath(res.companion_lrc_path)}")
        if res.companion_json_path:
            console.print(f"[bold green][+] Companion JSON configuration:[/bold green] {os.path.abspath(res.companion_json_path)}")
    else:
        console.print(f"\n[bold red][-] Failed to download audio:[/bold red] {res.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
