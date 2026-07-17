#!/usr/bin/env python3
"""
Atena Video Editor — MVP clone do Captions.ai
Substituivel por Submagic, Vizard etc.
MVP: upload video -> transcrever (faster-whisper) -> fazer SRT -> queimar legenda com ffmpeg.
Sem b-roll ou zoom inteligente nesta primeira versao.
"""

import os, subprocess, uuid, json, time
from pathlib import Path
from flask import Flask, request, render_template, jsonify, send_file, url_for

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB
BASE = Path(__file__).parent
UPLOAD = BASE / "static" / "uploads"
OUTPUT = BASE / "static" / "outputs"
UPLOAD.mkdir(parents=True, exist_ok=True)
OUTPUT.mkdir(parents=True, exist_ok=True)

JOBS = {}  # job_id -> status

def transcrever(video_path: Path, lang="pt"):
    """Transcreve audio com Whisper e gera SRT."""
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(str(video_path), language=lang, word_timestamps=True)
        return result
    except Exception as e:
        return {"error": str(e)}

def srt_from_segments(segments):
    lines = []
    for i, seg in enumerate(segments, 1):
        start = seg["start"]
        end = seg["end"]
        text = seg["text"].strip()
        if not text:
            continue
        lines.append(f"{i}")
        lines.append(f"{_fmt_time(start)} --> {_fmt_time(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)

def _fmt_time(secs):
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/process", methods=["POST"])
def process():
    if "video" not in request.files:
        return jsonify({"error": "Nenhum video enviado"}), 400
    file = request.files["video"]
    if not file.filename:
        return jsonify({"error": "Arquivo vazio"}), 400
    ext = Path(file.filename).suffix or ".mp4"
    job_id = uuid.uuid4().hex[:12]
    video_path = UPLOAD / f"{job_id}{ext}"
    file.save(video_path)
    JOBS[job_id] = {"status": "processing", "progress": "Transcrevendo audio..."}
    lang = request.form.get("lang", "pt")
    try:
        result = transcrever(video_path, lang)
        if "error" in result:
            JOBS[job_id]["status"] = "error"
            JOBS[job_id]["error"] = result["error"]
            return jsonify({"job_id": job_id, "error": result["error"]}), 500
        srt_content = srt_from_segments(result["segments"])
        srt_path = OUTPUT / f"{job_id}.srt"
        srt_path.write_text(srt_content, encoding="utf-8")
        output_video = OUTPUT / f"{job_id}_legendado.mp4"
        JOBS[job_id]["progress"] = "Renderizando video com legendas..."
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"subtitles={str(srt_path)}:force_style='FontSize=16,FontColor=&HFFFFFF&,BorderStyle=1,Outline=2,Shadow=1'",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            str(output_video)
        ]
        subprocess.run(cmd, capture_output=True, timeout=300)
        if not output_video.exists():
            JOBS[job_id]["status"] = "error"
            return jsonify({"job_id": job_id, "error": "Falha ao renderizar video"}), 500
        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["video_url"] = url_for("static", filename=f"outputs/{job_id}_legendado.mp4")
        JOBS[job_id]["srt_url"] = url_for("static", filename=f"outputs/{job_id}.srt")
        return jsonify({
            "job_id": job_id,
            "status": "done",
            "video_url": JOBS[job_id]["video_url"],
            "srt_url": JOBS[job_id]["srt_url"],
            "segments": len(result["segments"])
        })
    except Exception as e:
        JOBS[job_id]["status"] = "error"
        return jsonify({"job_id": job_id, "error": str(e)}), 500

@app.route("/api/status/<job_id>")
def status(job_id):
    j = JOBS.get(job_id)
    if not j:
        return jsonify({"error": "Job nao encontrado"}), 404
    return jsonify(j)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)