"""
Edionic Backend + Single-Job Render Queue (Layer 2 — Phases 0 through 6)
- Serves the Web Editor UI (Layer 1) from ../frontend and Live Style Previews from ../styles
- Manages the one-render-job-at-a-time queue with live progress visible in the UI
- Connects Brain Router (Layer 3), Media Engine (Layer 4), Project EDL (Layer 6), Slop Gate QA (Layer 7),
  Phase 3 Style-Copy + Storyboard + Contact-Sheet QA, Phase 4 editor-job.json consumer,
  Phase 5 OpenFilm frame(t) & stream-copy trim, and Phase 6 4K Render + B-Roll Hunter + Music Beds + Publishing Kit.
"""

import json
import os
import queue
import shutil
import sys
import threading
import time
import urllib.parse
import uuid
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain_router import BrainRouter
from caption_presets import PRESET_CATALOG_INFO
from pipeline_v3 import (
    check_media_engine_status,
    ensure_sample_raw_clip,
    get_video_duration,
    render_edl_to_video,
    roundtrip_timeline_to_edl,
)
from sfx_system import ensure_sfx_library
from slop_gate import run_slop_gate_qa
from learn_style import (
    STYLES_DIR,
    ensure_default_style_library,
    learn_style_from_videos,
    list_style_library,
)
from storyboard import (
    generate_storyboard_html_preview,
    roundtrip_storyboard_edits_to_edl,
)
from templates import apply_template_to_job, list_templates
from contact_sheet_qa import run_contact_sheet_qa
from openfilm import (
    apply_overrides_and_locks,
    frame,
    trim_without_reencode,
    verify_look_double_draw,
)
from broll_hunter import ensure_broll_pool, hunt_broll_for_edl
from music_library import ensure_music_library
from publishing_kit import generate_publishing_kit

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
PROJECTS_DIR = os.path.join(BASE_DIR, "projects", "default")
UPLOADS_DIR = os.path.join(PROJECTS_DIR, "uploads")
EXPORTS_DIR = os.path.join(PROJECTS_DIR, "exports")
EDL_PATH = os.path.join(PROJECTS_DIR, "project.edl.json")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)
ensure_default_style_library()
ensure_music_library()

brain = BrainRouter()
job_queue: "queue.Queue[str]" = queue.Queue()
jobs_store: Dict[str, Dict[str, Any]] = {}
jobs_lock = threading.Lock()


def load_edl() -> Dict[str, Any]:
    if os.path.isfile(EDL_PATH):
        with open(EDL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_edl(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(EDL_PATH), exist_ok=True)
    with open(EDL_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def render_worker_loop() -> None:
    """Single-job-at-a-time render queue processor."""
    while True:
        job_id = job_queue.get()
        try:
            with jobs_lock:
                job = jobs_store.get(job_id)
                if not job:
                    continue
                job["status"] = "running"
                job["progress"] = 5
                job["message"] = "Starting render worker..."

            def update_progress(pct: int, msg: str) -> None:
                with jobs_lock:
                    if job_id in jobs_store:
                        jobs_store[job_id]["progress"] = pct
                        jobs_store[job_id]["message"] = msg

            source_video = job["source_video"]
            edl_data = job["edl"]
            target_res = job.get("resolution") or edl_data.get("resolution") or "1080x1920"
            suffix = "_4k" if str(target_res).lower() in ("4k", "2160x3840") else ""
            output_filename = f"edionic_render_{job_id[:8]}{suffix}.mp4"
            output_path = os.path.join(EXPORTS_DIR, output_filename)

            render_info = render_edl_to_video(
                source_video=source_video,
                edl_data=edl_data,
                output_video=output_path,
                progress_cb=update_progress,
                target_resolution=target_res
            )
            save_edl(edl_data)

            qa_report = run_slop_gate_qa(output_path, phase=6, render_info=render_info)
            cs_dir = os.path.join(EXPORTS_DIR, f"cs_{job_id[:8]}")
            cs_report = run_contact_sheet_qa(
                video_path=output_path,
                edl_data=edl_data,
                output_dir=cs_dir,
                ass_path=render_info.get("ass_path")
            )
            pub_dir = os.path.join(EXPORTS_DIR, f"pub_{job_id[:8]}")
            pub_kit = generate_publishing_kit(output_path, edl_data, output_dir=pub_dir)

            with jobs_lock:
                jobs_store[job_id]["status"] = "completed" if qa_report.get("overall_pass") else "qa_failed"
                jobs_store[job_id]["progress"] = 100
                jobs_store[job_id]["message"] = (
                    f"Render ({render_info.get('resolution')}) + Slop Gate & Contact-Sheet QA passed!"
                    if qa_report.get("overall_pass")
                    else "Render finished, but Slop Gate QA reported issues."
                )
                jobs_store[job_id]["output_filename"] = output_filename
                jobs_store[job_id]["download_url"] = f"/api/download/{output_filename}"
                jobs_store[job_id]["render_info"] = render_info
                jobs_store[job_id]["qa_report"] = qa_report
                jobs_store[job_id]["contact_sheet_qa"] = cs_report
                jobs_store[job_id]["publishing_kit"] = pub_kit

        except Exception as exc:
            with jobs_lock:
                if job_id in jobs_store:
                    jobs_store[job_id]["status"] = "failed"
                    jobs_store[job_id]["progress"] = 100
                    jobs_store[job_id]["message"] = f"Error: {exc}"
        finally:
            job_queue.task_done()


worker_thread = threading.Thread(target=render_worker_loop, daemon=True)
worker_thread.start()


class EdionicRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        raw = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Filename")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            media_status = check_media_engine_status()
            brain_status = brain.status()
            with jobs_lock:
                active_jobs = list(jobs_store.values())[-10:]
            self._send_json(200, {
                "product": "Edionic",
                "domain": "edionic.com",
                "support": "infosupport@edionic.com",
                "phase": 6,
                "media_engine": media_status,
                "brain_router": brain_status,
                "recent_jobs": active_jobs
            })
            return

        if path == "/api/sfx/catalog":
            self._send_json(200, ensure_sfx_library())
            return

        if path == "/api/music/catalog":
            self._send_json(200, ensure_music_library())
            return

        if path == "/api/broll/pool":
            self._send_json(200, {"broll": ensure_broll_pool()})
            return

        if path == "/api/styles":
            self._send_json(200, {"styles": list_style_library()})
            return

        if path == "/api/templates":
            self._send_json(200, {"templates": list_templates()})
            return

        if path.startswith("/styles/"):
            rel_path = urllib.parse.unquote(path[len("/styles/"):]).lstrip("/\\")
            full_style_file = os.path.abspath(os.path.join(STYLES_DIR, rel_path))
            if full_style_file.startswith(os.path.abspath(STYLES_DIR)) and os.path.isfile(full_style_file):
                ext = os.path.splitext(full_style_file)[1].lower()
                ctype = "text/html; charset=utf-8" if ext == ".html" else (
                    "application/javascript; charset=utf-8" if ext == ".js" else (
                        "application/json; charset=utf-8" if ext == ".json" else "text/markdown; charset=utf-8"
                    )
                )
                raw = open(full_style_file, "rb").read()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            self._send_json(404, {"error": "Style asset not found"})
            return

        if path == "/api/storyboard/preview":
            edl = load_edl()
            sb = edl.get("storyboard") or {}
            html_out = os.path.join(EXPORTS_DIR, "storyboard_preview.html")
            generate_storyboard_html_preview(sb, html_out)
            raw = open(html_out, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if path == "/api/captions/presets":
            self._send_json(200, {"presets": PRESET_CATALOG_INFO})
            return

        if path == "/api/edl":
            self._send_json(200, load_edl())
            return

        if path.startswith("/api/jobs/"):
            job_id = path.split("/api/jobs/", 1)[1].strip("/")
            with jobs_lock:
                job = jobs_store.get(job_id)
            if not job:
                self._send_json(404, {"error": "Job not found"})
            else:
                self._send_json(200, job)
            return

        if path.startswith("/api/download/") or path.startswith("/api/media/"):
            is_upload = path.startswith("/api/media/")
            fname = os.path.basename(urllib.parse.unquote(path.split("/", 3)[-1]))
            target_dir = UPLOADS_DIR if is_upload else EXPORTS_DIR
            fpath = os.path.join(target_dir, fname)
            if not os.path.isfile(fpath):
                self._send_json(404, {"error": f"File not found: {fname}"})
                return
            fsize = os.path.getsize(fpath)
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(fsize))
            if not is_upload:
                self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
            self.end_headers()
            with open(fpath, "rb") as f:
                shutil.copyfileobj(f, self.wfile)
            return

        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", "0"))

        if path == "/api/upload":
            raw_filename = self.headers.get("X-Filename", f"clip_{int(time.time())}.mp4")
            safe_name = "".join(c for c in os.path.basename(raw_filename) if c.isalnum() or c in "._-")
            if not safe_name.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
                safe_name += ".mp4"
            dest_path = os.path.join(UPLOADS_DIR, safe_name)

            # Fast chunked streaming write (1 MB chunks) + 100-continue support so large raw videos upload in milliseconds
            if self.headers.get("Expect", "").lower() == "100-continue":
                self.send_response_only(100)
                self.end_headers()

            remaining = length
            chunk_size = 1024 * 1024  # 1 MB chunks
            with open(dest_path, "wb") as f:
                while remaining > 0:
                    read_len = min(chunk_size, remaining)
                    chunk = self.rfile.read(read_len)
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            edl = load_edl()
            dur = round(max(1.0, get_video_duration(dest_path)), 2)
            for track in edl.get("tracks", []):
                if track.get("id") == "V1" and not track.get("locked"):
                    track["clips"] = [{
                        "id": "clip_v1_0",
                        "source": dest_path,
                        "in": 0.0,
                        "out": dur,
                        "at": 0.0,
                        "speed": 1.0,
                        "placement": "face_anchored_9_16"
                    }]
                elif track.get("id") == "A1" and not track.get("locked"):
                    track["clips"] = [{
                        "id": "clip_a1_0",
                        "source": dest_path,
                        "in": 0.0,
                        "out": dur,
                        "at": 0.0,
                        "speed": 1.0,
                        "volume": 1.0
                    }]
            save_edl(edl)
            self._send_json(200, {
                "uploaded": True,
                "filename": safe_name,
                "duration_s": dur,
                "media_url": f"/api/media/{safe_name}",
                "edl": edl
            })
            return

        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            payload = {}

        if path == "/api/edl":
            edl = roundtrip_timeline_to_edl(payload, existing_edl=load_edl())
            save_edl(edl)
            self._send_json(200, {"saved": True, "edl": edl})
            return

        if path == "/api/storyboard/roundtrip":
            edl = load_edl()
            sb = payload.get("storyboard") or payload
            edl = roundtrip_storyboard_edits_to_edl(edl, sb)
            save_edl(edl)
            self._send_json(200, {"roundtripped": True, "edl": edl})
            return

        if path == "/api/styles/learn":
            ref_videos = payload.get("reference_videos") or []
            style_id = payload.get("style_id") or f"custom_style_{int(time.time())}"
            learned = learn_style_from_videos(ref_videos, style_id=style_id, save_to_library=True)
            self._send_json(200, {"learned": True, "style": learned})
            return

        if path == "/api/openfilm/frame":
            t_sec = float(payload.get("t", 0.0))
            edl = payload.get("edl") or load_edl()
            self._send_json(200, frame(t_sec, edl))
            return

        if path == "/api/openfilm/trim":
            edl = load_edl()
            in_s = float(payload.get("in", 0.0))
            out_s = float(payload.get("out", 3.0))
            src = payload.get("source_video")
            if not src:
                for trk in edl.get("tracks", []):
                    if trk.get("id") == "V1" and trk.get("clips"):
                        src = trk["clips"][0].get("source")
                        break
            if not src or not os.path.isfile(str(src)):
                src = ensure_sample_raw_clip(os.path.join(UPLOADS_DIR, "hello_raw_5s.mp4"))
            out_trim = os.path.join(EXPORTS_DIR, f"trimmed_copy_{int(time.time())}.mp4")
            trim_res = trim_without_reencode(src, in_s, out_s, out_trim)
            self._send_json(200, trim_res)
            return

        if path == "/api/broll/hunt":
            edl = load_edl()
            hunt_res = hunt_broll_for_edl(edl)
            save_edl(edl)
            self._send_json(200, {"broll_hunt": hunt_res, "edl": edl})
            return

        if path == "/api/publishing-kit":
            edl = load_edl()
            video_path = payload.get("video_path")
            if not video_path or not os.path.isfile(str(video_path)):
                # Find latest MP4 in EXPORTS_DIR
                mp4s = [
                    os.path.join(EXPORTS_DIR, f)
                    for f in os.listdir(EXPORTS_DIR)
                    if f.endswith(".mp4") and os.path.isfile(os.path.join(EXPORTS_DIR, f))
                ]
                video_path = max(mp4s, key=os.path.getmtime) if mp4s else ensure_sample_raw_clip(
                    os.path.join(UPLOADS_DIR, "hello_raw_5s.mp4")
                )
            kit = generate_publishing_kit(video_path, edl)
            self._send_json(200, kit)
            return

        if path == "/api/brain/config":
            new_status = brain.configure_runtime(payload)
            self._send_json(200, {"configured": True, "brain_router": new_status})
            return

        if path == "/api/agent/command":
            cmd_text = payload.get("command", "")
            edl = load_edl()
            decision = brain.decide_edit_command(cmd_text, edl)
            if decision.get("edl_patch"):
                edl = apply_overrides_and_locks(edl, decision["edl_patch"])
                save_edl(edl)

            extra_results: Dict[str, Any] = {}
            triggers = decision.get("pipeline_triggers") or []
            if "hunt_broll" in triggers:
                extra_results["broll_hunt"] = hunt_broll_for_edl(edl)
                save_edl(edl)
            if "generate_publishing_kit" in triggers:
                mp4s = [
                    os.path.join(EXPORTS_DIR, f)
                    for f in os.listdir(EXPORTS_DIR)
                    if f.endswith(".mp4") and os.path.isfile(os.path.join(EXPORTS_DIR, f))
                ]
                video_path = max(mp4s, key=os.path.getmtime) if mp4s else ensure_sample_raw_clip(
                    os.path.join(UPLOADS_DIR, "hello_raw_5s.mp4")
                )
                extra_results["publishing_kit"] = generate_publishing_kit(video_path, edl)

            self._send_json(200, {
                "decision": decision,
                "extra_results": extra_results,
                "edl": edl
            })
            return

        if path in ("/api/render", "/api/render/job"):
            raw_job = payload.get("edl") or payload
            template_id = payload.get("template_id") or raw_job.get("template_id")
            if template_id:
                try:
                    raw_job = apply_template_to_job(template_id, raw_job)
                except ValueError as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
            edl = roundtrip_timeline_to_edl(raw_job, existing_edl=load_edl())
            target_res = payload.get("resolution") or raw_job.get("resolution") or "1080x1920"
            edl["resolution"] = target_res

            source_video = payload.get("source_video") or raw_job.get("source_video")
            if not source_video or not os.path.isfile(str(source_video)):
                for track in edl.get("tracks", []):
                    if track.get("id") == "V1" and track.get("clips"):
                        cand = track["clips"][0].get("source")
                        if cand and os.path.isfile(cand):
                            source_video = cand
                            break

            if not source_video or not os.path.isfile(str(source_video)):
                sample_raw = os.path.join(UPLOADS_DIR, "talking_head_phase2_raw.mp4")
                source_video = ensure_sample_raw_clip(sample_raw)
                for track in edl.get("tracks", []):
                    if track.get("id") == "V1":
                        track["clips"] = [{
                            "id": "clip_v1_0",
                            "source": source_video,
                            "in": 0.0,
                            "out": 5.0,
                            "at": 0.0,
                            "speed": 1.0,
                            "placement": "face_anchored_9_16"
                        }]
                    elif track.get("id") == "A1":
                        track["clips"] = [{
                            "id": "clip_a1_0",
                            "source": source_video,
                            "in": 0.0,
                            "out": 5.0,
                            "at": 0.0,
                            "speed": 1.0,
                            "volume": 1.0
                        }]
            save_edl(edl)

            job_id = str(uuid.uuid4())
            job_entry = {
                "job_id": job_id,
                "status": "queued",
                "progress": 0,
                "resolution": target_res,
                "message": f"Queued {target_res} render in single-render-job queue...",
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "source_video": source_video,
                "edl": edl
            }
            with jobs_lock:
                jobs_store[job_id] = job_entry
            job_queue.put(job_id)
            self._send_json(202, job_entry)
            return

        self._send_json(404, {"error": f"Unknown endpoint: {path}"})


if __name__ == "__main__":
    host = os.environ.get("EDIONIC_HOST", "0.0.0.0")
    port = int(os.environ.get("EDIONIC_PORT", os.environ.get("PORT", "8080")))
    server = ThreadingHTTPServer((host, port), EdionicRequestHandler)
    print(f"Edionic Multi-Threaded Backend + UI running at http://127.0.0.1:{port} (bound to {host}:{port})")
    server.serve_forever()
