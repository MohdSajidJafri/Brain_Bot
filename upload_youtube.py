"""
Upload rendered GTA VI brainrot shorts to YouTube Shorts.
Uses OAuth2 refresh token from env vars directly (no browser required).
All API calls have timeouts to prevent indefinite hangs on CI.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import config

YOUTUBE_API_TIMEOUT = 120  # 2 minute timeout for API calls


def _get_authenticated_service():
    """
    Build YouTube API client with OAuth2 using refresh token from env.
    Does NOT open a browser — uses the refresh token directly.
    Falls back to token file cache if available.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    creds = None
    token_file = config.CACHE_DIR / "yt_token.json"

    # Try loading cached token file first
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except Exception as e:
            print(f"   ⚠ Could not load cached token: {e}")
            creds = None

    # If we have a refresh token in env, use it directly
    if (not creds or not creds.valid) and config.YT_REFRESH_TOKEN:
        print("   Using refresh token from environment...")
        creds = Credentials(
            token=None,
            refresh_token=config.YT_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=config.YT_CLIENT_ID,
            client_secret=config.YT_CLIENT_SECRET,
            scopes=SCOPES,
        )

    # Refresh the token if expired
    if creds and not creds.valid:
        try:
            creds.refresh(Request())
            print("   ✅ Token refreshed")
        except Exception as e:
            print(f"   ⚠ Token refresh failed: {e}")
            creds = None

    if not creds or not creds.valid:
        print("❌ Could not authenticate with YouTube. Check YT_REFRESH_TOKEN in .env")
        print("   Run 'python get_refresh_token.py' to generate a new token")
        return None

    # Save token for next run
    try:
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    except Exception as e:
        print(f"   ⚠ Could not save token: {e}")

    return build("youtube", "v3", credentials=creds)


def upload_short(
    video_path: Path,
    title: str,
    description: str = "",
    privacy: str = "public",
) -> str:
    """
    Upload a short to YouTube.
    
    Args:
        video_path: Path to the rendered MP4.
        title: YouTube Shorts title.
        description: Video description (hashtags appended automatically).
        privacy: public / unlisted / private.
    
    Returns:
        YouTube video ID, or empty string on failure.
    """
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return ""

    # Use description directly from pipeline
    desc = description.strip()

    print(f"📤 YouTube: uploading {video_path.name}…")
    print(f"   Title: {title}")
    print(f"   Privacy: {privacy}")

    youtube = _get_authenticated_service()
    if not youtube:
        print("⚠ YouTube authentication failed — skipping upload")
        return ""

    body = {
        "snippet": {
            "title": title[:100],
            "description": desc,
            "tags": [
                "GTA 6", "GTA VI", "gta6leaks", "genz", "genalpha", "brainrot", "youtubeshorts", "youtube", "gta6gameplay", "shorts", "viral",
                "trending", "gtabrainrot", "gaming", "fyp", "gtaonline", "gta5",
                "gtav", "funnygaming", "gamingclips", "rockstargames", "NPC"
            ],
            "categoryId": "20",  # Gaming
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=4 * 1024 * 1024, resumable=True)

    try:
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        import socket
        socket.setdefaulttimeout(YOUTUBE_API_TIMEOUT)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"   ⏫ Upload progress: {pct}%")

        video_id = response["id"]
        print(f"   ✅ Uploaded! https://www.youtube.com/shorts/{video_id}")
        return video_id

    except HttpError as e:
        print(f"❌ YouTube upload failed: {e}")
        return ""
    except Exception as e:
        print(f"❌ YouTube upload error: {e}")
        return ""


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, help="Path to MP4")
    ap.add_argument("--title", default="GTA VI BRAINROT 🎮🔥", help="Video title")
    ap.add_argument("--description", default="", help="Video description")
    ap.add_argument("--privacy", default="public", choices=["private", "unlisted", "public"])
    args = ap.parse_args()

    upload_short(Path(args.video), args.title, args.description, args.privacy)