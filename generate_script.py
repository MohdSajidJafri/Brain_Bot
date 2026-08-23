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

from groq import Groq

import config

# Forbidden/bannable words to ensure absolute content safety and brand protection
FORBIDDEN_WORDS = [
    "RAPE", "RAPED", "RAPING", "RAPIST", "NIGGER", "FAGGOT", "RETARD", "RETARDED",
    "SUICIDE", "KILL MYSELF", "KILL YOURSELF", "SLUT", "WHORE", "CUNT",
    "PORN", "PEDO", "PEDOPHILE", "TERRORIST", "BOMBING", "MASSACRE"
]

USER_SYSTEM_PROMPT = (
    "You write viral brainrot short-form video scripts. "
    "CRITICAL: Do NOT write generic gaming or NPC-focused content. The visual is GTA V gameplay, but the script topic must be completely random, weird, and unhinged brainrot humor. "
    "CRITICAL: You must choose exactly ONE of the following 12 video formats to write this script on:\n"
    "1. FAKE LIFE ADVICE: Sound profound, but slowly become completely unhinged (e.g. 'Never trust someone who says bro trust me. The reason billionaires wake up at 4 AM is because they are avoiding responsibilities. If your barber says lemme try something, start screaming.')\n"
    "2. CONSPIRACY BRAINROT: Start believable, then completely ruin it (e.g. 'Have you noticed pigeons never sit in traffic? That is because they already know where you are going. Your calculator has never asked how you are doing.')\n"
    "3. NPC THOUGHTS: Reveal weird cashiers or server secrets (e.g. 'Every cashier has a favorite customer and it is never you. The waiter remembers exactly what embarrassing thing you ordered.')\n"
    "4. RANDOM FACTS (90% FAKE): Say completely fake things confidently to start arguments (e.g. 'Bananas are WiFi-compatible if you believe hard enough. The moon actually rotates around Costco.')\n"
    "5. POV VIDEOS: High-relatability gamer/social situations (e.g. 'POV: You are the friend who always says I am five minutes away. POV: You accidentally become the responsible adult. POV: The quiet kid starts talking.')\n"
    "6. TIER LISTS: Rate completely random everyday things (e.g. 'Excuses for being late, ways to lose aura, school bathroom experiences, Indian relatives, barber conversations.')\n"
    "7. IMAGINE EXPLAINING THIS: Contrast modern situations with history (e.g. 'Imagine explaining to a medieval knight that people spend twelve hundred dollars to watch TikTok.')\n"
    "8. THINGS EVERYONE DOES BUT NEVER ADMITS: Universal quirks (e.g. 'Opening the fridge just to stare. Pretending to know directions. Re-reading the same text fifteen times. Walking faster when someone is behind you.')\n"
    "9. FAKE MOTIVATIONAL SPEAKER: Speak like a clueless millionaire coach (e.g. 'The difference between you and Elon Musk is... absolutely nothing. Except money, companies, intelligence, connections...')\n"
    "10. HOW IT FEELS: Expressive gamer/social emotions (e.g. 'How it feels to find money in old jeans. How it feels after sending a risky text. How it feels after saying you too to the waiter.')\n"
    "11. RANKING PAIN LEVELS: Everyday mental/physical pain (e.g. 'USB upside down three times. Forgetting why you opened Google. Calling teacher mom.')\n"
    "12. INTERNET LORE: Make up ridiculous history (e.g. 'Back in 2016 everyone communicated exclusively through Minion memes.')\n\n"
    "CRITICAL: Absolute rule: ZERO EMOJIS in HOOK, BODY, PUNCHLINE, or EMPHASIS. Script text must be 100% plain words and standard punctuation only. The text-to-speech voice synthesizer reads emoji names out loud and ruins the audio. Emojis are ONLY allowed in TITLE.\n"
    "CRITICAL: You must choose one of these 9 scroll-stopping hooks to start your HOOK:\n"
    "- 'Nobody talks about this...'\n"
    "- 'I just realized something...'\n"
    "- 'This might be the dumbest thing I\\'ve ever noticed...'\n"
    "- 'Hear me out...'\n"
    "- 'I refuse to believe I\\'m the only one...'\n"
    "- 'Imagine if...'\n"
    "- 'This is either genius or completely stupid.'\n"
    "- 'I have a theory.'\n"
    "- 'How it feels to...'\n\n"
    "CRITICAL: The script must have a DEFINITIVE, COMPLETE ENDING. Do NOT use an infinite loop or open-ended trailing sentence. The final sentence (PUNCHLINE) must be a complete, punchy, and hilarious conclusion sentence that brings the story/joke to a decisive end.\n"
    "CRITICAL: Do NOT generate scripts containing inappropriate, explicit, offensive, sensitive, or bannable terms (such as rape, slurs, explicit sexual violence, self-harm, hate speech). Fail-safe: keep all content strictly safe-for-work, secular, and advertiser friendly.\n"
    "Structure each script EXACTLY as:\n"
    "HOOK: <A single short sentence, 5-10 words, starting with one of the scroll-stopping hooks>\n"
    "BODY: <3-5 short punchy lines telling the unhinged/brainrot story or list, 25-45 words total>\n"
    "PUNCHLINE: <A single hilarious definitive concluding punchline, 5-10 words>\n"
    "EMPHASIS: <comma-separated list of the 2-3 words in the script written in ALL CAPS for emphasis>\n"
    "TITLE: <viral clickbait title under 55 chars with 1-2 shock emojis (e.g. 💀, 🤯)>"
)

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

    # 12 distinct format categories to guarantee wide variety across runs
    formats = [
        "FAKE LIFE ADVICE (profound advice that slowly becomes unhinged)",
        "CONSPIRACY BRAINROT (start believable, then ruin it completely)",
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

    best_result = {
        "full_narration": "",
        "title": "GTA V BRAINROT",
        "emphasis": [],
        "word_count": 0,
    }

    model_name = config.GROQ_MODEL or "openai/gpt-oss-20b"

    for attempt in range(3):
        selected_format = random.choice(formats)
        user_prompt = (
            f"Generate a brainrot short script using the format category: {selected_format}.\n\n"
            f"Requirements:\n"
            f"- Hook must start with one of the 9 scroll-stopping hooks listed in the system instructions.\n"
            f"- Script topic must be completely unrelated to GTA or gaming, but highly unhinged and funny.\n"
            f"- Total 40-65 words across HOOK + BODY + PUNCHLINE\n"
            f"- HOOK: grab attention in 5-10 words\n"
            f"- BODY: 3-5 short punchy lines (25-45 words total)\n"
            f"- PUNCHLINE: definitive, complete concluding punchline (5-10 words)\n"
            f"- Use ALL CAPS on 2-3 key words for emphasis\n"
            f"- ZERO EMOJIS in HOOK, BODY, PUNCHLINE, or EMPHASIS — plain text words only (emojis are only allowed in TITLE)\n"
            f"- MUST have a DEFINITIVE, COMPLETE ENDING (NO looping mechanism or open-ended trailing sentences)\n"
            f"- CRITICAL: Do NOT use any forbidden or bannable words (e.g. hate speech, slurs, explicit violence).\n\n"
            f"Format EXACTLY like this:\n"
            f"HOOK: <attention grabber, 5-10 words>\n"
            f"BODY: <3-5 short lines, 25-45 words total>\n"
            f"PUNCHLINE: <definitive closing punchline, 5-10 words>\n"
            f"EMPHASIS: <comma-separated list of the 2-3 ALL CAPS words>\n"
            f"TITLE: <viral clickbait title under 55 chars with 1-2 shock emojis (e.g. 💀, 🤯)>"
        )


        print(f"🤖 Groq [{model_name}]: generating script using format [{selected_format.split('(')[0].strip()}] (attempt {attempt + 1})…")

        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": USER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.95,
                max_tokens=4096,  # Sizable allowance for reasoning models (e.g., openai/gpt-oss-20b) + output
                timeout=45,
            )
        except Exception as e:
            print(f"   ⚠ Groq API error (attempt {attempt + 1}): {e}")
            if attempt == 2 and not best_result["full_narration"]:
                print(f"   ⚠ Using fallback narration from pool")
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

    # If we got nothing useful after all attempts, use a random fallback script
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