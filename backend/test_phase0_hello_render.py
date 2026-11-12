"""
Phase 0 End-to-End Verification ("Hello Render" + Upload -> Render -> Download + Slop Gate QA)
Runs against the real HTTP server, uploads a real 5-second video clip, triggers the render job queue,
waits for completion, downloads the rendered 9:16 MP4, and prints the full Slop Gate QA report.
"""

import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline_v3 import check_media_engine_status, ensure_sample_raw_clip


def run_phase0_test(base_url: str = "http://127.0.0.1:8080") -> dict:
    print("=== 1. Media Engine Check (FFmpeg + faster-whisper) ===")
    engine_status = check_media_engine_status()
    print(json.dumps(engine_status, indent=2))

    # Generate a real 5s raw clip to upload
    raw_sample = r"C:\ai editing\projects\default\uploads\test_input_5s.mp4"
    ensure_sample_raw_clip(raw_sample)
    with open(raw_sample, "rb") as f:
        raw_bytes = f.read()

    print(f"\n=== 2. Uploading Real Clip ({len(raw_bytes):,} bytes) via POST /api/upload ===")
    up_req = urllib.request.Request(
        f"{base_url}/api/upload",
        data=raw_bytes,
        headers={"X-Filename": "hello_test_5s.mp4", "Content-Type": "video/mp4"},
        method="POST"
    )
    with urllib.request.urlopen(up_req, timeout=10) as resp:
        up_data = json.loads(resp.read().decode("utf-8"))
    print("Uploaded:", up_data.get("filename"), "| Media URL:", up_data.get("media_url"))

    print("\n=== 3. Queueing 9:16 Render Job via POST /api/render ===")
    render_req = urllib.request.Request(
        f"{base_url}/api/render",
        data=json.dumps({"edl": up_data.get("edl")}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(render_req, timeout=10) as resp:
        job_data = json.loads(resp.read().decode("utf-8"))
    job_id = job_data["job_id"]
    print("Queued Job ID:", job_id)

    # Poll until completed
    final_job = {}
    for _ in range(60):
        time.sleep(0.5)
        with urllib.request.urlopen(f"{base_url}/api/jobs/{job_id}", timeout=5) as jresp:
            final_job = json.loads(jresp.read().decode("utf-8"))
        print(f"  Job Status: {final_job.get('status')} ({final_job.get('progress')}%) - {final_job.get('message')}")
        if final_job.get("status") in ("completed", "qa_failed", "failed"):
            break

    print("\n=== 4. Downloading Rendered 9:16 Video via GET", final_job.get("download_url"), "===")
    dl_path = r"C:\ai editing\projects\default\exports\verified_downloaded_hello_render.mp4"
    with urllib.request.urlopen(f"{base_url}{final_job['download_url']}", timeout=10) as dresp:
        dl_bytes = dresp.read()
    with open(dl_path, "wb") as f:
        f.write(dl_bytes)
    print(f"Downloaded verified render to: {dl_path} ({len(dl_bytes):,} bytes)")

    print("\n=== 5. Slop Gate QA Report (Real Render) ===")
    print(json.dumps(final_job.get("qa_report", {}), indent=2))
    return final_job


if __name__ == "__main__":
    run_phase0_test()
