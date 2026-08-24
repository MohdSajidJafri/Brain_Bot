# GTA V Brainrot Shorts Automation Pipeline 🎮🚀

A fully automated, self-optimizing Python pipeline that creates and publishes viral **GTA V Brainrot Shorts** to YouTube Shorts and Instagram Reels.

The pipeline integrates real-time **YouTube Analytics API feedback**, AI script generation via Groq reasoning models, natural TTS synthesis via Edge TTS, kinetic subtitle rendering via FFmpeg, and round-robin gameplay clip rotation.

---

## 🌟 Key Features

1. **Self-Optimizing Analytics Loop (`analytics_optimizer.py`):** Automatically connects to the private YouTube Analytics API (v2), ingests Average Percentage Viewed (APV) and Average View Duration (AVD), and dynamically adjusts script length, video duration, and style probabilities to maximize audience retention.
2. **AI Script Generation (`generate_script.py`):** Uses `openai/gpt-oss-20b` with token-optimized prompting, zero-emoji spoken text protection, definitive punchlines, and 12 unhinged brainrot format categories.
3. **Gameplay Scene Pool & Anti-Duplication (`process_clips.py`):** Holds up to 100 sliced gameplay scenes in `data/clips/` and tracks usage history via `used_clips.json` to guarantee non-repeating backgrounds.
4. **Channel Algorithm Diagnostics (`diagnose_channel.py`):** One-click audits of all uploaded videos, title duplicates, view distribution, and algorithm health.
5. **Kinetic Caption Video Rendering (`render_short.py`):** High-retention 9:16 vertical MP4 video with synced kinetic subtitles, dynamic styling, and loudness-normalized audio.
6. **Automated Publishing & Paced Cadence (`daily_brainrot.yml`):** Runs 2x daily at peak viewing hours (1:30 PM & 7:30 PM IST / 08:00 & 14:00 UTC) via GitHub Actions.

---

## 🛠️ Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in your credentials:

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq LLM API Key |
| `GROQ_MODEL` | Optional | Default: `openai/gpt-oss-20b` |
| `YT_CLIENT_ID` | For YouTube | Google Cloud OAuth Client ID |
| `YT_CLIENT_SECRET_VALUE` | For YouTube | Google Cloud OAuth Client Secret |
| `YT_REFRESH_TOKEN` | For YouTube | YouTube OAuth Master Refresh Token |
| `IG_USERNAME` | For Instagram | Instagram account username |
| `IG_PASSWORD` | For Instagram | Instagram account password |

### Generating YouTube OAuth & Analytics Tokens
To generate your master refresh token with Upload, Readonly, and Analytics scopes:
```bash
python get_refresh_token.py
```

---

## 🚀 Usage

### 1. Full Pipeline (One-Shot with Auto-Optimization)
```bash
python run_pipeline.py
```

### 2. Channel Performance & Algorithm Diagnostic
```bash
python diagnose_channel.py --channel "@YourChannelHandle"
```

### 3. Analytics Self-Optimization Engine
```bash
python analytics_optimizer.py
```

### 4. Individual Component Commands
```bash
python download_clips.py --count 10 --query "gta 5 funny moments 1080p"  # Download raw gameplay
python process_clips.py                                                # Slice into 15-40s scenes
python generate_script.py --style chaotic                              # AI script generation
python generate_voiceover.py --text "Sample narration text"            # TTS audio synthesis
python render_short.py                                                 # Render video + kinetic ASS captions
python upload_youtube.py                                               # Upload directly to YouTube Shorts
```