/**
 * Edionic Style Library Module — styles/smoke2_style/base.js
 * Pure deterministic style configuration & frame(t) overlay descriptor.
 */

export const STYLE_CONFIG = {
  "style_id": "smoke2_style",
  "name": "Smoke2 Style (Verified Reference)",
  "reference_video_count": 1,
  "reference_videos": [
    "smoke2_ref.mp4"
  ],
  "resolution": "1080x1920",
  "fps": 30.0,
  "duration": 35.19,
  "scene_count": 2,
  "avg_shot_length": 17.595,
  "palette": [
    "#864027",
    "#8C5B36",
    "#884126",
    "#864026",
    "#8E6039"
  ],
  "caption_style": "unverified",
  "hook_style": "unverified",
  "pacing": "unverified",
  "recommended_caption_preset": "glow",
  "ffmpeg_grade_filter": "eq=contrast=1.05:saturation=1.10:brightness=0.01"
};

export function computeStyleLookAtTime(t, state = {}) {
  const normT = Math.max(0, Number(t) || 0);
  const pulse = 0.5 + 0.5 * Math.sin(normT * 2.0 * Math.PI * 0.5);
  return {
    style_id: "smoke2_style",
    timestamp_s: Number(normT.toFixed(3)),
    primary_color: "#864027",
    secondary_color: "#8C5B36",
    palette: ["#864027", "#8C5B36", "#884126", "#864026", "#8E6039"],
    recommended_caption_preset: "glow",
    vignette_opacity: Number((0.18 + 0.04 * pulse).toFixed(3)),
    safe_zone_9_16: { top_pct: 8.0, eyes_pct: 32.5, caption_y_range: [1280, 1650] }
  };
}

export default STYLE_CONFIG;
