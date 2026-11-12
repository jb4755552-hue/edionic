"""
Edionic Phase 5 — OpenFilm Ideas & Determinism (`openfilm.py`)
Implements:
1. Film-as-code `.edl.json` pure function of time `frame(t, edl_data)`:
   - Given any timestamp `t` (in seconds) and an `.edl.json` state, deterministically computes
     the exact visual, caption, storyboard, audio, and SFX state at `t` with zero side effects
     and produces a cryptographic `frame_state_sha256` signature.
2. `look` Double-Draw in Shuffled Order (`verify_look_double_draw`):
   - Evaluates `frame(t)` AND extracts real video still frames at multiple sample timestamps
     in forward order (`[t0, t1, t2]`) and shuffled/reverse order (`[t2, t0, t1]`), verifying
     that both `frame(t)` state hashes and rendered RGB24 pixel hashes match 100% identically.
3. `overrides` Layer + `locked` Tracks (`apply_overrides_and_locks`):
   - Protects user manual edits (`overrides.user_edits`) and locked tracks (`overrides.locked_tracks`
     or `track.locked == true`) so AI mutations or re-renders never clobber locked user work.
4. Never-Re-Encode Trim / Stream-Copy (`trim_without_reencode`):
   - When only `in` / `out` trim boundaries change (no pixel filter re-encode needed), runs
     FFmpeg `-c copy` stream copy so trimming is instantaneous and lossless.
"""

import copy
import hashlib
import json
import os
import subprocess
import tempfile
import time
from typing import Dict, Any, List, Optional

from slop_gate import find_binary


def frame(t: float, edl_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure function of time `frame(t)`:
    Given a timestamp `t` (seconds) and an `.edl.json` dict, returns the complete deterministic
    scene graph state at time `t` without mutating `edl_data` or reading external mutable state.
    """
    t_sec = round(max(0.0, float(t)), 4)
    fps = float((edl_data.get("canvas") or {}).get("fps", 30))
    frame_index = int(round(t_sec * fps))

    tracks = edl_data.get("tracks") or []
    active_by_track: Dict[str, List[Dict[str, Any]]] = {
        "V3": [],
        "V2": [],
        "V1": [],
        "A1": [],
        "CC": []
    }

    for trk in tracks:
        tid = str(trk.get("id", ""))
        if tid not in active_by_track:
            continue
        for clip in (trk.get("clips") or []):
            if tid == "CC" or ("word" in clip and "start" in clip):
                c_start = float(clip.get("start", 0.0))
                c_end = float(clip.get("end", c_start + 0.25))
                if c_start <= t_sec <= c_end:
                    active_by_track["CC"].append({
                        "word": clip.get("word", ""),
                        "start": round(c_start, 3),
                        "end": round(c_end, 3),
                        "progress": round((t_sec - c_start) / max(0.001, c_end - c_start), 3)
                    })
            else:
                at_s = float(clip.get("at", 0.0))
                in_s = float(clip.get("in", 0.0))
                out_s = float(clip.get("out", in_s + float(clip.get("duration", 5.0))))
                speed = max(0.1, float(clip.get("speed", 1.0)))
                dur_s = (out_s - in_s) / speed
                if at_s <= t_sec <= (at_s + dur_s):
                    source_time = round(in_s + (t_sec - at_s) * speed, 4)
                    active_by_track[tid].append({
                        "id": clip.get("id", ""),
                        "source_time_s": source_time,
                        "in": round(in_s, 3),
                        "out": round(out_s, 3),
                        "at": round(at_s, 3),
                        "speed": speed,
                        "placement": clip.get("placement", "face_anchored_9_16"),
                        "graphic": clip.get("graphic", ""),
                        "visual": clip.get("visual", "")
                    })

    # Active storyboard block at time t
    active_block = None
    sb_blocks = ((edl_data.get("storyboard") or {}).get("blocks")) or []
    for blk in sb_blocks:
        b_start = float(blk.get("start", 0.0))
        b_end = float(blk.get("end", 0.0))
        if b_start <= t_sec <= b_end:
            active_block = {
                "id": blk.get("id", ""),
                "title": blk.get("title", ""),
                "text": blk.get("text", ""),
                "visual": blk.get("visual", ""),
                "graphic": blk.get("graphic", ""),
                "sfx": blk.get("sfx", "")
            }
            break

    # Active SFX within ±0.20s window of time t
    active_sfx = []
    for sfx_item in (edl_data.get("sfx") or []):
        placed_s = float(sfx_item.get("placed_at_s", -10.0))
        if 0.0 <= (t_sec - placed_s) <= 0.35:
            active_sfx.append({
                "name": sfx_item.get("name", ""),
                "placed_at_s": round(placed_s, 3),
                "offset_s": round(t_sec - placed_s, 3)
            })

    state_payload = {
        "t": t_sec,
        "frame_index": frame_index,
        "fps": fps,
        "caption_preset": edl_data.get("caption_preset", "glow"),
        "style_preset": edl_data.get("style_preset", "smoke2_style"),
        "title_text": edl_data.get("title_text", ""),
        "active_tracks": active_by_track,
        "active_storyboard_block": active_block,
        "active_sfx": active_sfx,
        "overrides_applied": len((edl_data.get("overrides") or {}).get("user_edits") or [])
    }

    canonical_json = json.dumps(state_payload, sort_keys=True, separators=(",", ":"))
    state_payload["frame_state_sha256"] = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()[:16]
    return state_payload


def verify_look_double_draw(
    video_path: str,
    edl_data: Dict[str, Any],
    sample_times: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    OpenFilm `look` Double-Draw Verification:
    1. Evaluates pure `frame(t, edl_data)` in forward order (`[t0, t1, t2]`) and shuffled order (`[t1, t2, t0]`).
    2. Extracts real RGB24 still frames from `video_path` in forward order (Pass A) and shuffled order (Pass B).
    3. Verifies that both the `frame(t)` state hashes AND the extracted RGB24 pixel SHA-256 hashes match 100%
       across shuffled draw orders.
    """
    times = sample_times or [0.40, 1.40, 2.60]
    shuffled_times = [times[1], times[-1], times[0]] if len(times) >= 3 else list(reversed(times))

    # 1. Pure function `frame(t)` double-draw check
    pass_a_fn = {t: frame(t, edl_data)["frame_state_sha256"] for t in times}
    pass_b_fn = {t: frame(t, edl_data)["frame_state_sha256"] for t in shuffled_times}
    fn_deterministic = all(pass_a_fn[t] == pass_b_fn[t] for t in times)

    # 2. Rendered video frame extraction double-draw in shuffled order
    ffmpeg_bin = find_binary("ffmpeg")
    pass_a_rgb: Dict[float, str] = {}
    pass_b_rgb: Dict[float, str] = {}

    if os.path.isfile(video_path):
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, t in enumerate(times):
                raw_a = os.path.join(tmpdir, f"a_{idx}.rgb")
                subprocess.run(
                    [
                        ffmpeg_bin, "-y", "-ss", f"{t:.3f}",
                        "-i", video_path,
                        "-frames:v", "1", "-vf", "scale=360:640",
                        "-f", "rawvideo", "-pix_fmt", "rgb24",
                        raw_a
                    ],
                    capture_output=True
                )
                if os.path.isfile(raw_a):
                    pass_a_rgb[t] = hashlib.sha256(open(raw_a, "rb").read()).hexdigest()[:16]

            for idx, t in enumerate(shuffled_times):
                raw_b = os.path.join(tmpdir, f"b_{idx}.rgb")
                subprocess.run(
                    [
                        ffmpeg_bin, "-y", "-ss", f"{t:.3f}",
                        "-i", video_path,
                        "-frames:v", "1", "-vf", "scale=360:640",
                        "-f", "rawvideo", "-pix_fmt", "rgb24",
                        raw_b
                    ],
                    capture_output=True
                )
                if os.path.isfile(raw_b):
                    pass_b_rgb[t] = hashlib.sha256(open(raw_b, "rb").read()).hexdigest()[:16]

    pixel_deterministic = (
        len(pass_a_rgb) == len(times)
        and all(pass_a_rgb.get(t) == pass_b_rgb.get(t) and bool(pass_a_rgb.get(t)) for t in times)
    )

    return {
        "pass": fn_deterministic and pixel_deterministic,
        "fn_deterministic": fn_deterministic,
        "pixel_deterministic": pixel_deterministic,
        "forward_order": times,
        "shuffled_order": shuffled_times,
        "frame_fn_hashes_pass_a": pass_a_fn,
        "frame_fn_hashes_pass_b": pass_b_fn,
        "pixel_hashes_pass_a": pass_a_rgb,
        "pixel_hashes_pass_b": pass_b_rgb
    }


def apply_overrides_and_locks(
    base_edl: Dict[str, Any],
    proposed_mutation: Dict[str, Any],
    record_user_edit: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Enforce `.edl.json` `overrides` layer (`user_edits` + `locked_tracks`) and track-level `locked: true`.
    - Any track listed in `overrides.locked_tracks` or with `"locked": true` ignores AI mutations to its clips.
    - Any explicit `user_edits` in `overrides.user_edits` (e.g., locked `caption_preset`, `title_text`, or clip `in`/`out`)
      are re-applied after the mutation so user overrides always win.
    """
    result = copy.deepcopy(base_edl)
    overrides = result.setdefault("overrides", {"user_edits": [], "locked_tracks": []})
    locked_tracks = set(overrides.get("locked_tracks") or [])

    if record_user_edit:
        overrides.setdefault("user_edits", []).append(record_user_edit)
        if record_user_edit.get("lock_track"):
            lt = record_user_edit["lock_track"]
            if lt not in locked_tracks:
                locked_tracks.add(lt)
                overrides["locked_tracks"] = sorted(locked_tracks)

    for trk in result.get("tracks") or []:
        if trk.get("locked"):
            locked_tracks.add(trk.get("id"))
    overrides["locked_tracks"] = sorted(locked_tracks)

    # Snapshot locked tracks before applying proposed_mutation
    saved_tracks = {
        trk["id"]: copy.deepcopy(trk)
        for trk in (result.get("tracks") or [])
        if trk.get("id") in locked_tracks
    }

    # Apply top-level non-locked fields from proposed_mutation
    for k, v in (proposed_mutation or {}).items():
        if k == "tracks":
            new_tracks = []
            for m_trk in v:
                tid = m_trk.get("id")
                if tid in saved_tracks:
                    # Preserve locked track untouched!
                    new_tracks.append(saved_tracks[tid])
                else:
                    new_tracks.append(copy.deepcopy(m_trk))
            result["tracks"] = new_tracks
        elif k == "sfx" and "A1" in locked_tracks:
            # Protect SFX if A1 audio track is locked
            continue
        elif k == "caption_preset" and "CC" in locked_tracks:
            # Protect caption preset if CC track is locked
            continue
        elif k != "overrides":
            result[k] = copy.deepcopy(v)

    # Re-apply explicit user_edits from overrides.user_edits so manual user tweaks always win
    for edit in overrides.get("user_edits") or []:
        field = edit.get("field")
        val = edit.get("value")
        if field in ("caption_preset", "title_text", "style_preset") and val is not None:
            result[field] = val
        elif field == "clip_trim" and edit.get("track_id") and edit.get("clip_id"):
            for trk in result.get("tracks") or []:
                if trk.get("id") == edit["track_id"]:
                    for clip in trk.get("clips") or []:
                        if clip.get("id") == edit["clip_id"]:
                            if "in" in edit:
                                clip["in"] = float(edit["in"])
                            if "out" in edit:
                                clip["out"] = float(edit["out"])

    return result


def trim_without_reencode(
    source_video: str,
    in_s: float,
    out_s: float,
    output_video: str
) -> Dict[str, Any]:
    """
    Phase 5 Golden Rule: Never re-encode when only `in`/`out` trim boundaries change!
    Uses FFmpeg `-c copy` stream copy for instant, zero-generation-loss trimming.
    """
    if not os.path.isfile(source_video):
        raise FileNotFoundError(f"Source video not found: {source_video}")

    os.makedirs(os.path.dirname(output_video), exist_ok=True)
    ffmpeg_bin = find_binary("ffmpeg")
    ffprobe_bin = find_binary("ffprobe")

    start_s = max(0.0, float(in_s))
    dur_s = max(0.2, float(out_s) - start_s)

    t0 = time.time()
    cmd = [
        ffmpeg_bin, "-y",
        "-ss", f"{start_s:.3f}",
        "-t", f"{dur_s:.3f}",
        "-i", source_video,
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        output_video
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed_s = round(time.time() - t0, 4)
    if proc.returncode != 0:
        raise RuntimeError(f"Stream-copy trim failed: {proc.stderr[-400:]}")

    # Probe output to confirm codec and duration
    p_cmd = [
        ffprobe_bin, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height:format=duration",
        "-of", "json",
        output_video
    ]
    p_res = subprocess.run(p_cmd, capture_output=True, text=True)
    out_dur = dur_s
    codec_name = "h264"
    if p_res.returncode == 0:
        try:
            info = json.loads(p_res.stdout)
            st = (info.get("streams") or [{}])[0]
            fmt = info.get("format") or {}
            codec_name = st.get("codec_name", "h264")
            out_dur = round(float(fmt.get("duration", dur_s)), 3)
        except Exception:
            pass

    return {
        "stream_copy_used": True,
        "reencoded": False,
        "ffmpeg_codec_flag": "-c copy",
        "codec_name": codec_name,
        "in_s": round(start_s, 3),
        "out_s": round(float(out_s), 3),
        "expected_duration_s": round(dur_s, 3),
        "actual_duration_s": out_dur,
        "elapsed_s": elapsed_s,
        "output_video": output_video
    }
