"""
Download GTA VI gameplay clips from YouTube using yt-dlp.
Tracks already-downloaded videos to avoid duplicates.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import config


def _load_history() -> set[str]:
    """Load set of already-downloaded video IDs."""
    if config.HISTORY_FILE.exists():
        return set(json.loads(config.HISTORY_FILE.read_text()))
    return set()


def _save_history(ids: set[str]) -> None:
    config.HISTORY_FILE.write_text(json.dumps(sorted(ids), indent=2))


def download_fresh_clips() -> list[Path]:
    """
    Search YouTube for GTA VI gameplay, download new videos.
    Returns list of downloaded file paths.
    """
    history = _load_history()
    print(f"📺 History: {len(history)} videos already downloaded")

    # Build yt-dlp command
    output_tpl = str(config.RAW_DIR / "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--format", config.YTDL_FORMAT,
        "--output", output_tpl,
        "--max-downloads", str(config.YTDL_MAX_DOWNLOADS),
        "--download-archive", str(config.CACHE_DIR / "archive.txt"),
        "--no-playlist",
        "--quiet",
        "--print", "after_move:filepath",
        f"ytsearch{config.YTDL_MAX_DOWNLOADS}:{config.YTDL_SEARCH_QUERY}",
    ]

    print(f"🔍 Searching: {config.YTDL_SEARCH_QUERY}")
    print(f"   Max downloads: {config.YTDL_MAX_DOWNLOADS}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠ yt-dlp stderr: {result.stderr.strip()}")
        if not result.stdout.strip():
            print("   No new clips downloaded.")
            return []

    downloaded = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if line:
            p = Path(line)
            if p.exists():
                downloaded.append(p)
                vid = p.stem
                history.add(vid)
                print(f"   ✅ Downloaded: {p.name}")

    _save_history(history)
    print(f"   Total: {len(downloaded)} new video(s)")
    return downloaded


def list_existing_raw() -> list[Path]:
    """List all previously downloaded raw videos."""
    return sorted(config.RAW_DIR.glob("*.*"))


if __name__ == "__main__":
    files = download_fresh_clips()
    if not files:
        print("No new clips. Existing raw files:")
        for f in list_existing_raw():
            print(f"  {f.name}")
    sys.exit(0)