/**
 * Edionic Style Library Module — styles/software_walkthrough_style/base.js
 * Pure deterministic style configuration & frame(t) overlay descriptor.
 */

export const STYLE_CONFIG = {
  "style_id": "software_walkthrough_style",
  "name": "Software Walkthrough (Nafay 3D, adapted)",
  "reference_video_count": 0,
  "reference_videos": [],
  "resolution": "1080x1920",
  "fps": 30.0,
  "duration": 19.5,
  "scene_count": 1,
  "avg_shot_length": 19.5,
  "palette": [
    "#5B5BF6",
    "#14161C",
    "#1FB46E",
    "#FFD60A",
    "#F8F9FB"
  ],
  "caption_style": "DM Sans UI text; DM Mono caps for tiny labels",
  "hook_style": "Title card first: mono tag, big two-line title, step-count pill",
  "pacing": "3-5 seconds per step, never more than one new action at a time",
  "recommended_caption_preset": "minimal_clean",
  "ffmpeg_grade_filter": "eq=contrast=1.04:saturation=1.05",
  "family": "Screen and UI",
  "fonts": [
    "DM Sans 400-700",
    "DM Mono 500"
  ],
  "motion_language": "One continuous screen recording: an app window on a soft indigo-to-teal gradient desktop, a cursor moving along eased waypoints with click ripples, camera zooming 1.2x-1.6x toward the control in use. Spotlight dims everything except a yellow-edged cutout. Numbered step pill at the bottom left; result ends on a dark lower third with a green check.",
  "sound_map": {
    "cursor_click": "click",
    "modals_menus": "pop",
    "typing": "click",
    "camera_zoom": "swish",
    "step_pill": "ding",
    "toggle": "swish",
    "toast_result": "chime",
    "panel_slide": "whoosh"
  },
  "adapted_from": "Nafay 3D ai-video-editor skill style: software-walkthrough",
  "adaptation_note": "Adapted from the Nafay 3D ai-video-editor skill style definition (colors, typography, motion language). Metrics are the skill's demo values, not measured from a reference video. The skill's 16:9-only limit does not apply: this bundle is Edionic-native 9:16."
};

export function computeStyleLookAtTime(t, state = {}) {
  const normT = Math.max(0, Number(t) || 0);
  const pulse = 0.5 + 0.5 * Math.sin(normT * 2.0 * Math.PI * 0.5);
  return {
    style_id: "software_walkthrough_style",
    timestamp_s: Number(normT.toFixed(3)),
    primary_color: "#5B5BF6",
    secondary_color: "#14161C",
    palette: ["#5B5BF6", "#14161C", "#1FB46E", "#FFD60A", "#F8F9FB"],
    recommended_caption_preset: "minimal_clean",
    vignette_opacity: Number((0.18 + 0.04 * pulse).toFixed(3)),
    safe_zone_9_16: { top_pct: 8.0, eyes_pct: 32.5, caption_y_range: [1280, 1650] }
  };
}

export default STYLE_CONFIG;
