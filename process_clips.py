"""
Split raw gameplay videos into short clips using FFmpeg scene detection.
Outputs clips in the 15-40 second range suitable for Shorts/Reels.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
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


# All subprocess calls get a timeout to prevent indefinite hangs
SUBPROCESS_TIMEOUT = 300  # 5 minutes per ffmpeg operation


def _get_video_duration(path: Path) -> float:
    """Get duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
    return float(result.stdout.strip())


def _detect_scenes(path: Path, threshold: float = 0.3) -> list[float]:
    """
    Use FFmpeg scene detection to find scene change timestamps.
    Returns list of timestamps in seconds where scenes change.
    """
    cmd = [
        "ffmpeg", "-an", "-i", str(path),
        "-filter:v", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)

    timestamps = []
    for line in result.stderr.splitlines():
        if "pts_time:" in line:
            try:
                # Extract pts_time value
                parts = line.split()
                for p in parts:
                    if p.startswith("pts_time:"):
                        ts = float(p.split(":")[1])
                        timestamps.append(ts)
            except (ValueError, IndexError):
                continue

    return sorted(set(timestamps))


def _split_into_clips(
    video_path: Path,
    scene_times: list[float],
    duration: float,
) -> list[Path]:
    """
    Split video at scene boundaries, keeping clips within min-max duration.
    Returns list of output clip paths.
    """
    clips = []
    boundaries = [0.0] + scene_times + [duration]

    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        clip_dur = end - start

        # Skip clips that are too short or too long
        if clip_dur < config.CLIP_MIN_DURATION:
            continue
        if clip_dur > config.CLIP_MAX_DURATION:
            # Clip is too long — just take the first N seconds
            end = start + config.CLIP_MAX_DURATION

        out_path = config.CLIPS_DIR / f"{video_path.stem}_clip_{i:03d}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(video_path),
            "-t", str(end - start),
            "-c", "copy",
            str(out_path),
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
        except subprocess.TimeoutExpired:
            print(f"   ⚠ Clip {i:03d} timed out, skipping")
            continue

        if out_path.exists() and out_path.stat().st_size > 100_000:
            clips.append(out_path)
            print(f"   🎬 Clip {i:03d}: {start:.1f}s → {end:.1f}s ({clip_dur:.1f}s)")

    return clips


def _cleanup_raw_videos(keep_processed: bool = True) -> None:
    """Delete raw videos after processing to save space."""
    import shutil
    raw_videos = sorted(config.RAW_DIR.glob("*.*"))
    if raw_videos:
        print(f"   🧹 Cleaning up {len(raw_videos)} raw video(s)…")
        for v in raw_videos:
            v.unlink(missing_ok=True)


def _keep_best_clips(max_clips: int | None = None) -> None:
    """Only keep the best (largest file-size) clips, delete the rest."""
    limit = max_clips if max_clips is not None else getattr(config, "MAX_CLIPS", 100)
    clips = sorted(config.CLIPS_DIR.glob("*.mp4"), key=lambda p: p.stat().st_size, reverse=True)
    if len(clips) > limit:
        to_delete = clips[limit:]
        print(f"   🧹 Keeping top {limit} clips, deleting {len(to_delete)}…")
        for c in to_delete:
            c.unlink(missing_ok=True)


def process_all_raw() -> list[Path]:
    """
    Process all raw videos in RAW_DIR into short clips.
    Returns list of clip paths.
    Cleans up raw videos and keeps only the best clips.
    """
    raw_videos = sorted(config.RAW_DIR.glob("*.*"))
    if not raw_videos:
        print("📂 No raw videos found in data/raw/")
        return []

    all_clips: list[Path] = []
    for video in raw_videos:
        print(f"\n🎞 Processing: {video.name}")
        try:
            dur = _get_video_duration(video)
        except (subprocess.TimeoutExpired, ValueError) as e:
            print(f"   ⚠ Could not get duration for {video.name}: {e}")
            continue
        print(f"   Duration: {dur:.1f}s")

        print(f"   🔍 Detecting scenes (threshold={config.SCENE_THRESHOLD})…")
        try:
            scenes = _detect_scenes(video, config.SCENE_THRESHOLD)
        except subprocess.TimeoutExpired:
            print(f"   ⚠ Scene detection timed out for {video.name}, skipping")
            continue
        print(f"   Found {len(scenes)} scene changes")

        clips = _split_into_clips(video, scenes, dur)
        all_clips.extend(clips)
        print(f"   → {len(clips)} usable clips")

    # Cleanup: remove raw files, keep best clips
    _cleanup_raw_videos()
    _keep_best_clips(max_clips=getattr(config, "MAX_CLIPS", 100))

    # Re-count remaining clips
    remaining = sorted(config.CLIPS_DIR.glob("*.mp4"))
    print(f"\n✅ {len(remaining)} clips available (raw files cleaned up)")
    return remaining



def get_random_clip() -> Path | None:
    """
    Pick a clip from the clips directory using round-robin rotation.
    Avoids reusing the same clip repeatedly by tracking used history in data/cache/used_clips.json.
    """
    import json
    import random

    clips = sorted(config.CLIPS_DIR.glob("*.mp4"))
    if not clips:
        return None

    history_file = config.CACHE_DIR / "used_clips.json"
    used_names: list[str] = []
    if history_file.exists():
        try:
            used_names = json.loads(history_file.read_text(encoding="utf-8"))
        except Exception:
            used_names = []

    # Find unused clips
    unused = [c for c in clips if c.name not in used_names]

    if not unused:
        # If all clips have been used, reset history and pick from all
        unused = clips
        used_names = []

    selected = random.choice(unused)

    # Update history (keep last N - 1 clips)
    used_names.append(selected.name)
    max_history = max(1, len(clips) - 2)
    if len(used_names) > max_history:
        used_names = used_names[-max_history:]

    try:
        history_file.write_text(json.dumps(used_names, indent=2), encoding="utf-8")
    except Exception:
        pass

    return selected



if __name__ == "__main__":
    clips = process_all_raw()
    if not clips:
        print("No clips generated. Download raw videos first.")
    sys.exit(0)