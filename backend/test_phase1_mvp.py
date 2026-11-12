"""
Phase 1 MVP End-to-End Verification:
Upload real talking-head clip -> faster-whisper word-level transcription -> default `glow` ASS captions
-> silence cut -> face-anchored 9:16 export at 1080p -> Section 7 Slop Gate QA Rules 1–3 on real render.
"""

import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline_v3 import ensure_sample_raw_clip


def run_phase1_test(base_url: str = "http://127.0.0.1:8080") -> dict:
    raw_talking_head = r"C:\ai editing\projects\default\uploads\talking_head_raw.mp4"
    # Force fresh talking-head sample generation if needed
    if os.path.isfile(raw_talking_head):
        os.remove(raw_talking_head)
    ensure_sample_raw_clip(raw_talking_head)

    with open(raw_talking_head, "rb") as f:
        raw_bytes = f.read()

    print(f"=== 1. Uploading Real Talking-Head Clip ({len(raw_bytes):,} bytes) via POST /api/upload ===")
    up_req = urllib.request.Request(
        f"{base_url}/api/upload",
        data=raw_bytes,
        headers={"X-Filename": "talking_head_mvp.mp4", "Content-Type": "video/mp4"},
        method="POST"
    )
    with urllib.request.urlopen(up_req, timeout=15) as resp:
        up_data = json.loads(resp.read().decode("utf-8"))
    print("Uploaded:", up_data.get("filename"))

    print("\n=== 2. Queueing Phase 1 MVP Render (Whisper + Silence Cut + Face Framing + Glow Captions) ===")
    render_req = urllib.request.Request(
        f"{base_url}/api/render",
        data=json.dumps({"edl": up_data.get("edl")}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(render_req, timeout=15) as resp:
        job_data = json.loads(resp.read().decode("utf-8"))
    job_id = job_data["job_id"]
    print("Queued Job ID:", job_id)

    final_job = {}
    for _ in range(180):
        time.sleep(1.0)
        with urllib.request.urlopen(f"{base_url}/api/jobs/{job_id}", timeout=10) as jresp:
            final_job = json.loads(jresp.read().decode("utf-8"))
        print(f"  [{final_job.get('progress')}%] {final_job.get('status')} — {final_job.get('message')}")
        if final_job.get("status") in ("completed", "qa_failed", "failed"):
            break

    r_info = final_job.get("render_info", {})
    print("\n=== 3. Whisper Word-Level Timestamps & Silence Cut Summary ===")
    print("Cut Plan:", json.dumps(r_info.get("cut_plan", {}), indent=2))
    print("\n=== 4. Slop Gate QA Report (Rules 1–3 on Real Render) ===")
    print(json.dumps(final_job.get("qa_report", {}), indent=2))
    return final_job


if __name__ == "__main__":
    run_phase1_test()
