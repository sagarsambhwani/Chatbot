import os
import requests

def download_file(url, target_path):
    print(f"Downloading {url} -> {target_path}...")
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print(f"Downloaded {target_path} ({os.path.getsize(target_path) / 1024 / 1024:.2f} MB)")

def setup_voice():
    base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
    model_name = "en_US-lessac-medium"
    
    model_path = os.path.join("voices", f"{model_name}.onnx")
    config_path = os.path.join("voices", f"{model_name}.onnx.json")

    if not os.path.exists(model_path):
        download_file(f"{base_url}/{model_name}.onnx", model_path)
    if not os.path.exists(config_path):
        download_file(f"{base_url}/{model_name}.onnx.json", config_path)
    
    print("Voice model setup complete!")

if __name__ == "__main__":
    setup_voice()
