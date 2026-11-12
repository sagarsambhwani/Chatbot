import os
import sys
import time
import subprocess
import threading
import webbrowser
import requests

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def ensure_ollama_running():
    """Ensure Ollama service is active with dual-model GPU VRAM optimization."""
    try:
        res = requests.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
        if res.status_code == 200:
            print("[+] Local Ollama service is active.")
            return
    except Exception:
        pass

    print("[!] Ollama is not active. Starting local Ollama service with GPU dual-model support...")
    env = os.environ.copy()
    env["OLLAMA_MAX_LOADED_MODELS"] = "2"
    env["OLLAMA_KEEP_ALIVE"] = "-1"
    env["OLLAMA_NUM_PARALLEL"] = "1"

    try:
        flags = 0
        if sys.platform == "win32":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)

        subprocess.Popen(
            ["ollama", "serve"],
            env=env,
            creationflags=flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        for _ in range(20):
            time.sleep(0.5)
            try:
                res = requests.get("http://127.0.0.1:11434/api/tags", timeout=1)
                if res.status_code == 200:
                    print("[+] Ollama service is ready.")
                    return
            except Exception:
                pass
    except Exception as e:
        print(f"[!] Warning: Could not auto-launch Ollama: {e}")

def auto_open_browser():
    """Open assistant web UI in the default browser once server is up."""
    time.sleep(1.2)
    try:
        webbrowser.open("http://127.0.0.1:5000")
    except Exception:
        pass

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(">> Launching Local AI Voice Assistant")
    print("=" * 60)

    # 1. Guarantee Ollama is up with dual-model support
    ensure_ollama_running()

    # 2. Launch browser window in background
    threading.Thread(target=auto_open_browser, daemon=True).start()

    # 3. Start Flask assistant server
    from backend.app import app
    app.run(host="127.0.0.1", port=5000, debug=False)
