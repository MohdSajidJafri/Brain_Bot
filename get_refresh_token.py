#!/usr/bin/env python3
"""
Helper script: Generate a YouTube OAuth refresh token for a new channel.

Usage:
    python get_refresh_token.py

Then paste the printed REFRESH_TOKEN into your .env file.
Uses the same YT_CLIENT_ID and YT_CLIENT_SECRET_VALUE from your .env.
"""
from __future__ import annotations

import sys
from pathlib import Path
from dotenv import load_dotenv

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

load_dotenv()

import config



def main() -> None:
    if not config.YT_CLIENT_ID or "your_client_id" in config.YT_CLIENT_ID:
        print("❌ Set YT_CLIENT_ID and YT_CLIENT_SECRET_VALUE in .env first!")
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ]


    client_config = {
        "installed": {
            "client_id": config.YT_CLIENT_ID,
            "client_secret": config.YT_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    print("=" * 60)
    print("🔑 YOUTUBE REFRESH TOKEN GENERATOR")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT: When the browser opens, sign in with your")
    print("   NEW channel's email address (not your old one)!")
    print()
    print("   Then click 'Continue' to grant access.")
    print()

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True, prompt="consent select_account")

    # Verify which channel was authorized
    channel_name = "Unknown"
    channel_id = "Unknown"
    try:
        from googleapiclient.discovery import build
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        ch = yt.channels().list(mine=True, part="snippet").execute()
        if ch.get("items"):
            channel_name = ch["items"][0]["snippet"]["title"]
            channel_id = ch["items"][0]["id"]
    except Exception as e:
        channel_name = f"Error querying: {e}"

    print()
    print("=" * 60)
    print("✅ SUCCESS! Authorization Complete")
    print(f"   📺 Channel Connected: {channel_name}")
    print(f"   🆔 Channel ID:        {channel_id}")
    print("=" * 60)
    print()
    print("🔑 Your new Master Refresh Token:")
    print(f"   {creds.refresh_token}")
    print()
    print("=" * 60)

    print()
    print("📌 Add this to your .env file:")
    print(f'   YT_REFRESH_TOKEN="{creds.refresh_token}"')
    print()
    print("   Or if keeping both old and new tokens:")
    print(f'   YT_REFRESH_TOKEN_GTA="{creds.refresh_token}"')
    print()


if __name__ == "__main__":
    main()