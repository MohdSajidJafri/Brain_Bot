"""
Self-Optimizing YouTube Analytics Engine.
Queries private YouTube Analytics API (v2) & Data API (v3) to analyze audience retention,
Average View Duration (AVD), Average Percentage Viewed (APV), and engagement.
Saves optimization weights to data/cache/analytics_intelligence.json to continuously
train and improve script generation, styles, hooks, and video length.
"""
from __future__ import annotations

import datetime
import json
import os
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
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

INTELLIGENCE_FILE = config.CACHE_DIR / "analytics_intelligence.json"


def get_authenticated_services():
    """
    Build YouTube Data (v3) and YouTube Analytics (v2) API clients.
    """
    if not config.YT_REFRESH_TOKEN or not config.YT_CLIENT_ID or not config.YT_CLIENT_SECRET:
        return None, None

    try:
        creds = Credentials(
            token=None,
            refresh_token=config.YT_REFRESH_TOKEN,
            client_id=config.YT_CLIENT_ID,
            client_secret=config.YT_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES,
        )
        creds.refresh(Request())
        yt_data = build("youtube", "v3", credentials=creds, cache_discovery=False)
        yt_analytics = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
        return yt_data, yt_analytics
    except Exception as e:
        print(f"⚠ Could not initialize YouTube Analytics credentials: {e}")
        return None, None


def fetch_private_analytics_report(days_back: int = 30) -> dict:
    """
    Query YouTube Analytics API for channel-level and video-level retention metrics.
    """
    yt_data, yt_analytics = get_authenticated_services()
    if not yt_analytics:
        return {}

    today = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")

    analytics_data = {
        "channel_metrics": {},
        "top_videos": [],
        "traffic_sources": [],
    }

    print(f"🔍 Fetching private YouTube Analytics ({start_date} to {today})…")

    # 1. Channel Level Core Metrics
    try:
        res = yt_analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=today,
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost,likes,comments",
        ).execute()

        headers = [h["name"] for h in res.get("columnHeaders", [])]
        rows = res.get("rows", [])
        if rows:
            row_dict = dict(zip(headers, rows[0]))
            analytics_data["channel_metrics"] = row_dict
            print(f"   ✅ Channel Views: {row_dict.get('views', 0):,} | APV: {row_dict.get('averageViewPercentage', 0):.1f}% | Avg Duration: {row_dict.get('averageViewDuration', 0):.1f}s")
    except HttpError as e:
        print(f"   ⚠ Channel analytics query notice: {e}")

    # 2. Top Performing Videos with Retention
    try:
        v_res = yt_analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=today,
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes",
            dimensions="video",
            sort="-views",
            maxResults=25,
        ).execute()

        v_headers = [h["name"] for h in v_res.get("columnHeaders", [])]
        for row in v_res.get("rows", []):
            analytics_data["top_videos"].append(dict(zip(v_headers, row)))
        print(f"   ✅ Fetched video-level retention data for {len(analytics_data['top_videos'])} videos")
    except HttpError as e:
        print(f"   ⚠ Video-level analytics query notice: {e}")

    return analytics_data


def compute_optimization_intelligence(analytics_data: dict) -> dict:
    """
    Analyze analytics metrics and generate actionable optimization parameters
    for script generation, style weights, and target clip lengths.
    """
    default_intelligence = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "style_weights": {
            "chaotic": 0.35,
            "meme": 0.30,
            "story": 0.20,
            "npc": 0.15,
        },
        "target_word_count_min": 40,
        "target_word_count_max": 55,
        "optimal_video_duration_range": [15, 25],
        "top_performing_hook_styles": [
            "Nobody talks about this...",
            "I just realized something...",
            "This might be the dumbest thing I've ever noticed...",
            "Hear me out...",
        ],
        "algorithm_status": "optimizing",
    }

    if not analytics_data or not analytics_data.get("channel_metrics"):
        # If private API not yet available, return structured baseline
        INTELLIGENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
        INTELLIGENCE_FILE.write_text(json.dumps(default_intelligence, indent=2), encoding="utf-8")
        return default_intelligence

    ch_metrics = analytics_data.get("channel_metrics", {})
    apv = float(ch_metrics.get("averageViewPercentage", 65.0))
    avd = float(ch_metrics.get("averageViewDuration", 18.0))

    intelligence = dict(default_intelligence)
    intelligence["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    intelligence["channel_apv"] = apv
    intelligence["channel_avd"] = avd

    # Self-Optimization Rule 1: Duration & Word Count Tuning based on Audience Retention
    if apv < 60.0:
        # If retention is low (<60%), shorten the videos to boost completion rate and loop potential
        intelligence["target_word_count_min"] = 35
        intelligence["target_word_count_max"] = 48
        intelligence["optimal_video_duration_range"] = [14, 20]
        intelligence["style_weights"]["chaotic"] = 0.45
        intelligence["style_weights"]["meme"] = 0.35
        intelligence["style_weights"]["story"] = 0.10
        intelligence["style_weights"]["npc"] = 0.10
    elif apv >= 75.0:
        # High retention (>75%): audience loves the story/dialogue depth
        intelligence["target_word_count_min"] = 45
        intelligence["target_word_count_max"] = 60
        intelligence["optimal_video_duration_range"] = [18, 28]
        intelligence["style_weights"]["chaotic"] = 0.30
        intelligence["style_weights"]["story"] = 0.35
        intelligence["style_weights"]["meme"] = 0.25
        intelligence["style_weights"]["npc"] = 0.10

    INTELLIGENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    INTELLIGENCE_FILE.write_text(json.dumps(intelligence, indent=2), encoding="utf-8")
    print(f"🧠 Intelligence updated and saved to {INTELLIGENCE_FILE}")
    return intelligence


def load_intelligence() -> dict:
    """
    Load current optimization intelligence config.
    """
    if INTELLIGENCE_FILE.exists():
        try:
            return json.loads(INTELLIGENCE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return compute_optimization_intelligence({})


def sync_and_optimize():
    """
    Main sync runner: queries YouTube Analytics and updates optimization intelligence.
    """
    print("=" * 60)
    print("📊 REAL-TIME YOUTUBE ANALYTICS & SELF-OPTIMIZATION ENGINE")
    print("=" * 60)
    data = fetch_private_analytics_report()
    intel = compute_optimization_intelligence(data)
    print("\n📈 Current Optimization Parameters:")
    print(f"   Target Words: {intel.get('target_word_count_min')} - {intel.get('target_word_count_max')} words")
    print(f"   Target Duration: {intel.get('optimal_video_duration_range')} seconds")
    print(f"   Style Probabilities: {intel.get('style_weights')}")
    print("=" * 60)
    return intel


if __name__ == "__main__":
    sync_and_optimize()
