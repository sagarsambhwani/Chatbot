import os
import sys
import io
import time
import json
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, stream_with_context
from werkzeug.utils import secure_filename

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.config import DATA_DIR, TEMPLATES_DIR, STATIC_DIR, AUDIO_CACHE_DIR, BASE_DIR
from backend.assistant import LocalAssistant
from ai_infra.voice_stt import SpeechToText
from ai_infra.voice_tts import TextToSpeech

app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["UPLOAD_FOLDER"] = DATA_DIR
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB max upload

@app.after_request
def add_header(response):
    """Disable aggressive browser caching for instantaneous UI updates."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Initialize AI & Assistant services
assistant = LocalAssistant()
stt = SpeechToText()
tts = TextToSpeech()

def get_system_vram() -> str:
    """Get real-time GPU VRAM usage."""
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
            text=True
        ).strip()
        used, total = output.split(",")
        return f"{used.strip()} MB / {total.strip()} MB"
    except Exception:
        return "N/A"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/system_status")
def system_status():
    return jsonify({
        "vram": get_system_vram(),
        "model": "qwen2.5:1.5b (100% on GPU)"
    })

@app.route("/api/chat_stream", methods=["POST"])
def chat_stream():
    data = request.json or {}
    user_message = data.get("message", "").strip()
    history = data.get("history", [])
    use_web = data.get("use_web", True)
    use_rag = data.get("use_rag", True)
    enable_tts = data.get("enable_tts", True)
    stt_seconds = data.get("stt_seconds", 0.0)

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    def event_stream():
        full_answer = ""
        final_latencies = {}
        for event in assistant.generate_stream(
            user_prompt=user_message,
            chat_history=history,
            use_web=use_web,
            use_rag=use_rag
        ):
            if event["type"] == "done":
                full_answer = event["answer"]
                final_latencies = event.get("latencies", {})
                final_latencies["stt_seconds"] = stt_seconds
                final_latencies["tts_seconds"] = 0.0
                event["audio_url"] = ""
                event["latencies"] = final_latencies
                yield f"data: {json.dumps(event)}\n\n"

                # Async TTS: synthesize after done event without blocking the text response!
                if enable_tts and full_answer:
                    audio_url, tts_time = tts.synthesize(full_answer)
                    audio_event = {
                        "type": "audio",
                        "audio_url": audio_url,
                        "tts_seconds": tts_time
                    }
                    yield f"data: {json.dumps(audio_event)}\n\n"
                return

            yield f"data: {json.dumps(event)}\n\n"

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_message = data.get("message", "").strip()
    history = data.get("history", [])
    use_web = data.get("use_web", True)
    use_rag = data.get("use_rag", True)
    enable_tts = data.get("enable_tts", True)
    stt_seconds = data.get("stt_seconds", 0.0)

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Generate grounded response
    result = assistant.generate_response(
        user_prompt=user_message,
        chat_history=history,
        use_web=use_web,
        use_rag=use_rag
    )

    audio_url = ""
    tts_time = 0.0
    if enable_tts and result["answer"]:
        audio_url, tts_time = tts.synthesize(result["answer"])

    latencies = result.get("latencies", {})
    latencies["tts_seconds"] = tts_time
    latencies["stt_seconds"] = stt_seconds

    return jsonify({
        "reply": result["answer"],
        "audio_url": audio_url,
        "web_sources": result["web_sources"],
        "doc_sources": result["doc_sources"],
        "latencies": latencies,
        "vram": get_system_vram()
    })

@app.route("/api/tts", methods=["POST"])
def synthesize_tts():
    data = request.json or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    audio_url, tts_time = tts.synthesize(text)
    return jsonify({"audio_url": audio_url, "tts_seconds": tts_time})

@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    # Transcribe directly from in-memory stream (zero disk I/O)
    audio_stream = io.BytesIO(audio_file.read())
    text, stt_time = stt.transcribe(audio_stream)

    return jsonify({"text": text, "stt_seconds": stt_time})

@app.route("/api/documents", methods=["GET", "POST"])
def handle_documents():
    if request.method == "POST":
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        filename = secure_filename(file.filename)
        dest_path = os.path.join(DATA_DIR, filename)
        file.save(dest_path)

        # Re-index documents
        indexed_count = assistant.rag.index_documents()
        return jsonify({
            "message": f"Successfully uploaded and indexed '{filename}'.",
            "total_chunks": indexed_count
        })

    # GET: List existing documents
    files = []
    if os.path.exists(DATA_DIR):
        files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith((".txt", ".md", ".pdf"))]
    return jsonify({
        "documents": files,
        "indexed_chunks": len(assistant.rag.index)
    })

@app.route("/api/documents/reindex", methods=["POST"])
def reindex_documents():
    count = assistant.rag.index_documents()
    return jsonify({"message": f"Re-indexed {count} document chunks."})

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(">> Starting Local Voice Assistant on http://127.0.0.1:5000")
    print(f">> Initial VRAM: {get_system_vram()}")
    print("=" * 60 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
