"""Shim to maintain backward-compatibility with 'python app.py'."""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
