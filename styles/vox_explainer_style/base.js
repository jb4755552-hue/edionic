/**
 * Edionic Style Library Module — styles/vox_explainer_style/base.js
 * Pure deterministic style configuration & frame(t) overlay descriptor.
 */

export const STYLE_CONFIG = {
  "style_id": "vox_explainer_style",
  "name": "Vox Explainer 9:16",
  "reference_video_count": 1,
  "reference_videos": [
    "vox_ref.mp4"
  ],
  "resolution": "1080x1920",
  "fps": 30.0,
  "duration": 18.0,
  "scene_count": 4,
  "avg_shot_length": 4.5,
  "palette": [
    "#0F172A",
    "#1E293B",
    "#38BDF8",
    "#FACC15",
    "#F8FAFC"
  ],
  "caption_style": "unverified",
  "hook_style": "unverified",
  "pacing": "unverified",
  "recommended_caption_preset": "pill_highlight",
  "ffmpeg_grade_filter": "eq=contrast=1.06:saturation=1.05"
};

export function computeStyleLookAtTime(t, state = {}) {
  const normT = Math.max(0, Number(t) || 0);
  const pulse = 0.5 + 0.5 * Math.sin(normT * 2.0 * Math.PI * 0.5);
  return {
    style_id: "vox_explainer_style",
    timestamp_s: Number(normT.toFixed(3)),
    primary_color: "#0F172A",
    secondary_color: "#1E293B",
    palette: ["#0F172A", "#1E293B", "#38BDF8", "#FACC15", "#F8FAFC"],
    recommended_caption_preset: "pill_highlight",
    vignette_opacity: Number((0.18 + 0.04 * pulse).toFixed(3)),
    safe_zone_9_16: { top_pct: 8.0, eyes_pct: 32.5, caption_y_range: [1280, 1650] }
  };
}

export default STYLE_CONFIG;
