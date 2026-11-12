---
title: Edionic 9:16 AI Video Studio
emoji: 🎬
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Edionic — 24/7 Cloud & Local-First 9:16 AI Video Editor (`edionic.com`)

## How to Run 24/7 in the Cloud (Without Keeping Your PC On — $0 Cost)

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) and click **Create new Space**.
2. Name it `edionic-studio`, select **Docker** (Blank), and choose the **Free CPU Basic (2 vCPU · 16 GB RAM)** hardware tier (100% Free, no credit card needed).
3. Upload or `git push` this folder (`Dockerfile`, `frontend/`, `backend/`, `sfx/`, `projects/`).
4. *(Optional)* In Space **Settings → Variables and secrets**, add:
   - `GROQ_API_KEY` (Free from `console.groq.com`) or `GEMINI_API_KEY` (Free from `aistudio.google.com`).
   - Even without any keys, Edionic's built-in **10-Agent Bilingual Crew Engine** works automatically!
5. Your Edionic Studio will stay online 24/7 even when your PC is turned off.
