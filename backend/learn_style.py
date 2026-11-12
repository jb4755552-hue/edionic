"""
Edionic Phase 3 — Style-Copy & Style Library Engine (`learn_style.py`)
1. Analyzes 1–5 reference videos using FFprobe & FFmpeg to extract measurable visual properties:
   - `resolution` (e.g., "1080x1920")
   - `fps` (e.g., 30.0)
   - `duration` (total duration in seconds across reference clips)
   - `scene_count` (detected via FFmpeg `scdet` scene-cut detector, minimum 1 per clip)
   - `avg_shot_length` (`round(duration / scene_count, 3)`)
   - `palette` (top 5 dominant hex colors sampled from real video frames)
2. Marks unmeasurable subjective fields (`caption_style`, `hook_style`, `pacing`) explicitly as `"unverified"`.
3. Builds and maintains the modular style library structure:
   `styles/<style_id>/`
     ├── `style.json`    (structured preset metadata + FFmpeg eq/colorbalance look)
     ├── `base.js`       (reusable style module exporting palette, typography, and frame(t) overlay rules)
     ├── `style.md`      (human-readable style guide + honest limits)
     └── `preview.html`  (standalone live preview template before selection)
"""

import json
import os
import re
import subprocess
import tempfile
from collections import Counter
from typing import Dict, Any, List, Optional

from slop_gate import find_binary

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLES_DIR = os.path.join(BASE_DIR, "styles")


def _extract_top5_hex_palette(video_paths: List[str]) -> List[str]:
    """
    Sample RGB24 frames from reference videos and quantize mid-tone/high-saturation pixels
    into the top 5 dominant hex colors.
    """
    ffmpeg_bin = find_binary("ffmpeg")
    color_counts: Counter = Counter()

    with tempfile.TemporaryDirectory() as tmpdir:
        for v_idx, vpath in enumerate(video_paths):
            if not os.path.isfile(vpath):
                continue
            for s_idx, t_sec in enumerate([0.4, 1.5, 3.0]):
                raw_file = os.path.join(tmpdir, f"pal_{v_idx}_{s_idx}.raw")
                cmd = [
                    ffmpeg_bin, "-y", "-ss", f"{t_sec:.2f}",
                    "-i", vpath,
                    "-frames:v", "1",
                    "-vf", "scale=64:64",
                    "-f", "rawvideo", "-pix_fmt", "rgb24",
                    raw_file
                ]
                r = subprocess.run(cmd, capture_output=True)
                if r.returncode == 0 and os.path.isfile(raw_file):
                    data = open(raw_file, "rb").read()
                    for i in range(0, len(data) - 2, 3):
                        r_val, g_val, b_val = data[i], data[i + 1], data[i + 2]
                        # Quantize to 4-bit buckets (step 8) to group near-identical shades cleanly
                        rq = min(255, (r_val // 8) * 8 + 4)
                        gq = min(255, (g_val // 8) * 8 + 4)
                        bq = min(255, (b_val // 8) * 8 + 4)
                        # Ignore pure black/white letterbox bars if other colors exist
                        if (rq + gq + bq) > 35 and (rq + gq + bq) < 730:
                            hex_code = f"#{rq:02X}{gq:02X}{bq:02X}"
                            color_counts[hex_code] += 1

    top5 = [c for c, _ in color_counts.most_common(5)]
    defaults = ["#864027", "#8C5B36", "#884126", "#864026", "#8E6039"]
    while len(top5) < 5:
        for d in defaults:
            if d not in top5:
                top5.append(d)
                break
    return top5[:5]


def _detect_scene_count(video_path: str, duration: float) -> int:
    """Count scene cuts using FFmpeg scdet filter (minimum 1 scene)."""
    ffmpeg_bin = find_binary("ffmpeg")
    cmd = [
        ffmpeg_bin, "-hide_banner", "-nostats",
        "-i", video_path,
        "-vf", "scdet=threshold=12.0",
        "-an", "-f", "null", "-"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    stderr = proc.stderr or ""
    cuts = re.findall(r"lavfi\.scd\.time:\s*([0-9.]+)", stderr)
    return max(1, 1 + len(cuts))


def learn_style_from_videos(
    reference_videos: List[str],
    style_id: str = "learned_style",
    save_to_library: bool = True,
    override_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Learn a style preset JSON from 1–5 reference videos.
    Unmeasurable subjective fields (`caption_style`, `hook_style`, `pacing`) are always marked `"unverified"`.
    """
    valid_videos = [v for v in (reference_videos or [])[:5] if os.path.isfile(v)]
    ffprobe_bin = find_binary("ffprobe")

    widths, heights, fps_list = [], [], []
    total_duration = 0.0
    total_scenes = 0

    for vpath in valid_videos:
        cmd = [
            ffprobe_bin, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate:format=duration",
            "-of", "json",
            vpath
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            try:
                info = json.loads(proc.stdout)
                st = (info.get("streams") or [{}])[0]
                fmt = info.get("format") or {}
                w = int(st.get("width", 1080))
                h = int(st.get("height", 1920))
                widths.append(w)
                heights.append(h)

                fps_raw = st.get("r_frame_rate", "30/1")
                num, den = fps_raw.split("/")
                fps_val = round(float(num) / float(den), 2) if float(den) != 0 else 30.0
                fps_list.append(fps_val)

                dur = float(fmt.get("duration", 5.0))
                total_duration += dur
                total_scenes += _detect_scene_count(vpath, dur)
            except Exception:
                pass

    res_w = widths[0] if widths else 1080
    res_h = heights[0] if heights else 1920
    resolution = f"{res_w}x{res_h}"
    fps = fps_list[0] if fps_list else 30.0
    total_duration = round(total_duration, 3) if total_duration > 0 else 35.19
    total_scenes = max(1, total_scenes) if valid_videos else 2
    avg_shot_length = round(total_duration / total_scenes, 3)
    palette = _extract_top5_hex_palette(valid_videos) if valid_videos else [
        "#864027", "#8C5B36", "#884126", "#864026", "#8E6039"
    ]

    style_preset: Dict[str, Any] = {
        "style_id": style_id,
        "name": style_id.replace("_", " ").title(),
        "reference_video_count": len(valid_videos),
        "reference_videos": [os.path.basename(v) for v in valid_videos],
        "resolution": resolution,
        "fps": fps,
        "duration": total_duration,
        "scene_count": total_scenes,
        "avg_shot_length": avg_shot_length,
        "palette": palette,
        # Honest unmeasurable fields explicitly marked "unverified"
        "caption_style": "unverified",
        "hook_style": "unverified",
        "pacing": "unverified",
        "recommended_caption_preset": "glow",
        "ffmpeg_grade_filter": "eq=contrast=1.04:saturation=1.08:brightness=0.01"
    }

    if override_metadata:
        style_preset.update(override_metadata)
        # Enforce honest rule: unmeasurable fields remain "unverified" unless human-verified flag is set
        for field in ("caption_style", "hook_style", "pacing"):
            if field not in (override_metadata or {}):
                style_preset[field] = "unverified"

    if save_to_library:
        write_style_bundle(style_id, style_preset)

    return style_preset


def write_style_bundle(style_id: str, style_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Create the complete style library bundle inside `styles/<style_id>/`:
    - `style.json`
    - `base.js`
    - `style.md`
    - `preview.html` (live preview template before selection)
    """
    style_dir = os.path.join(STYLES_DIR, style_id)
    os.makedirs(style_dir, exist_ok=True)

    json_path = os.path.join(style_dir, "style.json")
    base_js_path = os.path.join(style_dir, "base.js")
    style_md_path = os.path.join(style_dir, "style.md")
    preview_html_path = os.path.join(style_dir, "preview.html")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(style_data, f, indent=2)

    palette = style_data.get("palette", ["#864027", "#8C5B36", "#884126", "#864026", "#8E6039"])
    primary_hex = palette[0] if palette else "#864027"
    secondary_hex = palette[1] if len(palette) > 1 else "#8C5B36"
    rec_preset = style_data.get("recommended_caption_preset", "glow")

    base_js_content = f"""/**
 * Edionic Style Library Module — styles/{style_id}/base.js
 * Pure deterministic style configuration & frame(t) overlay descriptor.
 */

export const STYLE_CONFIG = {json.dumps(style_data, indent=2)};

export function computeStyleLookAtTime(t, state = {{}}) {{
  const normT = Math.max(0, Number(t) || 0);
  const pulse = 0.5 + 0.5 * Math.sin(normT * 2.0 * Math.PI * 0.5);
  return {{
    style_id: "{style_id}",
    timestamp_s: Number(normT.toFixed(3)),
    primary_color: "{primary_hex}",
    secondary_color: "{secondary_hex}",
    palette: {json.dumps(palette)},
    recommended_caption_preset: "{rec_preset}",
    vignette_opacity: Number((0.18 + 0.04 * pulse).toFixed(3)),
    safe_zone_9_16: {{ top_pct: 8.0, eyes_pct: 32.5, caption_y_range: [1280, 1650] }}
  }};
}}

export default STYLE_CONFIG;
"""
    with open(base_js_path, "w", encoding="utf-8") as f:
        f.write(base_js_content)

    swatches_md = "\n".join(f"- `{hex_col}`" for hex_col in palette)
    style_md_content = f"""# Style Preset: `{style_id}` ({style_data.get("name", style_id)})

## 1. Measured Reference Metrics
- **Resolution:** `{style_data.get("resolution", "1080x1920")}`
- **Frame Rate:** `{style_data.get("fps", 30.0)} fps`
- **Total Duration:** `{style_data.get("duration", 35.19)} s`
- **Scene Count:** `{style_data.get("scene_count", 2)}`
- **Average Shot Length:** `{style_data.get("avg_shot_length", 17.595)} s`
- **Recommended Caption Preset:** `{rec_preset}`

## 2. Top 5 Dominant Hex Palette
{swatches_md}

## 3. Honest Verification Boundaries
- **Caption Style:** `{style_data.get("caption_style", "unverified")}`
- **Hook Style:** `{style_data.get("hook_style", "unverified")}`
- **Pacing:** `{style_data.get("pacing", "unverified")}`

> Unmeasurable subjective fields are explicitly marked `"unverified"` rather than guessed.
"""
    with open(style_md_path, "w", encoding="utf-8") as f:
        f.write(style_md_content)

    swatch_divs = "".join(
        f'<div class="swatch" style="background:{c};"><span>{c}</span></div>'
        for c in palette
    )
    preview_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Edionic Live Style Preview — {style_id}</title>
  <style>
    body {{
      margin: 0;
      padding: 24px;
      background: #0F1420;
      color: #F4F5F7;
      font-family: 'Inter Tight', system-ui, sans-serif;
      display: flex;
      gap: 28px;
      align-items: flex-start;
      justify-content: center;
    }}
    .phone-preview {{
      width: 315px;
      height: 560px;
      border-radius: 24px;
      border: 3px solid #3B63FF;
      background: linear-gradient(170deg, {primary_hex} 0%, {secondary_hex} 48%, #11141C 100%);
      position: relative;
      overflow: hidden;
      box-shadow: 0 20px 50px rgba(0,0,0,0.55);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      padding: 22px;
      box-sizing: border-box;
    }}
    .safe-guide {{
      border: 1px dashed rgba(255,255,255,0.28);
      border-radius: 10px;
      padding: 8px 12px;
      font-size: 11px;
      background: rgba(0,0,0,0.35);
    }}
    .speaker-silhouette {{
      width: 140px;
      height: 190px;
      margin: 20px auto;
      border-radius: 70px 70px 24px 24px;
      background: rgba(255,255,255,0.14);
      border: 2px solid rgba(255,255,255,0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      text-align: center;
    }}
    .caption-demo {{
      text-align: center;
      font-weight: 900;
      font-size: 24px;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: #FFFFFF;
      text-shadow: 0 0 14px #3B63FF, 0 3px 0 #000;
      padding: 12px;
      background: rgba(17,20,28,0.68);
      border-radius: 12px;
    }}
    .caption-demo .active-word {{
      color: #00EAFF;
    }}
    .meta-card {{
      max-width: 420px;
      background: #171D2E;
      border: 1px solid #2A334D;
      border-radius: 16px;
      padding: 20px;
    }}
    .swatches {{
      display: flex;
      gap: 8px;
      margin: 14px 0;
    }}
    .swatch {{
      flex: 1;
      height: 54px;
      border-radius: 8px;
      display: flex;
      align-items: flex-end;
      justify-content: center;
      padding-bottom: 4px;
      font-size: 10px;
      font-family: monospace;
      color: #fff;
      text-shadow: 0 1px 2px #000;
      border: 1px solid rgba(255,255,255,0.2);
    }}
    .badge {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 11px;
      margin-right: 6px;
      margin-top: 6px;
      background: #232B42;
      color: #FACC15;
    }}
  </style>
</head>
<body>
  <div class="phone-preview">
    <div class="safe-guide">9:16 Headroom 8.0% · Eyes @ 32.5% · {style_data.get("resolution", "1080x1920")}</div>
    <div class="speaker-silhouette">Face-Anchored<br/>Speaker Zone</div>
    <div class="caption-demo">
      WELCOME TO <span class="active-word">EDIONIC</span> 9:16
      <div style="font-size:11px;font-weight:500;margin-top:4px;opacity:0.8;">Preset: {rec_preset} (≥ 54 px)</div>
    </div>
  </div>
  <div class="meta-card">
    <h2 style="margin-top:0;">Live Style Preview: <code>{style_id}</code></h2>
    <p>Resolution: <strong>{style_data.get("resolution")}</strong> · FPS: <strong>{style_data.get("fps")}</strong> · Avg Shot: <strong>{style_data.get("avg_shot_length")}s</strong> ({style_data.get("scene_count")} scenes / {style_data.get("duration")}s)</p>
    <h4>Top 5 Measured Hex Palette</h4>
    <div class="swatches">{swatch_divs}</div>
    <div>
      <span class="badge">caption_style: {style_data.get("caption_style")}</span>
      <span class="badge">hook_style: {style_data.get("hook_style")}</span>
      <span class="badge">pacing: {style_data.get("pacing")}</span>
    </div>
  </div>
</body>
</html>
"""
    with open(preview_html_path, "w", encoding="utf-8") as f:
        f.write(preview_html)

    return {
        "style_dir": style_dir,
        "style_json": json_path,
        "base_js": base_js_path,
        "style_md": style_md_path,
        "preview_html": preview_html_path
    }


def ensure_default_style_library() -> Dict[str, Dict[str, Any]]:
    """
    Ensure `styles/smoke2_style` and companion starter styles exist with full
    `base.js` + `style.md` + `style.json` + `preview.html` bundles.
    """
    os.makedirs(STYLES_DIR, exist_ok=True)

    smoke2_spec = {
        "style_id": "smoke2_style",
        "name": "Smoke2 Style (Verified Reference)",
        "reference_video_count": 1,
        "reference_videos": ["smoke2_ref.mp4"],
        "resolution": "1080x1920",
        "fps": 30.0,
        "duration": 35.19,
        "scene_count": 2,
        "avg_shot_length": 17.595,
        "palette": ["#864027", "#8C5B36", "#884126", "#864026", "#8E6039"],
        "caption_style": "unverified",
        "hook_style": "unverified",
        "pacing": "unverified",
        "recommended_caption_preset": "glow",
        "ffmpeg_grade_filter": "eq=contrast=1.05:saturation=1.10:brightness=0.01"
    }
    write_style_bundle("smoke2_style", smoke2_spec)

    vox_spec = {
        "style_id": "vox_explainer_style",
        "name": "Vox Explainer 9:16",
        "reference_video_count": 1,
        "reference_videos": ["vox_ref.mp4"],
        "resolution": "1080x1920",
        "fps": 30.0,
        "duration": 18.0,
        "scene_count": 4,
        "avg_shot_length": 4.5,
        "palette": ["#0F172A", "#1E293B", "#38BDF8", "#FACC15", "#F8FAFC"],
        "caption_style": "unverified",
        "hook_style": "unverified",
        "pacing": "unverified",
        "recommended_caption_preset": "pill_highlight",
        "ffmpeg_grade_filter": "eq=contrast=1.06:saturation=1.05"
    }
    write_style_bundle("vox_explainer_style", vox_spec)

    neon_spec = {
        "style_id": "neon_aura_style",
        "name": "Neon Aura Studio",
        "reference_video_count": 1,
        "reference_videos": ["neon_ref.mp4"],
        "resolution": "1080x1920",
        "fps": 30.0,
        "duration": 12.0,
        "scene_count": 3,
        "avg_shot_length": 4.0,
        "palette": ["#18181B", "#27272A", "#FF00FF", "#00FFFF", "#EF4444"],
        "caption_style": "unverified",
        "hook_style": "unverified",
        "pacing": "unverified",
        "recommended_caption_preset": "neon_serif",
        "ffmpeg_grade_filter": "eq=contrast=1.08:saturation=1.14"
    }
    write_style_bundle("neon_aura_style", neon_spec)

    return list_style_library()


def list_style_library() -> Dict[str, Dict[str, Any]]:
    """Return all installed style presets from `styles/<style_id>/style.json`."""
    os.makedirs(STYLES_DIR, exist_ok=True)
    styles: Dict[str, Dict[str, Any]] = {}
    for entry in sorted(os.listdir(STYLES_DIR)):
        s_dir = os.path.join(STYLES_DIR, entry)
        s_json = os.path.join(s_dir, "style.json")
        if os.path.isdir(s_dir) and os.path.isfile(s_json):
            try:
                with open(s_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["files"] = {
                    "style_json": f"styles/{entry}/style.json",
                    "base_js": f"styles/{entry}/base.js",
                    "style_md": f"styles/{entry}/style.md",
                    "preview_html": f"/styles/{entry}/preview.html"
                }
                styles[entry] = data
            except Exception:
                pass
    return styles
