"""
Upload rendered GTA VI brainrot shorts to YouTube Shorts.
Reuses the same OAuth2 pattern as the existing YouTube bot.
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

import config

# Viral GTA / gaming hashtags
HASHTAGS_POOL = [
    "#GTAVI", "#GTA6", "#GamingShorts", "#Brainrot", "#GTA6Gameplay",
    "#GamingMemes", "#NPC", "#GTA6Leaks", "#RockstarGames", "#GTA",
    "#GamingFails", "#Shorts", "#GTA6Trailer", "#GTA6Moment", "#GTA6Online",
    "#GrandTheftAuto", "#GamingVideos", "#GTA6Edit", "#GTA6Clip", "#ViralGaming",
]


def _pick_hashtags(n: int = 5) -> str:
    """Pick n random hashtags."""
    return " ".join(random.sample(HASHTAGS_POOL, min(n, len(HASHTAGS_POOL))))


def _get_authenticated_service():
    """Build YouTube API client with OAuth2."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    creds = None
    token_file = config.CACHE_DIR / "yt_token.json"

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not config.YT_CLIENT_ID or not config.YT_CLIENT_SECRET:
                print("❌ YT_CLIENT_ID / YT_CLIENT_SECRET_VALUE not set")
                sys.exit(1)

            client_config = {
                "installed": {
                    "client_id": config.YT_CLIENT_ID,
                    "client_secret": config.YT_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0, open_browser=False)

        # Save token for next time
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
        print(f"   💾 Token saved to {token_file}")

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
        YouTube video ID.
    """
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        sys.exit(1)

    # Build description with hashtags
    desc = description.strip()
    if desc:
        desc += "\n\n"
    desc += _pick_hashtags(7)

    print(f"📤 YouTube: uploading {video_path.name}…")
    print(f"   Title: {title}")
    print(f"   Privacy: {privacy}")

    youtube = _get_authenticated_service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": desc,
            "tags": [
                "GTA VI", "GTA 6", "Gaming", "Shorts", "Brainrot",
                "GTA6Gameplay", "GamingMemes", "Rockstar",
            ],
            "categoryId": "20",  # Gaming
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
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, help="Path to MP4")
    ap.add_argument("--title", default="GTA VI BRAINROT 🎮🔥", help="Video title")
    ap.add_argument("--description", default="", help="Video description")
    ap.add_argument("--privacy", default="public", choices=["private", "unlisted", "public"])
    args = ap.parse_args()

    upload_short(Path(args.video), args.title, args.description, args.privacy)