# Edionic — Free, Local-First 9:16 AI Video Editor

> **Agent-First Vertical Video Studio** · Open-Source & Local-First  
> Powered by Whisper word-level transcription, FFmpeg, 11 ASS caption presets, and pluggable AI Brain (Local Ollama / Groq / Gemini / Built-in 10-Agent Crew).

---

## 🌟 Overview

**Edionic** is a 9:16 vertical video editor designed for short-form content creators (TikTok, Instagram Reels, YouTube Shorts). It combines a web-based timeline interface with a local-first Python backend and multi-agent AI brain that makes editing decisions directly onto a single source-of-truth timeline (`project.edl.json`).

### Key Capabilities
- 🚀 **3-Stage Workflow:** Landing Hub → Ready-Made / Custom 9:16 Style Creator → Multi-Track NLE Studio.
- 🗣️ **Whisper Word-Level Transcription:** High-accuracy timestamps via `faster-whisper`.
- ✂️ **Automatic Silence Cutting:** Detects and cuts dead-air silences (`-35 dB`) while preserving word boundaries.
- 🎨 **11 Verified Caption Presets:** `glow`, `gradient_steps`, `extrude_3d`, `handwritten`, `neon_serif`, `condensed`, `pill_highlight`, `karaoke_pop`, `podcast_two_tier`, `minimal_clean`, `light_sweep_title`.
- 🔊 **Royalty-Free SFX & Music:** Exact-frame cut placement, `-12 dB` gain, and `-14 LUFS` loudness normalization.
- 🎞️ **Multi-Track Timeline:** Track lanes (`V3` Adjustment, `V2` Overlay/B-Roll, `V1` Primary Video, `A1` Voice, `CC` Captions).
- 🧠 **Pluggable AI Brain:** 10-Agent Crew Engine supporting Roman Urdu & English natural language commands + Groq, Gemini & local Ollama (`llama3.2:3b`).

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.10+
- FFmpeg 6.0+ (with libass enabled)

### Run Locally
```bash
# Clone the repository
git clone https://github.com/<your-username>/edionic.git
cd edionic

# Install Python requirements
pip install faster-whisper==1.2.1

# Start Backend & Web UI
python backend/server.py
```
Open [http://127.0.0.1:8080](http://127.0.0.1:8080) in your browser.

---

## ☁️ 24/7 Cloud Deployment (Hugging Face Spaces / Docker)

Edionic includes a production-ready `Dockerfile` and `CLOUD_DEPLOY_24_7.md` guide for deploying to **Hugging Face Spaces (Free 16 GB RAM Docker tier)** or Railway/Render, so your studio runs 24/7 without needing your personal PC turned on.

```bash
docker build -t edionic-studio .
docker run -p 7860:7860 edionic-studio
```

---

## 📂 Project Structure

```
edionic/
├── backend/               # Python backend & Media Engine
│   ├── server.py          # Multi-threaded HTTP server & single-job render queue
│   ├── pipeline_v3.py     # FFmpeg render engine, Whisper transcription, silence cuts
│   ├── brain_router.py    # Pluggable AI Brain & 10-Specialist Agent Crew
│   ├── caption_presets.py # 11 ASS subtitle presets & styling
│   ├── sfx_system.py      # SFX library & -14 LUFS loudness normalizer
│   ├── broll_hunter.py    # Motion-verified 9:16 B-Roll hunter
│   └── slop_gate.py       # Quality assurance checks (caption size, framing, loudness)
├── frontend/              # Web Studio interface (HTML5, Clean CSS, Vanilla JS)
│   ├── index.html         # Landing Hub, Style Creator & Multi-Track Studio
│   ├── styles.css         # Responsive Dark / Light theme design system
│   └── app.js             # Studio logic, API client & real-time editor state
├── sfx/                   # 10 Synthesized royalty-free audio effects (.wav)
├── music/                 # Royalty-free background music beds
├── styles/                # Pre-built 9:16 style template bundles
├── Dockerfile             # Container configuration for 24/7 cloud hosting
└── CLOUD_DEPLOY_24_7.md   # Zero-cost cloud deployment guide
```

---

## 📄 License
MIT License. Created for the Edionic Community.
