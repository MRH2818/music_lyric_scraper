"""
Audio Downloader & Candidate Search Engine.
Downloads audio tracks matching specific lyric metadata, with duration-matching
safeguards against music video intros/outros.
"""

import os
import re
import shutil
import requests
from typing import Optional, List, Tuple, Dict, Any

from .models import SongMetadata, AudioCandidate, DownloadResult

# Negative keywords for audio/lyric sync (indicative of intros/dialogue/alterations)
MV_NEGATIVE_KEYWORDS = [
    "music video",
    "official video",
    "official mv",
    " m/v",
    "m/v ",
    "short film",
    "live at",
    "live in",
    "live performance",
    "concert",
    "acoustic version",
    "unplugged",
    "cover by",
    "reaction",
    "dance practice",
    "dialogue",
    "soundtrack scene",
]

# Positive keywords indicating studio/album cuts
STUDIO_POSITIVE_KEYWORDS = [
    "official audio",
    "audio",
    "provided to youtube",
    "original audio",
    "album version",
    "topic",
    "studio version",
]


class AudioDownloader:
    """
    Scrapes and downloads audio files with duration-matching and studio-track priority.
    """

    def __init__(
        self,
        output_format: str = "mp3",
        bitrate: str = "192k",
        tolerance_seconds: float = 6.0,
        temp_dir: Optional[str] = None,
    ):
        self.output_format = output_format.lower().lstrip(".")
        self.bitrate = bitrate
        self.tolerance_seconds = tolerance_seconds
        self.temp_dir = temp_dir or os.path.join(os.path.expanduser("~"), ".cache", "song_scraper")
        os.makedirs(self.temp_dir, exist_ok=True)

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitizes string for cross-platform safe filesystem naming."""
        clean = re.sub(r'[\\/*?:"<>|]', "", name)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean or "audio"

    def try_direct_provider_stream(self, meta: SongMetadata, output_path: str) -> Optional[DownloadResult]:
        """
        Attempts direct audio stream download from provider (e.g. NetEase) if source_id is present.
        """
        if meta.provider == "netease" and meta.source_id:
            direct_url = f"https://music.163.com/song/media/outer/url?id={meta.source_id}.mp3"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://music.163.com/",
            }
            try:
                resp = requests.get(direct_url, headers=headers, stream=True, timeout=10)
                if resp.status_code == 200:
                    content_type = resp.headers.get("Content-Type", "")
                    # NetEase returns audio/mpeg or length > 500KB if track is accessible
                    content_length = int(resp.headers.get("Content-Length", 0))
                    if "audio" in content_type or content_length > 500000:
                        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                        with open(output_path, "wb") as f:
                            for chunk in resp.iter_content(chunk_size=65536):
                                if chunk:
                                    f.write(chunk)
                        
                        return DownloadResult(
                            success=True,
                            metadata=meta,
                            audio_path=output_path,
                            duration=meta.duration,
                            expected_duration=meta.duration,
                            duration_diff=0.0,
                            source_url=direct_url,
                            source_title=f"{meta.artist} - {meta.title} (NetEase Studio Master)",
                        )
            except Exception:
                pass
        return None

    def search_candidates(self, meta: SongMetadata, max_results: int = 5) -> List[AudioCandidate]:
        """
        Searches YouTube / YouTube Music for audio track candidates and scores them.
        """
        import yt_dlp

        query_terms = [
            f"{meta.artist} - {meta.title} audio".strip(),
            f"{meta.artist} - {meta.title}".strip(),
            meta.title.strip(),
        ]

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
        }

        candidates: List[AudioCandidate] = []
        seen_ids = set()

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for term in query_terms:
                if len(candidates) >= max_results:
                    break
                try:
                    search_query = f"ytsearch{max_results}:{term}"
                    info = ydl.extract_info(search_query, download=False)
                    entries = info.get("entries", []) if info else []

                    for entry in entries:
                        if not entry:
                            continue
                        video_id = entry.get("id")
                        if not video_id or video_id in seen_ids:
                            continue
                        seen_ids.add(video_id)

                        title = entry.get("title", "")
                        uploader = entry.get("uploader", "") or entry.get("channel", "")
                        duration = float(entry.get("duration") or 0.0)
                        url = entry.get("url") or f"https://www.youtube.com/watch?v={video_id}"

                        diff = abs(duration - meta.duration) if meta.duration > 0 else 0.0

                        # Determine if official audio
                        lower_title = title.lower()
                        lower_uploader = uploader.lower()
                        is_official = any(k in lower_title or k in lower_uploader for k in STUDIO_POSITIVE_KEYWORDS)

                        # Calculate score (higher is better)
                        score = 100.0

                        # Duration penalty
                        if meta.duration > 0:
                            if diff <= 1.5:
                                score += 40.0  # Exact match bonus
                            elif diff <= self.tolerance_seconds:
                                score += 20.0 - (diff * 2.0)
                            else:
                                score -= (diff - self.tolerance_seconds) * 10.0

                        # Keyword scoring
                        if is_official:
                            score += 25.0
                        if "topic" in lower_uploader or "- topic" in lower_uploader:
                            score += 35.0  # High confidence studio topic track

                        # Negative scoring for MV intro risk
                        has_mv_keyword = any(k in lower_title for k in MV_NEGATIVE_KEYWORDS)
                        if has_mv_keyword:
                            # Only penalize MV if title doesn't specifically have official audio
                            if not is_official or diff > 2.0:
                                score -= 45.0

                        candidates.append(
                            AudioCandidate(
                                title=title,
                                uploader=uploader,
                                duration=duration,
                                url=url,
                                duration_diff=diff,
                                is_official_audio=is_official,
                                score=score,
                                source="youtube",
                            )
                        )
                except Exception:
                    continue

        # Sort by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    def download_candidate(
        self,
        candidate: AudioCandidate,
        meta: SongMetadata,
        output_path: str,
    ) -> DownloadResult:
        """
        Downloads a specific audio candidate and transcodes to the desired format.
        """
        import yt_dlp

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        base_no_ext, _ = os.path.splitext(output_path)
        temp_out_template = f"{base_no_ext}.%(ext)s"

        ydl_opts: Dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": temp_out_template,
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": self.output_format,
                    "preferredquality": self.bitrate.replace("k", ""),
                }
            ],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([candidate.url])

            final_path = f"{base_no_ext}.{self.output_format}"
            if os.path.isfile(final_path):
                # Clean up any residual source containers (e.g. .webm, .opus)
                for ext in (".webm", ".opus", ".m4a", ".ogg", ".aac", ".part", ".ytdl"):
                    temp_residual = f"{base_no_ext}{ext}"
                    if temp_residual != final_path and os.path.isfile(temp_residual):
                        try:
                            os.remove(temp_residual)
                        except OSError:
                            pass

                return DownloadResult(
                    success=True,
                    metadata=meta,
                    audio_path=final_path,
                    duration=candidate.duration,
                    expected_duration=meta.duration,
                    duration_diff=candidate.duration_diff,
                    source_url=candidate.url,
                    source_title=candidate.title,
                )
            else:
                return DownloadResult(
                    success=False,
                    metadata=meta,
                    error=f"Downloaded file not found at expected path {final_path}",
                )
        except Exception as e:
            return DownloadResult(
                success=False,
                metadata=meta,
                error=str(e),
            )

    def download_for_metadata(
        self,
        meta: SongMetadata,
        output_path: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> DownloadResult:
        """
        Full workflow: Checks direct stream -> searches & scores candidates -> downloads best available match.
        """
        # Determine output file path
        if not output_path:
            dir_path = output_dir or "./audio_output"
            filename_part = f"{meta.artist} - {meta.title}" if meta.artist else meta.title
            safe_name = self._sanitize_filename(filename_part)
            output_path = os.path.join(dir_path, f"{safe_name}.{self.output_format}")

        # 1. Try direct provider stream first if available
        direct_res = self.try_direct_provider_stream(meta, output_path)
        if direct_res and direct_res.success:
            return direct_res

        # 2. Search candidates on YouTube / YouTube Music
        candidates = self.search_candidates(meta)
        if not candidates:
            return DownloadResult(
                success=False,
                metadata=meta,
                error=f"No audio candidates found for query '{meta.query_string}'",
            )

        # 3. Iterate through candidates until one downloads successfully
        last_error = None
        for candidate in candidates:
            result = self.download_candidate(candidate, meta, output_path)
            if result.success:
                return result
            last_error = result.error

        return DownloadResult(
            success=False,
            metadata=meta,
            error=last_error or "All candidate downloads failed",
        )
