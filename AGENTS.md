# Edionic — Multi-Agent Handoff & Project Status (`C:\ai editing`)

> **PROJECT STATUS: ALL PHASES 0 THROUGH 6 COMPLETED & QA VERIFIED**
> Every phase (Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, and Phase 6) has been built and verified end-to-end on real vertical renders (`1080x1920` and `2160x3840` 4K) in `C:\ai editing`.

---

## 1. Local Environment & Installed Tools (`C:\ai editing\tools`)
Always prepend these to `PATH` when running commands:
- **Python 3.11.9 (with `faster-whisper 1.2.1` installed):** `C:\ai editing\tools\python\python.exe`
- **FFmpeg & FFprobe 9.0.2:** `C:\ai editing\tools\ffmpeg\bin\ffmpeg.exe` and `ffprobe.exe`
- **Whisper Model Cache (`tiny` multilingual int8; override via `EDIONIC_WHISPER_MODEL`):** `C:\ai editing\tools\whisper_models`
- **Launcher Script:** `C:\ai editing\start_edionic.bat` (starts backend + UI on `http://127.0.0.1:8080`)

---

## 2. Completed & Verified Phases (0 through 6)

### ✅ Phase 0 — Setup & "Hello Render" (DONE & QA PASSED)
- `frontend/index.html`, `frontend/styles.css`, `frontend/app.js` — Strict Section 6 Design System (`#F4F5F7` bg, `#3B63FF` accent, Inter Tight + Anton fonts, all 7 navigation sections intact, `editor-job.json` exporter).
- `backend/server.py` — HTTP Server + Single-render-job-at-a-time queue worker.
- `backend/brain_router.py` — Pluggable AI Brain Router (`FreeLLMAPI` -> `OmniRoute` -> Local Ollama `llama3.2:3b` tuned for 8 GB RAM + local rules fallback).
- `projects/default/project.edl.json` — Default `.edl.json` project format (`V3`, `V2`, `V1`, `A1`, `CC` tracks + `overrides` layer).
- `backend/test_phase0_hello_render.py` — Verified 5s 9:16 `1080x1920` upload -> render -> download.

### ✅ Phase 1 — MVP (DONE & QA RULES 1–3 PASSED)
- `backend/pipeline_v3.py` — `faster-whisper` word-level transcription (`transcribe_with_word_timestamps`), automatic silence cutting (`detect_and_cut_silences`), face-anchored 9:16 speaker framing (`compute_face_anchored_crop`: eyes @ `32.5%`, headroom `8.0%`, chin unclipped @ `50.9%`).
- `backend/test_phase1_mvp.py` — Verified on real talking-head video (`talking_head_raw.mp4`).

### ✅ Phase 2 — SFX System + All 11 Caption Presets (DONE & 11/11 QA PASSED)
- `backend/sfx_system.py` + `sfx/catalog.json` + `sfx/*.wav` — All 10 royalty-free synthesized sounds (`whoosh`, `swoosh`, `swish`, `pop`, `snap`, `thump`, `click`, `ding`, `chime`, `riser`), exact-frame cut placement (`-12.0 dB` gain), and two-pass `-14.0 LUFS` loudness normalization.
- `backend/caption_presets.py` — All 11 verified presets (`glow`, `gradient_steps`, `extrude_3d`, `handwritten`, `neon_serif`, `condensed`, `pill_highlight`, `karaoke_pop`, `podcast_two_tier`, `minimal_clean`, `light_sweep_title`).
- `backend/slop_gate.py` — Frame-level caption size (`>= 54 px` @ 1080p, `>= 108 px` @ 4K), visual SHA-256 hash, motion frame-diff, face-anchored framing, and `-14 LUFS ±1.0` verifier.
- `backend/test_phase2_sfx_and_presets.py` & `projects/default/exports/phase2_presets/phase2_qa_report.json` — 11/11 presets passed with 11/11 unique visual fingerprints.

### ✅ Phase 3 — Style-Copy + Storyboard-First + Contact-Sheet QA (DONE & QA PASSED)
- `backend/learn_style.py` & `backend/style_copy.py` — Extracts `resolution`, `fps`, `duration`, `scene_count`, `avg_shot_length`, and top 5 hex `palette` from 1–5 reference videos; marks unmeasurable subjective fields (`caption_style`, `hook_style`, `pacing`) as `"unverified"`. Verified `smoke2_style` (`1080x1920`, `30.0` fps, `17.595s` avg shot, `#864027`..`#8E6039`).
- `styles/<style_id>/` (`smoke2_style`, `vox_explainer_style`, `neon_aura_style`, `learned_from_sample`) — Full modular style bundles (`style.json` + `base.js` + `style.md` + live `preview.html`).
- `backend/storyboard.py` — Storyboard JSON (`id`, `title`, `text`, `start`, `end`, `visual`, `graphic`, `sfx`) + one-page interactive HTML preview (`phase3_storyboard_preview.html`) + bidirectional round-trip (`roundtrip_storyboard_edits_to_edl`) into `.edl.json`.
- `backend/contact_sheet_qa.py` — Renders 3 stills per graphics span (`contact_sheet.png`), automatically inspecting for clipped/overlapping text, graphics covering the face, off-style colors, and wrong words. Verified 0 defects on clean render (`phase3_cs_clean/contact_sheet.png`) and caught all 36 planted still defects on the defective test render (`phase3_cs_planted_defect/contact_sheet_qa.json`).

### ✅ Phase 4 — Pipeline Consumes `editor-job.json` Directly (DONE & QA PASSED)
- `backend/pipeline_v3.py` (`run_editor_job_json` & `roundtrip_timeline_to_edl`) + `POST /api/render/job` — Consumes UI-exported `editor-job.json` (`caption_preset`, `title_text`, `style_preset`, `sfx`, `storyboard`) with zero manual steps and renders verified `1080x1920` output (`phase4_from_editor_job.mp4`).

### ✅ Phase 5 — OpenFilm Ideas & Determinism (DONE & QA PASSED)
- `backend/openfilm.py` — Pure function of time `frame(t, edl)` with cryptographic state hash (`frame_state_sha256`), `verify_look_double_draw` in shuffled draw order (100% identical state and RGB24 pixel hashes), `apply_overrides_and_locks` (`overrides.user_edits` + `locked_tracks` protection), and `trim_without_reencode` (`-c copy` lossless stream-copy trim in `0.05s`).
- `backend/slop_gate.py` — Enhanced with Phase 5 font-load, non-missing-audio, unclipped-text margin, and shuffled `look` double-draw checks.

### ✅ Phase 6 — Publishing Kit, 4K (`2160x3840`) Render, Timeline Round-Trip, B-Roll Hunter & Music Library (DONE & QA PASSED)
- `backend/broll_hunter.py` + `projects/default/broll/` — Automated motion-verified 9:16 B-Roll Hunter (`verify_broll_motion` rejects static clips; binds moving B-Roll to Track `V2`).
- `backend/music_library.py` + `music/catalog.json` + `music/*.wav` — 3 synthesized royalty-free background music beds (`upbeat_pulse`, `lo_fi_warmth`, `cinematic_drone`) ducked at `-22 dB` under voice while maintaining `-13.99 LUFS` (`-14.0 ±1.0 LUFS`) master loudness.
- `backend/pipeline_v3.py` — Verified `2160x3840` 4K vertical render (`phase6_final_4k_2160x3840.mp4`, caption glyph height `138 px >= 108 px`, `-13.99 LUFS`, Slop Gate PASS).
- `backend/publishing_kit.py` — Generates `publishing_kit.json`, `publishing_kit.md`, and `thumbnail_1080x1920.png` (titles, timestamped chapters, 12 hashtags, and branded-content/AI disclosure checklist).
- `backend/test_phase3_to_6_complete.py` & `projects/default/exports/phases_3_to_6_qa_report.json` — Full end-to-end verification suite passing Phases 3, 4, 5, and 6.

---

## 3. Batch 4 — Planner Reachability Fix + Ollama LLM Planner (branch `rocky/skills-templates`)

- **Planner-reachability fix:** the old hardcoded `b0`/`b1` placeholder storyboard blocks (frontend default + `normalize_storyboard` regeneration) made `job_has_manual_graphics()` return True on every default-UI render, so the Batch 3 motion planner never ran. Fixed: factory-default blocks are ignored by the planner check and stripped before planning; `normalize_storyboard` returns empty blocks for empty input; the frontend default storyboard is empty; `graphics.py` never renders placeholder ids/titles as on-screen text (no more "B1" pill over the face). Plan-generated clips/blocks (`v2_plan_*`, `plan_b*`) are likewise ignored + stripped, so consecutive renders on new videos always re-plan with fresh timings.
- **Graphics placement rule:** all mid-frame graphics (card sequences, proof cards, pills, lower-thirds, emphasis) render in the band y 995–1230 on the 1080×1920 grid — below the face (chin 50.9%) and above the two-tier caption keyword slot (y 1240). Never move them back over the face.
- **Ollama LLM planner (`backend/ollama_planner.py`):** transcript + word times → local Ollama `/api/chat` → strict-validated motion-plan JSON → the same V2-clip injection as the rules planner. Rules planner is the fallback (Ollama down/invalid/slow never fails a render); `render_info.motion_plan` reports `planner: "ollama"|"rules"` + model. Env vars (same names as `brain_router.py`): `EDIONIC_OLLAMA_URL` (default `http://127.0.0.1:11434`), `EDIONIC_OLLAMA_MODEL` (default `llama3.2:3b`; `qwen2.5:7b` on 16 GB RAM), `EDIONIC_OLLAMA_ENABLED`, `EDIONIC_OLLAMA_TIMEOUT` (default 180s). The PC must have Ollama running with the model pulled, or renders silently use the rules planner.
- **Still not rendered:** split-screen/grid layouts, V3 style grades, template pacing/music enforcement. Timeline UI is display-only (editable timeline is a separate batch).
- **Hotfix 4.2 (branch `rocky/skills-templates`):** the last two structural rejections from the Hotfix 4.1 real-model test are now repairs — extra card_sequences are dropped (first kept), and a drawn segment overlapping the card_sequence span is trimmed to end before it starts / start after it ends (dropped only when <0.5s would remain; end-trim preferred so a hook title_card at 0.0 stays a hook). Prompt now tells the model to merge all list speech into ONE card_sequence and to place pills/proof cards outside the card span. Still rejecting: unknown element type, missing text, malformed card payloads, missing hook title. Unit checks 12/12 pass; real-model re-test (llama3.2:3b, same transcript): attempt 1 VALID on the first try (124.1s, 5 repairs incl. a trimmed progress_bar and a dropped proof_card) and the separate raw sampling also valid — up from ~1 in 3 samplings in 4.1. Note: the model's card_sequence span ran 3.7–20.0s (whole video); that is the model's choice, not a validator issue.
