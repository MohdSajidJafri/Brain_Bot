"""
Generate brainrot scripts for GTA V clips using Groq LLM (free tier).
Target: 40-65 words, hook-first, with emphasis keywords for kinetic captions.
No emojis — clean text only for TTS compatibility.
"""
from __future__ import annotations

import os
import random
import re
import sys
import time
from pathlib import Path

# Ensure UTF-8 console output on Windows to prevent UnicodeEncodeError with emojis
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

from groq import Groq, RateLimitError, APIStatusError


import config

# Forbidden/bannable words to ensure absolute content safety and brand protection
FORBIDDEN_WORDS = [
    "RAPE", "RAPED", "RAPING", "RAPIST", "NIGGER", "FAGGOT", "RETARD", "RETARDED",
    "SUICIDE", "KILL MYSELF", "KILL YOURSELF", "SLUT", "WHORE", "CUNT",
    "PORN", "PEDO", "PEDOPHILE", "TERRORIST", "BOMBING", "MASSACRE"
]

USER_SYSTEM_PROMPT = (
    "You write viral, unhinged brainrot short-form video scripts. "
    "Rules:\n"
    "1. Total length must be 40-65 words across HOOK, BODY, and PUNCHLINE.\n"
    "2. ZERO EMOJIS in HOOK, BODY, PUNCHLINE, or EMPHASIS. Emojis are only allowed in TITLE.\n"
    "3. Definitive, complete ending with a punchline (NO looping or trailing sentences).\n"
    "4. Include 2-3 ALL CAPS words for emphasis.\n"
    "5. Keep content strictly safe-for-work, secular, and advertiser friendly.\n"
    "6. Output EXACT format:\n"
    "HOOK: <5-10 words>\n"
    "BODY: <25-45 words, 3-5 punchy lines>\n"
    "PUNCHLINE: <5-10 words, decisive ending>\n"
    "EMPHASIS: <word1, word2>\n"
    "TITLE: <viral title under 55 chars with 1-2 shock emojis>"
)

SCROLL_HOOKS = [
    "Nobody talks about this...",
    "I just realized something...",
    "This might be the dumbest thing I've ever noticed...",
    "Hear me out...",
    "I refuse to believe I'm the only one...",
    "Imagine if...",
    "This is either genius or completely stupid.",
    "I have a theory.",
    "How it feels to...",
]

FORMAT_CATEGORIES = [
    "FAKE LIFE ADVICE (profound advice that slowly becomes unhinged)",
    "CONSPIRACY BRAINROT (start believable, then completely ruin it)",
    "NPC THOUGHTS (weird cashiers or server secrets)",
    "RANDOM FACTS 90% FAKE (confident fake statements that start comment arguments)",
    "POV VIDEOS (relatable gamer or social situations)",
    "TIER LISTS (rating completely random everyday items)",
    "IMAGINE EXPLAINING THIS (explaining modern situations to historical figures)",
    "THINGS EVERYONE DOES BUT NEVER ADMITS (universal quirks/loops)",
    "FAKE MOTIVATIONAL SPEAKER (clueless millionaire coach advice)",
    "HOW IT FEELS (gamer or social emotions)",
    "RANKING PAIN LEVELS (everyday mental or physical pain)",
    "INTERNET LORE (fake history memes)"
]


# Diverse fallback narration pool to guarantee variety even during network/API failures
FALLBACK_SCRIPTS = [
    (
        "EVER wonder what happens when you mess with physics? "
        "Bro I was just walking NORMAL and a flying tractor SPAWNS on my forehead. "
        "The simulation is officially broken and nobody can fix it.",
        "When Physics Completely Break 💀",
        ["EVER", "NORMAL", "SPAWNS"]
    ),
    (
        "Nobody talks about this refrigerator conspiracy. "
        "Every time you open the fridge door at 3 AM looking for CHEESE, "
        "the leftover pizza is actively plotting its REVENGE. "
        "Close the door and walk away slowly.",
        "The Midnight Fridge Conspiracy 🤯",
        ["CHEESE", "REVENGE"]
    ),
    (
        "I just realized something about elevator buttons. "
        "Pressing the button SEVENTEEN times does not make it arrive FASTER. "
        "It just lets the elevator know you are PANICKING with zero patience.",
        "The Elevator Secret Nobody Admits 💀",
        ["SEVENTEEN", "FASTER", "PANICKING"]
    ),
    (
        "This might be the dumbest thing I have ever noticed. "
        "Your phone BATTERY drops from twenty percent to one percent in four seconds, "
        "but stays on ONE percent for three whole business days. Science cannot explain this.",
        "Why Your Phone Battery Lies To You 🔋",
        ["BATTERY", "ONE"]
    ),
    (
        "Hear me out about microwave timers. "
        "Opening the door with exactly ONE second remaining makes you feel like an elite SECRET agent "
        "defusing a bomb in an intense action movie.",
        "How It Feels To Defuse The Microwave ⏱️",
        ["ONE", "SECRET"]
    ),
    (
        "I refuse to believe I am the only one who does this. "
        "You lower the CAR radio volume just to see the street signs CLEARER. "
        "Your eyes apparently require total SILENCE to read letters.",
        "Why Turning Down Music Helps You See 👀",
        ["CAR", "CLEARER", "SILENCE"]
    ),
    (
        "I have a theory about ceiling fans. "
        "If you stare at a spinning fan long enough, it starts transmitting SECRET messages directly into your brain. "
        "Do not make eye contact with it.",
        "The Ceiling Fan Secret Code 🤯",
        ["SECRET"]
    ),
    (
        "How it feels to finally find that missing song. "
        "Searching random nonsense lyrics on GOOGLE for three months until you find the exact MASTERPIECE "
        "is pure unmatched bliss.",
        "Finding That ONE Song You Forgot 🎵",
        ["GOOGLE", "MASTERPIECE"]
    ),
]


def _strip_emojis(text: str) -> str:
    """Remove all emoji and pictorial/symbol characters from text to protect TTS audio."""
    import unicodedata
    result = []
    for char in text:
        cat = unicodedata.category(char)
        # Keep standard letters, numbers, punctuation, spaces
        if cat.startswith(('L', 'N', 'P', 'Z')) or char in ' \t\n':
            cp = ord(char)
            # Filter out dingbats, emojis, variation selectors, zero-width joiners
            if (0x1F000 <= cp <= 0x1FAFF) or (0x2600 <= cp <= 0x27BF) or (0xFE00 <= cp <= 0xFE0F) or cp == 0x200D:
                continue
            result.append(char)
    cleaned = ''.join(result)
    return re.sub(r'\s+', ' ', cleaned).strip()



def _clean_markdown(text: str) -> str:
    """Remove markdown bold, italic, code markers."""
    return text.replace("**", "").replace("__", "").replace("*", "").replace("`", "").strip()


def _parse_structured_response(response: str) -> dict:
    """Parse the structured LLM response into components.
    Handles strict HOOK|BODY|PUNCHLINE format, markdown formatting, and free-form text.
    """
    result = {
        "hook": "",
        "body": "",
        "punchline": "",
        "emphasis": [],
        "full_narration": "",
        "title": "GTA V BRAINROT",
    }

    lines = response.splitlines()
    current_section = None
    sections: dict[str, str] = {}
    found_any_label = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Strip leading markdown symbols, numbering, headers
        clean_line = re.sub(r'^[#*\-\d\.\s\[\]\(\)]+', '', line).strip()
        clean_line = re.sub(r'^\*\*([A-Za-z]+)\*\*\s*:\s*', r'\1: ', clean_line)
        clean_line = re.sub(r'^\*([A-Za-z]+)\*\s*:\s*', r'\1: ', clean_line)

        upper = clean_line.upper()

        if upper.startswith("HOOK:"):
            found_any_label = True
            current_section = "hook"
            content = clean_line.split(":", 1)[1].strip()
            sections["hook"] = _clean_markdown(content)
        elif upper.startswith("BODY:"):
            found_any_label = True
            current_section = "body"
            content = clean_line.split(":", 1)[1].strip()
            sections["body"] = _clean_markdown(content)
        elif upper.startswith("PUNCHLINE:"):
            found_any_label = True
            current_section = "punchline"
            content = clean_line.split(":", 1)[1].strip()
            sections["punchline"] = _clean_markdown(content)
        elif upper.startswith("EMPHASIS:"):
            found_any_label = True
            current_section = "emphasis"
            raw = clean_line.split(":", 1)[1].strip()
            raw = _clean_markdown(raw)
            result["emphasis"] = [w.strip().strip(".,!?;:\"'").upper() for w in raw.split(",") if w.strip()]
        elif upper.startswith("NARRATION:"):
            found_any_label = True
            current_section = "narration"
            result["full_narration"] = _clean_markdown(clean_line.split(":", 1)[1].strip())
        elif upper.startswith("TITLE:"):
            found_any_label = True
            current_section = "title"
            title_text = _clean_markdown(clean_line.split(":", 1)[1].strip())
            result["title"] = title_text[:60]
        elif current_section and current_section in ["hook", "body", "punchline"]:
            content_line = _clean_markdown(line)
            if content_line:
                if sections.get(current_section):
                    sections[current_section] = sections[current_section] + " " + content_line
                else:
                    sections[current_section] = content_line

    # Build structured result from sections
    if sections.get("hook") or sections.get("body") or sections.get("punchline"):
        result["hook"] = sections.get("hook", "")
        result["body"] = sections.get("body", "")
        result["punchline"] = sections.get("punchline", "")
        parts = [p for p in [result["hook"], result["body"], result["punchline"]] if p]
        result["full_narration"] = " ".join(parts)
    elif result["full_narration"]:
        pass  # Already set from NARRATION: label
    elif found_any_label:
        result["full_narration"] = _clean_markdown(response)
    else:
        # No labels at all - treat entire response as free-form narration
        clean_resp = _clean_markdown(response)
        result["full_narration"] = clean_resp
        last_line = lines[-1].strip() if lines else ""
        if last_line and len(last_line.split()) <= 8 and not last_line.endswith((".", "!", "?")):
            result["title"] = _clean_markdown(last_line)[:60]
            result["full_narration"] = "\n".join(lines[:-1]).strip()

    # Generate title from HOOK if no explicit TITLE was found
    if (not result["title"] or result["title"] == "GTA V BRAINROT") and result.get("hook"):
        hook_title = result["hook"].rstrip(".!?")
        hook_title = re.sub(r'[^\w\s\'-]', '', hook_title).strip()
        if hook_title:
            result["title"] = hook_title[:60]

    # If still no title, generate from first sentence of narration
    if (not result["title"] or result["title"] == "GTA V BRAINROT") and result["full_narration"]:
        first_sentence = result["full_narration"].split(".")[0].strip()
        if first_sentence and len(first_sentence) > 5:
            first_sentence = re.sub(r'[^\w\s\'-]', '', first_sentence).strip()
            if len(first_sentence) > 55:
                first_sentence = first_sentence[:55] + "..."
            result["title"] = first_sentence

    # Always extract emphasis from narration if none was explicitly provided
    if not result["emphasis"] and result["full_narration"]:
        result["emphasis"] = _extract_emphasis_from_text(result["full_narration"])

    return result


def _extract_emphasis_from_text(text: str) -> list[str]:
    """Extract ALL CAPS words as emphasis targets."""
    words = text.split()
    caps_words = [w.strip(".,!?;:\"'") for w in words if w.isupper() and len(w) > 2]
    # Deduplicate while preserving order
    seen = set()
    return [w for w in caps_words if not (w in seen or seen.add(w))][:5]


def _get_random_fallback() -> tuple[str, str, list[str]]:
    """Return a randomly chosen fallback script tuple (narration, title, emphasis)."""
    return random.choice(FALLBACK_SCRIPTS)


def generate_brainrot_script(
    clip_description: str = "",
    style: str = "chaotic",
) -> tuple[str, str, list[str]]:
    """
    Generate a brainrot script.
    Returns: (full_narration, title, emphasis_words)
    """
    api_key = config.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not set! Using fallback.")
        return _get_random_fallback()

    client = Groq(api_key=api_key)
    model_name = config.GROQ_MODEL or "openai/gpt-oss-20b"

    best_result = {
        "full_narration": "",
        "title": "GTA V BRAINROT",
        "emphasis": [],
        "word_count": 0,
    }

    # Limit retries to 2 to stay well within Groq TPM and RPM rate limits
    for attempt in range(2):
        selected_format = random.choice(FORMAT_CATEGORIES)
        selected_hook = random.choice(SCROLL_HOOKS)

        user_prompt = (
            f"Write a {style} brainrot short script using category: {selected_format}.\n"
            f"Start the HOOK with: '{selected_hook}'\n"
            f"Requirements:\n"
            f"- Total 40-65 words across HOOK + BODY + PUNCHLINE\n"
            f"- HOOK: attention grabber in 5-10 words starting with '{selected_hook}'\n"
            f"- BODY: 3-5 punchy lines (25-45 words total)\n"
            f"- PUNCHLINE: definitive, complete concluding punchline (5-10 words)\n"
            f"- ALL CAPS on 2-3 key words for emphasis\n"
            f"- ZERO EMOJIS in HOOK, BODY, PUNCHLINE, or EMPHASIS — plain text words only (emojis are only in TITLE)\n"
            f"- MUST have a DEFINITIVE, COMPLETE ENDING (NO looping mechanism or trailing sentences)\n\n"
            f"Format EXACTLY like this:\n"
            f"HOOK: <5-10 words>\n"
            f"BODY: <25-45 words>\n"
            f"PUNCHLINE: <5-10 words>\n"
            f"EMPHASIS: <word1, word2>\n"
            f"TITLE: <viral title under 55 chars with 1-2 shock emojis>"
        )

        print(f"🤖 Groq [{model_name}]: generating script using format [{selected_format.split('(')[0].strip()}] (attempt {attempt + 1})…")

        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": USER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.92,
                max_tokens=2048,  # Optimal limit (~1500 total tokens per request) - safe from 429 TPM exhaustion and reasoning truncation
                timeout=35,
            )
        except RateLimitError as e:
            print(f"   ⚠ Groq 429 Rate Limit hit (attempt {attempt + 1}): {e}")
            if attempt < 1:
                wait_secs = 12
                print(f"   ⏳ Waiting {wait_secs}s for rate limit window to reset…")
                time.sleep(wait_secs)
                continue
            else:
                print("   ⚠ Rate limit exceeded — selecting diverse fallback script")
                return _get_random_fallback()
        except Exception as e:
            print(f"   ⚠ Groq API error (attempt {attempt + 1}): {e}")
            if attempt < 1:
                time.sleep(2)
                continue
            elif not best_result["full_narration"]:
                print("   ⚠ Using fallback narration from pool")
                return _get_random_fallback()
            continue

        raw_response = completion.choices[0].message.content or ""
        raw_response = raw_response.strip()

        if not raw_response:
            print(f"   ⚠ Received empty content from model (attempt {attempt + 1})")
            continue

        # Parse structured response
        parsed = _parse_structured_response(raw_response)

        # Strip formatting and emojis
        narration = _strip_emojis(parsed["full_narration"])
        narration = _clean_markdown(narration)
        title = _clean_markdown(parsed["title"])

        # Strict Brand Safety check: scan narration and title for forbidden/bannable terms
        combined_text = (narration + " " + title).upper()
        has_forbidden = False
        for forbidden in FORBIDDEN_WORDS:
            if re.search(r'\b' + re.escape(forbidden) + r'\b', combined_text):
                print(f"   ⚠ Safety filter triggered: found forbidden word '{forbidden}' - retrying...")
                has_forbidden = True
                break

        if has_forbidden:
            continue

        # Get emphasis words
        emphasis = parsed["emphasis"]
        if not emphasis:
            emphasis = _extract_emphasis_from_text(narration)

        wc = len(narration.split())
        if wc >= 25:
            best_result["full_narration"] = narration
            best_result["title"] = title or "GTA V BRAINROT 🤯"
            best_result["emphasis"] = emphasis
            best_result["word_count"] = wc

        # Optimal word count window
        if 35 <= wc <= 75:
            break

    # If we got nothing useful after attempts, use a random fallback script
    if not best_result["full_narration"]:
        print("   ⚠ No valid script generated, selecting diverse fallback")
        return _get_random_fallback()

    print(f"   📝 {best_result['word_count']} words, {len(best_result['emphasis'])} emphasis words")
    return best_result["full_narration"], best_result["title"], best_result["emphasis"]



# Backward compatibility for old code that expects 2 return values
def generate_brainrot_script_legacy(
    clip_description: str = "",
    style: str = "chaotic",
) -> tuple[str, str]:
    """Legacy wrapper that returns (narration, title) without emphasis."""
    narration, title, _ = generate_brainrot_script(clip_description, style)
    return narration, title


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="chaotic")
    args = ap.parse_args()
    n, t, e = generate_brainrot_script(style=args.style)
    print(f"\n✅ {len(n.split())} words: {n}")
    print(f"📌 {t}")
    print(f"🔍 Emphasis: {e}")