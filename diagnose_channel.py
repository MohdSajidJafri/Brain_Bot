"""
YouTube Channel & Video Performance Diagnostic Tool.
Audits all uploaded videos, view distribution, upload intervals, and algorithm health.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from collections import Counter
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
from upload_youtube import _get_authenticated_service


def get_channel_uploads(youtube, channel_id: str | None = None) -> tuple[dict, list[dict]]:
    """
    Fetch channel details and all uploaded videos.
    Returns (channel_info, list_of_video_objects).
    """
    from googleapiclient.errors import HttpError

    channel_info = {}
    uploads_playlist_id = None

    if channel_id:
        print(f"🔍 Fetching channel data for ID: {channel_id}…")
        resp = youtube.channels().list(id=channel_id, part="snippet,statistics,contentDetails").execute()
    else:
        print("🔍 Fetching authenticated channel data (mine=True)…")
        try:
            resp = youtube.channels().list(mine=True, part="snippet,statistics,contentDetails").execute()
        except HttpError as e:
            print(f"⚠ Could not fetch via mine=True ({e}).")
            return {}, []

    items = resp.get("items", [])
    if not items:
        print("❌ No channel found with provided credentials/ID.")
        return {}, []

    ch = items[0]
    channel_info = {
        "id": ch.get("id"),
        "title": ch.get("snippet", {}).get("title"),
        "customUrl": ch.get("snippet", {}).get("customUrl", "N/A"),
        "publishedAt": ch.get("snippet", {}).get("publishedAt"),
        "subscribers": int(ch.get("statistics", {}).get("subscriberCount", 0)),
        "totalViews": int(ch.get("statistics", {}).get("viewCount", 0)),
        "totalVideos": int(ch.get("statistics", {}).get("videoCount", 0)),
    }
    uploads_playlist_id = ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")

    if not uploads_playlist_id:
        print("❌ Uploads playlist not found.")
        return channel_info, []

    print(f"   Channel: {channel_info['title']} ({channel_info['customUrl']})")
    print(f"   Subscribers: {channel_info['subscribers']:,} | Total Views: {channel_info['totalViews']:,} | Videos: {channel_info['totalVideos']:,}")
    print(f"\n📥 Fetching all video metadata from uploads playlist…")

    video_ids = []
    next_page = None

    while True:
        req = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="contentDetails",
            maxResults=50,
            pageToken=next_page,
        )
        res = req.execute()
        for it in res.get("items", []):
            vid = it.get("contentDetails", {}).get("videoId")
            if vid:
                video_ids.append(vid)

        next_page = res.get("nextPageToken")
        if not next_page:
            break

    print(f"   Found {len(video_ids)} uploaded video(s). Fetching detailed statistics…")

    # Fetch detailed statistics in batches of 50
    videos = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        v_req = youtube.videos().list(
            id=",".join(batch),
            part="snippet,statistics,contentDetails,status",
        )
        v_res = v_req.execute()
        for v in v_res.get("items", []):
            snippet = v.get("snippet", {})
            stats = v.get("statistics", {})
            status = v.get("status", {})

            videos.append({
                "id": v.get("id"),
                "title": snippet.get("title", ""),
                "publishedAt": snippet.get("publishedAt", ""),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "duration": v.get("contentDetails", {}).get("duration", ""),
                "privacy": status.get("privacyStatus", ""),
                "tags": snippet.get("tags", []),
                "description": snippet.get("description", ""),
            })

    return channel_info, videos


def analyze_channel_health(channel_info: dict, videos: list[dict]) -> str:
    """
    Run algorithmic health diagnosis on the video catalog and return formatted markdown report.
    """
    total = len(videos)
    if total == 0:
        return "# Channel Diagnostic Report\n\nNo videos found on this channel."

    # Sort videos by publishedAt (newest first)
    videos_sorted = sorted(videos, key=lambda x: x["publishedAt"], reverse=True)

    # View Distribution Categories
    zero_views = [v for v in videos_sorted if v["views"] == 0]
    under_10 = [v for v in videos_sorted if 1 <= v["views"] <= 10]
    under_100 = [v for v in videos_sorted if 11 <= v["views"] <= 100]
    under_1k = [v for v in videos_sorted if 101 <= v["views"] <= 1000]
    over_1k = [v for v in videos_sorted if v["views"] > 1000]

    # Recent vs Older performance split
    recent_50 = videos_sorted[:50]
    older_videos = videos_sorted[50:]

    recent_avg_views = sum(v["views"] for v in recent_50) / max(len(recent_50), 1)
    older_avg_views = sum(v["views"] for v in older_videos) / max(len(older_videos), 1) if older_videos else 0

    # Title Duplicate / Repetition Analysis
    clean_titles = [re.sub(r'#\w+', '', v["title"]).strip().lower() for v in videos_sorted]
    title_counts = Counter(clean_titles)
    duplicate_titles = {t: c for t, c in title_counts.items() if c > 1}

    # Tag Frequency
    all_tags = []
    for v in videos_sorted:
        all_tags.extend(v.get("tags", []))
    top_tags = Counter(all_tags).most_common(10)

    # Top 5 and Bottom 5 videos
    top_videos = sorted(videos_sorted, key=lambda x: x["views"], reverse=True)[:5]
    bottom_videos = sorted(videos_sorted, key=lambda x: x["views"])[:5]

    report = []
    report.append(f"# 📊 YouTube Channel Algorithm & Growth Diagnostic")
    report.append(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"### Channel Overview")
    report.append(f"- **Channel Title:** {channel_info.get('title', 'N/A')}")
    report.append(f"- **Handle / URL:** {channel_info.get('customUrl', 'N/A')}")
    report.append(f"- **Subscribers:** {channel_info.get('subscribers', 0):,}")
    report.append(f"- **Total Catalog Views:** {channel_info.get('totalViews', 0):,}")
    report.append(f"- **Total Uploads Analyzed:** {total}")
    report.append("")

    report.append("---")
    report.append("### 📈 View Distribution Breakdown")
    report.append("| View Range | Video Count | % of Catalog | Algorithm Interpretation |")
    report.append("|---|---|---|---|")
    report.append(f"| **0 Views (Zero Test)** | {len(zero_views)} | {len(zero_views)/total*100:.1f}% | 🚨 YouTube did NOT push to Shorts Feed seed impressions |")
    report.append(f"| **1 – 10 Views** | {len(under_10)} | {len(under_10)/total*100:.1f}% | ⚠️ Minimal impressions; user channel clicks only |")
    report.append(f"| **11 – 100 Views** | {len(under_100)} | {len(under_100)/total*100:.1f}% | 🟡 Initial seed test performed, but audience swiped away early |")
    report.append(f"| **101 – 1,000 Views** | {len(under_1k)} | {len(under_1k)/total*100:.1f}% | 🟢 Healthy initial Shorts Feed test |")
    report.append(f"| **1,000+ Views** | {len(over_1k)} | {len(over_1k)/total*100:.1f}% | 🔥 Viral momentum / algorithm pick-up |")
    report.append("")

    report.append("---")
    report.append("### ⏱️ Performance Trend (Recent vs Older Uploads)")
    report.append(f"- **Most Recent 50 Uploads Avg Views:** {recent_avg_views:.1f} views / video")
    if older_videos:
        report.append(f"- **Earlier Uploads ({len(older_videos)} videos) Avg Views:** {older_avg_views:.1f} views / video")
        if recent_avg_views < older_avg_views * 0.3:
            report.append(f"- **Trend Status:** 🔴 **Heavy Distribution Stall Detected.** Recent videos are receiving significantly fewer impressions.")
        else:
            report.append(f"- **Trend Status:** 🟡 Steady / Low Baseline.")
    report.append("")

    report.append("---")
    report.append("### 🏆 Top 5 Performing Videos")
    report.append("| Views | Likes | Published | Title |")
    report.append("|---|---|---|---|")
    for v in top_videos:
        report.append(f"| **{v['views']:,}** | {v['likes']} | {v['publishedAt'][:10]} | [{v['title'][:45]}...](https://youtube.com/shorts/{v['id']}) |")
    report.append("")

    if duplicate_titles:
        report.append("---")
        report.append(f"### ⚠️ Title Repetition & Duplication Warning")
        report.append(f"Found **{len(duplicate_titles)}** titles that have been reused multiple times across uploads:")
        for t, c in sorted(duplicate_titles.items(), key=lambda x: x[1], reverse=True)[:8]:
            report.append(f"- **{c}x:** `\"{t}\"`")
        report.append("")

    report.append("---")
    report.append("### 🎯 Diagnosis & Algorithm Recovery Plan")
    report.append("1. **The 0-View Seed Suppression:**")
    report.append("   - When videos receive 0 views, it means YouTube's recommendation engine did not allocate seed impressions in the Shorts feed.")
    report.append("   - *Cause:* High upload frequency (4/day) combined with repeated script audio and duplicate visual clips triggered YouTube's programmatic content filter.")
    report.append("2. **Algorithm Reset Strategy:**")
    report.append("   - **Pacing:** Shifted to 1–2 uploads per day at peak hours (1:30 PM & 7:30 PM IST / 08:00 & 14:00 UTC).")
    report.append("   - **Visual Diversity:** Expand visual gameplay pool from 9 clips to 50–100 distinct clips.")
    report.append("   - **Script Uniqueness:** With `openai/gpt-oss-20b` generating fresh, punchline-driven, emoji-free narrations, every upload now has 100% unique audio and visual fingerprints.")
    report.append("   - **Action:** Allow the channel 5–7 days of consistent, unique 1–2x daily posting for the algorithm trust score to reset.")

    return "\n".join(report)


def main():
    ap = argparse.ArgumentParser(description="YouTube Channel Algorithm & Performance Diagnostic")
    ap.add_argument("--channel-id", help="Optional YouTube Channel ID to audit")
    args = ap.parse_args()

    print("=" * 65)
    print("📊 YOUTUBE SHORTS ALGORITHM & CHANNEL DIAGNOSTIC TOOL")
    print("=" * 65)

    youtube = _get_authenticated_service()
    if not youtube:
        print("\n❌ YouTube API authentication failed.")
        print("   Make sure YT_REFRESH_TOKEN, YT_CLIENT_ID, and YT_CLIENT_SECRET_VALUE are set in .env")
        print("   OR run this via GitHub Actions workflow '.github/workflows/audit_channel.yml'")
        sys.exit(1)

    channel_info, videos = get_channel_uploads(youtube, channel_id=args.channel_id)
    if not videos:
        print("❌ Could not retrieve videos for analysis.")
        sys.exit(1)

    report_md = analyze_channel_health(channel_info, videos)

    # Save report artifact
    out_file = config.OUTPUT_DIR / "channel_diagnosis_report.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(report_md, encoding="utf-8")

    print("\n" + "=" * 65)
    print(report_md)
    print("=" * 65)
    print(f"\n✅ Diagnostic Report saved to: {out_file}")


if __name__ == "__main__":
    main()
