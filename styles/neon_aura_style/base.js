/**
 * Edionic Style Library Module — styles/neon_aura_style/base.js
 * Pure deterministic style configuration & frame(t) overlay descriptor.
 */

export const STYLE_CONFIG = {
  "style_id": "neon_aura_style",
  "name": "Neon Aura Studio",
  "reference_video_count": 1,
  "reference_videos": [
    "neon_ref.mp4"
  ],
  "resolution": "1080x1920",
  "fps": 30.0,
  "duration": 12.0,
  "scene_count": 3,
  "avg_shot_length": 4.0,
  "palette": [
    "#18181B",
    "#27272A",
    "#FF00FF",
    "#00FFFF",
    "#EF4444"
  ],
  "caption_style": "unverified",
  "hook_style": "unverified",
  "pacing": "unverified",
  "recommended_caption_preset": "neon_serif",
  "ffmpeg_grade_filter": "eq=contrast=1.08:saturation=1.14"
};

export function computeStyleLookAtTime(t, state = {}) {
  const normT = Math.max(0, Number(t) || 0);
  const pulse = 0.5 + 0.5 * Math.sin(normT * 2.0 * Math.PI * 0.5);
  return {
    style_id: "neon_aura_style",
    timestamp_s: Number(normT.toFixed(3)),
    primary_color: "#18181B",
    secondary_color: "#27272A",
    palette: ["#18181B", "#27272A", "#FF00FF", "#00FFFF", "#EF4444"],
    recommended_caption_preset: "neon_serif",
    vignette_opacity: Number((0.18 + 0.04 * pulse).toFixed(3)),
    safe_zone_9_16: { top_pct: 8.0, eyes_pct: 32.5, caption_y_range: [1280, 1650] }
  };
}

export default STYLE_CONFIG;
