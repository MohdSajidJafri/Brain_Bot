"""
Download GTA VI gameplay clips from YouTube using yt-dlp.
Tracks already-downloaded videos to avoid duplicates.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 console output on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import config






def download_fresh_clips(query: str | None = None, max_downloads: int | None = None) -> list[Path]:
    """
    Search YouTube for GTA gameplay, download new videos.
    Works best on local machine (GitHub runners may get bot-blocked).
    Falls back gracefully if download fails.
    Returns list of downloaded file paths (empty if none found).
    """
    search_query = query or config.YTDL_SEARCH_QUERY
    count = max_downloads if max_downloads is not None else config.YTDL_MAX_DOWNLOADS
    output_tpl = str(config.RAW_DIR / "%(id)s.%(ext)s")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--extractor-args", "youtube:player_client=android,web",
        "--format", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "--output", output_tpl,
        "--max-downloads", str(count),
        "--download-archive", str(config.CACHE_DIR / "archive.txt"),
        "--no-playlist",
        "--quiet",
        "--print", "after_move:filepath",
        "--extractor-retries", "2",
        "--retries", "3",
        f"ytsearch{count}:{search_query}",
    ]


    print(f"🔍 Searching: {search_query}")
    print(f"   Max downloads: {count}")

    timeout_seconds = max(180, count * 60)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        print(f"⚠ Download timed out after {timeout_seconds}s — YouTube may be throttling")
        return []

    if result.returncode != 0:
        print(f"⚠ Download failed: YouTube may be blocking this environment")
        if "Sign in" in result.stderr:
            print("   → YouTube requires sign-in (common on GitHub runners / datacenter IPs)")
            print("   → Run 'python download_clips.py' locally on your PC instead")
        else:
            print(f"   Error: {result.stderr[:200]}")
        return []

    downloaded = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if line:
            p = Path(line)
            if p.exists():
                downloaded.append(p)
                print(f"   ✅ Downloaded: {p.name}")

    print(f"   Total: {len(downloaded)} new video(s)")
    return downloaded


def list_existing_raw() -> list[Path]:
    """List all previously downloaded raw videos."""
    return sorted(config.RAW_DIR.glob("*.*"))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Download GTA gameplay clips via yt-dlp")
    ap.add_argument("--query", "-q", default=None, help="Search query on YouTube")
    ap.add_argument("--count", "-n", type=int, default=None, help="Max videos to download")
    args = ap.parse_args()

    files = download_fresh_clips(query=args.query, max_downloads=args.count)
    if not files:
        print("No new clips downloaded. Existing raw files:")
        for f in list_existing_raw():
            print(f"  {f.name}")
    sys.exit(0)