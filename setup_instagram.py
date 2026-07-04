#!/usr/bin/env python3
"""
One-time Instagram session setup.

Instagram blocks automated logins (CSRF error), so this script
helps you extract a session from your browser instead.

Steps:
1. Log into instagram.com in your browser
2. Install a cookie export extension (e.g. "Get cookies.txt" for Chrome)
3. Export cookies as Netscape format to data/cache/instagram_cookies.txt
4. Run this script to convert them to instagrapi format
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import config


def main():
    settings_path = config.CACHE_DIR / "ig_settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    # Method 1: Try to log in normally (may fail with CSRF)
    if config.IG_USERNAME and config.IG_PASSWORD:
        print(f"📱 Attempting login as {config.IG_USERNAME}…")
        try:
            from instagrapi import Client

            cl = Client()
            cl.set_user_agent(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
            cl.delay_range = [1, 3]

            def challenge_handler(username, challenge_type):
                print(f"\n⚠ Verification required for {username}")
                code = input("   Enter code from email/phone: ").strip()
                return code

            cl.challenge_code_handler = challenge_handler
            cl.login(config.IG_USERNAME, config.IG_PASSWORD)
            cl.dump_settings(str(settings_path))
            print(f"\n✅ Session saved to {settings_path}")
            print("   Now commit and push:")
            print(f"   git add {settings_path}")
            print("   git commit -m 'Add Instagram session'")
            print("   git push")
            return
        except Exception as e:
            print(f"   ❌ Login failed: {e}")

    # Method 2: Extract from browser cookies
    print("\n" + "=" * 60)
    print("ALTERNATIVE: Extract session from your browser")
    print("=" * 60)
    print()
    print("Since Instagram blocks automated logins, use this method:")
    print()
    print("1. Open Chrome/Firefox and log into instagram.com")
    print("2. Install a cookie export extension:")
    print("   - Chrome: 'Get cookies.txt' or 'EditThisCookie'")
    print("   - Firefox: 'cookies.txt'")
    print("3. On instagram.com, use the extension to export cookies")
    print("   as Netscape format to: data/cache/instagram_cookies.txt")
    print("4. Run this script again")
    print()
    print("Or manually create the session file:")
    print("   The file should be at: data/cache/ig_settings.json")
    print("   It needs 'cookies', 'user_agent', and 'device_id' fields.")
    print()

    # Check if cookies file was provided
    cookies_file = config.CACHE_DIR / "instagram_cookies.txt"
    if cookies_file.exists():
        print("📁 Found cookies file, converting to session…")
        try:
            from instagrapi import Client
            cl = Client()
            cl.set_user_agent(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
            cl.load_settings(str(settings_path)) if settings_path.exists() else None
            # Try to set cookies from the file
            import http.cookiejar
            cj = http.cookiejar.MozillaCookieJar(str(cookies_file))
            cj.load()
            cl.cookie_jar = cj
            cl.dump_settings(str(settings_path))
            print(f"✅ Session saved to {settings_path}")
        except Exception as e:
            print(f"❌ Failed to convert cookies: {e}")
    else:
        print("No cookies file found at:", cookies_file)


if __name__ == "__main__":
    main()