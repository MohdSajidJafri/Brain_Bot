"""
Generate voiceover audio using Edge TTS (free, no API key needed).
Synthesizes the brainrot narration script into an audio file.
Returns duration and sentence-level timings for captions.
All async/subprocess calls have timeouts to prevent indefinite hangs.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

import config

# Timeouts
TTS_TIMEOUT = 120  # 2 minutes for TTS synthesis
FFPROBE_TIMEOUT = 30  # 30 seconds for ffprobe


class SentenceTiming(TypedDict):
    text: str
    offset_ms: int
    duration_ms: int


def _ffprobe_duration(path: Path) -> float:
    """Get audio duration in seconds."""
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
        timeout=FFPROBE_TIMEOUT,
    ).strip()
    return float(out)


async def _synthesize_with_timing(
    text: str,
    out_path: Path,
    voice: str,
    rate: str = "-10%",
) -> list[SentenceTiming]:
    """Synthesize speech with sentence-level timestamps."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    sentences: list[SentenceTiming] = []

    with open(out_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                sentences.append(
                    SentenceTiming(
                        text=chunk["text"],
                        offset_ms=int(chunk["offset"]) // 10_000,
                        duration_ms=int(chunk["duration"]) // 10_000,
                    )
                )

    return sentences


def synthesize_brainrot_voiceover(
    narration: str,
    output_path: Path | None = None,
    voice: str | None = None,
    rate: str | None = None,
) -> tuple[float, list[SentenceTiming]]:
    """
    Synthesize brainrot narration to audio using Edge TTS.
    
    Args:
        narration: The brainrot script text to speak.
        output_path: Where to save the MP3. Default: data/output/voiceover.mp3.
        voice: Edge TTS voice name. Default: from config.
    
    Returns:
        Tuple of (total_duration_seconds, sentence_timings)
    """
    if output_path is None:
        output_path = config.OUTPUT_DIR / "voiceover.mp3"
    voice = voice or config.TTS_VOICE

    rate = rate or config.TTS_RATE
    # Normalize casing to prevent Edge TTS from spelling out ALL CAPS emphasis words
    words = narration.split()
    normalized_words = []
    for w in words:
        clean_w = w.strip(".,!?;:\"'-")
        if clean_w.upper() in ["GTA", "NPC", "POV", "CI", "IG", "YT"]:
            normalized_words.append(w.upper())  # Keep acronyms capitalized
        elif clean_w.isupper() and len(clean_w) > 1:
            # It's an emphasis word (ALL CAPS) - lowercase it to make it sound natural
            normalized_words.append(w.lower())
        else:
            normalized_words.append(w)
    tts_text = " ".join(normalized_words)

    print(f"🔊 Edge TTS: synthesizing voiceover ({voice} at {rate} speed)…")
    try:
        sentences = asyncio.run(
            asyncio.wait_for(
                _synthesize_with_timing(tts_text, output_path, voice, rate),
                timeout=TTS_TIMEOUT,
            )
        )
    except asyncio.TimeoutError:
        print(f"   ⚠ TTS synthesis timed out after {TTS_TIMEOUT}s")
        # Check if partial audio was written
        if output_path.exists() and output_path.stat().st_size > 1000:
            print("   ⚠ Partial audio found, using it anyway")
            sentences = []
        else:
            print("   ❌ No audio generated — cannot proceed")
            sys.exit(1)

    total_dur = _ffprobe_duration(output_path)
    print(f"   Audio: {total_dur:.1f}s ({len(sentences)} sentences)")
    print(f"   Saved: {output_path}")

    return total_dur, sentences


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="WHEN THE NPC CATCHES YOU SLIDING IN GTA VI 💀💀", help="Narration text")
    args = ap.parse_args()

    dur, timings = synthesize_brainrot_voiceover(args.text)
    print(f"\n✅ Voiceover generated: {dur:.1f}s")
    for t in timings:
        print(f"   [{t['offset_ms'] / 1000:.1f}s] {t['text']}")