/**
 * Edionic Style Library Module — styles/learned_from_sample/base.js
 * Pure deterministic style configuration & frame(t) overlay descriptor.
 */

export const STYLE_CONFIG = {
  "style_id": "learned_from_sample",
  "name": "Learned From Sample",
  "reference_video_count": 1,
  "reference_videos": [
    "talking_head_phase2_raw.mp4"
  ],
  "resolution": "1920x1080",
  "fps": 30.0,
  "duration": 13.112,
  "scene_count": 1,
  "avg_shot_length": 13.112,
  "palette": [
    "#1C2434",
    "#2C3444",
    "#E4B49C",
    "#242C44",
    "#ECBC9C"
  ],
  "caption_style": "unverified",
  "hook_style": "unverified",
  "pacing": "unverified",
  "recommended_caption_preset": "glow",
  "ffmpeg_grade_filter": "eq=contrast=1.04:saturation=1.08:brightness=0.01"
};

export function computeStyleLookAtTime(t, state = {}) {
  const normT = Math.max(0, Number(t) || 0);
  const pulse = 0.5 + 0.5 * Math.sin(normT * 2.0 * Math.PI * 0.5);
  return {
    style_id: "learned_from_sample",
    timestamp_s: Number(normT.toFixed(3)),
    primary_color: "#1C2434",
    secondary_color: "#2C3444",
    palette: ["#1C2434", "#2C3444", "#E4B49C", "#242C44", "#ECBC9C"],
    recommended_caption_preset: "glow",
    vignette_opacity: Number((0.18 + 0.04 * pulse).toFixed(3)),
    safe_zone_9_16: { top_pct: 8.0, eyes_pct: 32.5, caption_y_range: [1280, 1650] }
  };
}

export default STYLE_CONFIG;
