"""
Edionic Phases 3, 4, 5, and 6 Complete End-to-End Verification Suite
Runs real renders, FFprobe/FFmpeg inspections, Contact-Sheet QA (including planted defect detection),
`editor-job.json` consumption, OpenFilm `frame(t)` & shuffled `look` double-draw determinism,
`-c copy` stream-copy trimming, 4K (`2160x3840`) final render, B-Roll motion verification,
royalty-free music bed mixing, and Publishing Kit generation.
"""

import json
import os
import sys
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from learn_style import (
    ensure_default_style_library,
    learn_style_from_videos,
    list_style_library,
)
from storyboard import (
    generate_storyboard_from_transcript,
    generate_storyboard_html_preview,
    roundtrip_storyboard_edits_to_edl,
)
from contact_sheet_qa import (
    create_planted_defect_video,
    run_contact_sheet_qa,
)
from pipeline_v3 import (
    ensure_sample_raw_clip,
    render_edl_to_video,
    roundtrip_timeline_to_edl,
    run_editor_job_json,
    transcribe_with_word_timestamps,
)
from openfilm import (
    apply_overrides_and_locks,
    frame,
    trim_without_reencode,
    verify_look_double_draw,
)
from broll_hunter import ensure_broll_pool, hunt_broll_for_edl
from music_library import ensure_music_library
from publishing_kit import generate_publishing_kit
from slop_gate import run_slop_gate_qa

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS_DIR = os.path.join(BASE_DIR, "projects", "default", "exports")
UPLOADS_DIR = os.path.join(BASE_DIR, "projects", "default", "uploads")


def run_all_phases_verification() -> Dict[str, object]:
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    raw_clip = os.path.join(UPLOADS_DIR, "talking_head_phase2_raw.mp4")
    ensure_sample_raw_clip(raw_clip)
    cached_words = transcribe_with_word_timestamps(raw_clip)

    # =========================================================================
    # PHASE 3: Style-Copy + Storyboard-First + Contact-Sheet QA
    # =========================================================================
    print("=================================================================")
    print("PHASE 3: Style-Copy + Storyboard-First + Contact-Sheet QA")
    print("=================================================================")

    styles_lib = ensure_default_style_library()
    smoke2 = styles_lib.get("smoke2_style", {})
    assert smoke2.get("resolution") == "1080x1920", "smoke2_style resolution must be 1080x1920"
    assert smoke2.get("fps") == 30.0, "smoke2_style fps must be 30.0"
    assert smoke2.get("avg_shot_length") == 17.595, "smoke2_style avg_shot_length must be 17.595"
    assert smoke2.get("palette") == ["#864027", "#8C5B36", "#884126", "#864026", "#8E6039"]
    assert smoke2.get("caption_style") == "unverified"
    assert smoke2.get("hook_style") == "unverified"
    assert smoke2.get("pacing") == "unverified"

    # Also test live learning from a real reference video on disk
    learned_live = learn_style_from_videos([raw_clip], style_id="learned_from_sample", save_to_library=True)
    assert learned_live["caption_style"] == "unverified"
    assert len(learned_live["palette"]) == 5
    print(f"  [PASS] smoke2_style verified & live style learned: palette={learned_live['palette']}")

    # Storyboard generation + 1-page HTML preview + round-trip edit into EDL
    sb = generate_storyboard_from_transcript(cached_words, edited_duration=7.5, title="Phase 3 Storyboard Plan")
    sb_html_path = os.path.join(EXPORTS_DIR, "phase3_storyboard_preview.html")
    generate_storyboard_html_preview(sb, sb_html_path)
    assert os.path.isfile(sb_html_path), "Storyboard HTML preview must exist"

    # Edit storyboard block 0 text & graphic and round-trip into EDL
    sb["blocks"][0]["title"] = "VIRAL 9:16 HOOK"
    sb["blocks"][0]["graphic"] = "Kinetic Glow Banner"
    edl_p3 = roundtrip_timeline_to_edl({"storyboard": sb, "caption_preset": "glow", "style_preset": "smoke2_style"})
    assert edl_p3["title_text"] == "VIRAL 9:16 HOOK"
    print(f"  [PASS] Storyboard 1-page HTML preview & round-trip into EDL verified ({len(sb['blocks'])} blocks)")

    # Contact-Sheet QA: 1) Clean render passes, 2) Planted defect render is caught!
    clean_p3_mp4 = os.path.join(EXPORTS_DIR, "phase3_clean_render.mp4")
    r_info_p3 = render_edl_to_video(raw_clip, edl_p3, clean_p3_mp4, cached_words=cached_words)
    cs_clean_dir = os.path.join(EXPORTS_DIR, "phase3_cs_clean")
    cs_clean = run_contact_sheet_qa(clean_p3_mp4, edl_p3, cs_clean_dir, ass_path=r_info_p3["ass_path"])
    assert cs_clean["overall_pass"] is True, f"Clean render must pass Contact-Sheet QA: {cs_clean}"
    print(
        f"  [PASS] Contact-Sheet QA (Clean Render): {cs_clean['stills_rendered']} stills across "
        f"{cs_clean['spans_inspected']} spans -> 0 defects ({cs_clean['contact_sheet_png']})"
    )

    # Planted defect test (must catch planted defects!)
    defective_mp4 = os.path.join(EXPORTS_DIR, "phase3_planted_defect.mp4")
    defective_ass = os.path.join(EXPORTS_DIR, "phase3_planted_defect.ass")
    create_planted_defect_video(clean_p3_mp4, defective_mp4, defective_ass)
    cs_defect_dir = os.path.join(EXPORTS_DIR, "phase3_cs_planted_defect")
    cs_defect = run_contact_sheet_qa(defective_mp4, edl_p3, cs_defect_dir, ass_path=defective_ass)
    assert cs_defect["overall_pass"] is False, "Contact-Sheet QA MUST fail when planted defects are present!"
    assert cs_defect["defects_found_count"] >= 4, "Contact-Sheet QA must catch all 4 planted defect categories!"
    print(
        f"  [PASS] Contact-Sheet QA Caught Planted Defects: overall_pass={cs_defect['overall_pass']}, "
        f"defects_caught={cs_defect['defects_found_count']}"
    )

    # =========================================================================
    # PHASE 4: Pipeline Consumes `editor-job.json` Directly
    # =========================================================================
    print("\n=================================================================")
    print("PHASE 4: Pipeline Consumes editor-job.json Directly")
    print("=================================================================")

    editor_job_path = os.path.join(EXPORTS_DIR, "editor-job.json")
    exported_ui_job = {
        "version": 1,
        "caption_preset": "pill_highlight",
        "title_text": "Phase 4 Direct Job Hook",
        "style_preset": "vox_explainer_style",
        "sfx": [
            {"name": "whoosh", "placed_at_s": 1.0},
            {"name": "pop", "placed_at_s": 2.5},
            {"name": "ding", "placed_at_s": 4.0},
            {"name": "thump", "placed_at_s": 5.5},
            {"name": "snap", "placed_at_s": 7.0}
        ],
        "storyboard": sb
    }
    with open(editor_job_path, "w", encoding="utf-8") as f:
        json.dump(exported_ui_job, f, indent=2)

    phase4_mp4 = os.path.join(EXPORTS_DIR, "phase4_from_editor_job.mp4")
    p4_result = run_editor_job_json(
        job_source=editor_job_path,
        output_video=phase4_mp4,
        source_video=raw_clip,
        cached_words=cached_words
    )
    assert p4_result["job_consumed"] is True
    assert p4_result["qa_report"]["overall_pass"] is True
    assert p4_result["contact_sheet_qa"]["overall_pass"] is True
    print(
        f"  [PASS] Consumed {editor_job_path} with zero manual steps -> {phase4_mp4} "
        f"(Slop Gate PASS={p4_result['qa_report']['overall_pass']}, Contact-Sheet PASS={p4_result['contact_sheet_qa']['overall_pass']})"
    )

    # =========================================================================
    # PHASE 5: OpenFilm Ideas & Determinism
    # =========================================================================
    print("\n=================================================================")
    print("PHASE 5: OpenFilm Determinism, frame(t), Overrides & -c copy Trim")
    print("=================================================================")

    f_state_1 = frame(1.25, p4_result["edl"])
    f_state_2 = frame(1.25, p4_result["edl"])
    assert f_state_1["frame_state_sha256"] == f_state_2["frame_state_sha256"]
    print(f"  [PASS] Pure function frame(t=1.25s) deterministic hash: {f_state_1['frame_state_sha256']}")

    look_dd = verify_look_double_draw(phase4_mp4, p4_result["edl"], sample_times=[0.5, 1.8, 3.2])
    assert look_dd["pass"] is True
    print(
        f"  [PASS] OpenFilm 'look' Double-Draw in Shuffled Order: fn_deterministic={look_dd['fn_deterministic']}, "
        f"pixel_deterministic={look_dd['pixel_deterministic']}"
    )

    # Test overrides layer + locked tracks protection
    locked_edl = apply_overrides_and_locks(
        p4_result["edl"],
        proposed_mutation={"caption_preset": "extrude_3d"},
        record_user_edit={"field": "caption_preset", "value": "neon_serif", "lock_track": "CC"}
    )
    # Now attempt an AI mutation to change caption_preset back to condensed while CC is locked
    after_ai_mutation = apply_overrides_and_locks(locked_edl, {"caption_preset": "condensed"})
    assert after_ai_mutation["caption_preset"] == "neon_serif", "Locked CC track & user_edit must block AI overwrite!"
    print("  [PASS] Overrides layer & locked track ('CC') blocked unauthorized overwrite (kept 'neon_serif')")

    # Test never-re-encode stream-copy trim (-c copy)
    trimmed_copy_mp4 = os.path.join(EXPORTS_DIR, "phase5_stream_copy_trim.mp4")
    trim_info = trim_without_reencode(phase4_mp4, in_s=0.5, out_s=4.5, output_video=trimmed_copy_mp4)
    assert trim_info["stream_copy_used"] is True and trim_info["reencoded"] is False
    print(
        f"  [PASS] Never-Re-Encode Trim (-c copy): {trim_info['in_s']}s..{trim_info['out_s']}s completed in "
        f"{trim_info['elapsed_s']}s -> {trimmed_copy_mp4}"
    )

    # =========================================================================
    # PHASE 6: Publishing Kit, 4K (2160x3840) Render, B-Roll Hunter & Music Beds
    # =========================================================================
    print("\n=================================================================")
    print("PHASE 6: Publishing Kit, 4K (2160x3840) Render, B-Roll & Music")
    print("=================================================================")

    # 1. Automated Motion-Verified B-Roll Hunter
    broll_res = hunt_broll_for_edl(p4_result["edl"])
    assert broll_res["motion_verified_count"] >= 3
    assert len(broll_res["selected_broll"]) >= 2
    print(
        f"  [PASS] Motion-Verified B-Roll Hunter: {broll_res['motion_verified_count']} clips verified moving, "
        f"{len(broll_res['selected_broll'])} bound to Track V2"
    )

    # 2. Royalty-Free Music Bed Library
    music_cat = ensure_music_library()
    assert len(music_cat["beds"]) >= 3
    print(f"  [PASS] Royalty-Free Music Bed Library: {len(music_cat['beds'])} synthesized beds ready")

    # 3. 4K (2160x3840) Final Render with Music Bed + Slop Gate QA
    edl_4k = roundtrip_timeline_to_edl({
        "caption_preset": "glow",
        "title_text": "EDIONIC 4K ULTRA HD",
        "style_preset": "smoke2_style",
        "music_bed": "upbeat_pulse",
        "resolution": "2160x3840",
        "storyboard": sb
    }, existing_edl=p4_result["edl"])

    render_4k_mp4 = os.path.join(EXPORTS_DIR, "phase6_final_4k_2160x3840.mp4")
    r_info_4k = render_edl_to_video(
        source_video=raw_clip,
        edl_data=edl_4k,
        output_video=render_4k_mp4,
        cached_words=cached_words,
        target_resolution="2160x3840"
    )
    qa_4k = run_slop_gate_qa(render_4k_mp4, phase=6, render_info=r_info_4k)
    assert qa_4k["metrics"]["width"] == 2160 and qa_4k["metrics"]["height"] == 3840
    assert qa_4k["overall_pass"] is True, f"4K render must pass all Slop Gate QA checks: {qa_4k}"
    print(
        f"  [PASS] 4K Final Render (2160x3840): glyph_height={qa_4k['metrics']['caption_height_px']}px (>=108px), "
        f"LUFS={qa_4k['metrics']['integrated_lufs']}, Slop Gate PASS={qa_4k['overall_pass']}"
    )

    # 4. Publishing Kit Generation
    pub_kit_dir = os.path.join(EXPORTS_DIR, "phase6_publishing_kit")
    pub_kit = generate_publishing_kit(render_4k_mp4, edl_4k, output_dir=pub_kit_dir)
    assert pub_kit["thumbnail_exists"] is True
    assert len(pub_kit["hashtags"]) >= 10
    assert "branded_content_disclosure" in pub_kit
    print(
        f"  [PASS] Publishing Kit Generated: title={pub_kit['title']!r}, "
        f"hashtags={len(pub_kit['hashtags'])}, thumbnail={pub_kit['thumbnail_path']}"
    )

    summary_report = {
        "all_phases_3_to_6_passed": True,
        "phase_3": {
            "smoke2_style_verified": True,
            "live_learned_palette": learned_live["palette"],
            "storyboard_html": sb_html_path,
            "contact_sheet_clean_pass": cs_clean["overall_pass"],
            "contact_sheet_planted_defect_caught": not cs_defect["overall_pass"],
            "planted_defects_caught_count": cs_defect["defects_found_count"]
        },
        "phase_4": {
            "editor_job_json_path": editor_job_path,
            "output_video": phase4_mp4,
            "slop_gate_pass": p4_result["qa_report"]["overall_pass"]
        },
        "phase_5": {
            "frame_t_hash_1_25s": f_state_1["frame_state_sha256"],
            "look_double_draw_shuffled_pass": look_dd["pass"],
            "overrides_and_locks_pass": after_ai_mutation["caption_preset"] == "neon_serif",
            "stream_copy_trim_pass": trim_info["stream_copy_used"] and not trim_info["reencoded"],
            "stream_copy_elapsed_s": trim_info["elapsed_s"]
        },
        "phase_6": {
            "render_4k_video": render_4k_mp4,
            "render_4k_resolution": f"{qa_4k['metrics']['width']}x{qa_4k['metrics']['height']}",
            "render_4k_caption_px": qa_4k["metrics"]["caption_height_px"],
            "render_4k_lufs": qa_4k["metrics"]["integrated_lufs"],
            "render_4k_slop_gate_pass": qa_4k["overall_pass"],
            "broll_motion_verified_count": broll_res["motion_verified_count"],
            "music_beds_count": len(music_cat["beds"]),
            "publishing_kit_json": pub_kit["kit_json_path"],
            "publishing_kit_md": pub_kit["kit_md_path"],
            "thumbnail_path": pub_kit["thumbnail_path"]
        }
    }

    report_path = os.path.join(EXPORTS_DIR, "phases_3_to_6_qa_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)
    print(f"\nALL PHASES 3, 4, 5, AND 6 PASSED! Saved full report to: {report_path}")
    return summary_report


if __name__ == "__main__":
    run_all_phases_verification()
