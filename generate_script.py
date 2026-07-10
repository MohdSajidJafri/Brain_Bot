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

from groq import Groq

import config

# Forbidden/bannable words to ensure absolute content safety and brand protection
FORBIDDEN_WORDS = [
    "RAPE", "RAPED", "RAPING", "RAPIST", "NIGGER", "FAGGOT", "RETARD", "RETARDED",
    "SUICIDE", "KILL MYSELF", "KILL YOURSELF", "SLUT", "WHORE", "CUNT", "DICK",
    "PORN", "SEX", "PEDO", "PEDOPHILE", "TERRORIST", "BOMBING", "MASSACRE"
]

USER_SYSTEM_PROMPT = (
    "You write viral brainrot short-form video scripts. "
    "CRITICAL: Do NOT write generic gaming or NPC-focused content. The visual is GTA V gameplay, but the script topic must be completely random, weird, and unhinged brainrot humor. "
    "CRITICAL: You must choose exactly ONE of the following 12 video formats to write this script on:\n"
    "1. FAKE LIFE ADVICE: Sound profound, but slowly become completely unhinged (e.g. 'Never trust someone who says bro trust me. The reason billionaires wake up at 4 AM is because they are avoiding responsibilities. If your barber says lemme try something, start praying.')\n"
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
    "CRITICAL: Do NOT use any emojis or special unicode characters in the HOOK, BODY, or PUNCHLINE. Use ONLY plain text words and punctuation in the script sections.\n"
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
    "CRITICAL: Design the script as a SEAMLESS INFINITE LOOP. The final sentence (PUNCHLINE) must be an open-ended, incomplete phrase that flows naturally and grammatically back into the beginning of the HOOK. For example, if HOOK is 'Why GTA 6 physics make no sense...', the PUNCHLINE should close with '...and that is exactly' so when the video loops, it reads: '...and that is exactly Why GTA 6 physics make no sense...'. "
    "CRITICAL: Do NOT generate scripts containing inappropriate, explicit, offensive, or bannable terms (such as rape, slurs, explicit sexual violence, self-harm, hate speech). Fail-safe: keep all content strictly safe-for-work and advertiser friendly.\n"
    "Structure each script EXACTLY as:\n"
    "HOOK: <A single short sentence, 5-10 words, starting with one of the scroll-stopping hooks>\n"
    "BODY: <3-5 short punchy lines telling the unhinged/brainrot story or list, 25-45 words total>\n"
    "PUNCHLINE: <A single funny loop-ended closing line, 5-10 words>\n"
    "EMPHASIS: <comma-separated list of the 2-3 words in the script written in ALL CAPS for emphasis>\n"
    "TITLE: <viral clickbait title under 55 chars with 1-2 gamer/shock emojis (e.g. 💀, 🤯)>"
)

# Fallback narration for when Groq API fails
FALLBACK_NARRATION = (
    "EVER wonder what happens when you mess with GTA V physics? "
    "Bro I was just driving NORMAL and a trash truck SPAWNS on my car. "
    "This game is PEAK chaos and I love every second of it."
)
FALLBACK_EMPHASIS = "EVER, NORMAL, SPAWNS, PEAK"


def _strip_emojis(text: str) -> str:
    """Remove emoji characters from text."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text).strip()


def _parse_structured_response(response: str) -> dict:
    """Parse the structured LLM response into components.
    Handles both strict HOOK|BODY|PUNCHLINE format and free-form text.
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
    sections = {}
    found_any_label = False

    for line in lines:
        line = line.strip()
        if not line:
            continue
        upper = line.upper()

        if upper.startswith("HOOK:"):
            found_any_label = True
            current_section = "hook"
            sections["hook"] = line.split(":", 1)[1].strip()
        elif upper.startswith("BODY:"):
            found_any_label = True
            current_section = "body"
            sections["body"] = line.split(":", 1)[1].strip()
        elif upper.startswith("PUNCHLINE:"):
            found_any_label = True
            current_section = "punchline"
            sections["punchline"] = line.split(":", 1)[1].strip()
        elif upper.startswith("EMPHASIS:"):
            found_any_label = True
            current_section = "emphasis"
            raw = line.split(":", 1)[1].strip()
            result["emphasis"] = [w.strip().upper() for w in raw.split(",") if w.strip()]
        elif upper.startswith("NARRATION:"):
            found_any_label = True
            result["full_narration"] = line.split(":", 1)[1].strip()
        elif upper.startswith("TITLE:"):
            found_any_label = True
            result["title"] = line.split(":", 1)[1].strip()[:60]
        elif current_section and line:
            sections[current_section] = sections.get(current_section, "") + " " + line

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
        # Had labels but no content - shouldn't happen but handle gracefully
        result["full_narration"] = response
    else:
        # No labels at all - treat entire response as free-form narration
        # Try to extract title from last line if it looks like a title
        result["full_narration"] = response
        # Check if last line looks like a title (short, no punctuation)
        last_line = lines[-1].strip() if lines else ""
        if last_line and len(last_line.split()) <= 8 and not last_line.endswith((".", "!", "?")):
            result["title"] = last_line[:60]
            # Remove title from narration
            result["full_narration"] = "\n".join(lines[:-1]).strip()

    # Generate title from HOOK if no explicit TITLE was found
    if result["title"] == "GTA V BRAINROT" and result.get("hook"):
        # Use hook as title (truncate to 60 chars if needed)
        hook_title = result["hook"].rstrip(".!?")
        hook_title = re.sub(r'[^\w\s\'-]', '', hook_title).strip()
        if hook_title:
            # Style prefix based on content
            result["title"] = hook_title[:60]

    # If still no title, generate from first line of narration
    if result["title"] == "GTA V BRAINROT" and result["full_narration"]:
        first_sentence = result["full_narration"].split(".")[0].strip()
        if first_sentence and len(first_sentence) > 5:
            first_sentence = re.sub(r'[^\w\s\'-]', '', first_sentence).strip()
            if len(first_sentence) > 55:
                first_sentence = first_sentence[:55] + "..."
            result["title"] = first_sentence

    # Always extract emphasis from narration as fallback
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
        print("❌ GROQ_API_KEY not set!")
        sys.exit(1)

    client = Groq(api_key=api_key)

    # Randomly select a format category to keep scripts fresh and highly varied
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
    selected_format = random.choice(formats)

    user_prompt = (
        f"Generate a brainrot short script using the format category: {selected_format}.\n\n"
        f"Requirements:\n"
        f"- Hook must start with one of the 9 scroll-stopping hooks listed in the system instructions.\n"
        f"- Script topic must be completely unrelated to GTA or gaming, but highly unhinged and funny.\n"
        f"- Total 40-65 words across HOOK + BODY + PUNCHLINE\n"
        f"- HOOK: grab attention in 5-10 words\n"
        f"- BODY: 3-5 short punchy lines (25-45 words total)\n"
        f"- PUNCHLINE: loop-ended closing line (5-10 words)\n"
        f"- Use ALL CAPS on 2-3 key words for emphasis\n"
        f"- NO EMOJIS whatsoever in HOOK, BODY, or PUNCHLINE - plain text only\n"
        f"- MUST be a SEAMLESS INFINITE LOOP where PUNCHLINE flows directly back into HOOK.\n"
        f"- CRITICAL: Do NOT use any forbidden or bannable words (e.g. RAPE, slurs, hate speech, explicit violence).\n\n"
        f"Format EXACTLY like this:\n"
        f"HOOK: <attention grabber, 5-10 words>\n"
        f"BODY: <3-5 short lines, 25-45 words total>\n"
        f"PUNCHLINE: <loop-ended closing, 5-10 words>\n"
        f"EMPHASIS: <comma-separated list of the 2-3 ALL CAPS words>\n"
        f"TITLE: <viral clickbait title under 55 chars with 1-2 gamer/shock emojis (e.g. 💀, 🤯)>"
    )

    print(f"🤖 Groq: generating script using format [{selected_format}]…")

    best_result = {
        "full_narration": "",
        "title": "GTA V BRAINROT",
        "emphasis": [],
        "word_count": 0,
    }

    for attempt in range(2):
        try:
            completion = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": USER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.95,
                max_tokens=600,
                timeout=30,
            )
        except Exception as e:
            print(f"   ⚠ Groq API error (attempt {attempt+1}): {e}")
            if attempt == 1:
                print(f"   ⚠ Using fallback narration")
                return FALLBACK_NARRATION, "GTA V BRAINROT", ["EVER", "NORMAL", "SPAWNS", "PEAK"]
            continue

        response = completion.choices[0].message.content.strip()

        # Parse structured response
        parsed = _parse_structured_response(response)

        # Strip formatting
        narration = _strip_emojis(parsed["full_narration"])
        narration = narration.replace("**", "").replace("__", "").replace("*", "")
        title = parsed["title"].replace("**", "").replace("__", "").replace("*", "")

        # Strict Brand Safety check: scan narration and title for forbidden/bannable terms
        combined_text = (narration + " " + title).upper()
        has_forbidden = False
        for forbidden in FORBIDDEN_WORDS:
            # Match word boundary to avoid false positives (e.g. "grape")
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
        if wc > best_result["word_count"] and wc >= 30:
            best_result["full_narration"] = narration
            best_result["title"] = title or "GTA V BRAINROT"
            best_result["emphasis"] = emphasis
            best_result["word_count"] = wc

        if 35 <= wc <= 75:
            break
        user_prompt += "\n\nMake it shorter and punchier! MUST be 40-65 words."

    # If we got nothing useful, use fallback
    if not best_result["full_narration"]:
        print("   ⚠ No valid script generated, using fallback")
        return FALLBACK_NARRATION, "GTA V BRAINROT", ["EVER", "NORMAL", "SPAWNS", "PEAK"]

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