"""Background sentence boundary audio streamer."""

import re, queue, threading
from typing import Optional, Callable
from backend.deps import tts

class AudioStreamQueue:
    def __init__(self, session_id: str, emit_fn: Callable, enable_tts: bool):
        self.session_id, self.emit = session_id, emit_fn
        self.enable_tts, self.buffer = enable_tts, ""
        self.task_q = queue.Queue()
        self.audio_urls, self.total_time = [], 0.0
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        if enable_tts: self.worker.start()

    def _worker_loop(self):
        idx = 0
        while True:
            sent = self.task_q.get()
            if sent is None: break
            url, t = tts.synthesize(sent)
            if url:
                self.audio_urls.append(url)
                self.total_time += t
                self.emit({"type": "audio_chunk", "session_id": self.session_id, "audio_url": url, "chunk_index": idx})
                idx += 1
            self.task_q.task_done()

    def feed(self, token: str):
        if not self.enable_tts: return
        self.buffer += token
        if "<think>" in self.buffer.lower() and "</think>" not in self.buffer.lower(): return
        clean = re.sub(r'<think>[\s\S]*?</think>', '', self.buffer, flags=re.IGNORECASE).lstrip()
        match = re.search(r'([.!?\n])\s+', clean)
        while match:
            idx = match.end()
            sent, clean = clean[:idx].strip(), clean[idx:]
            self.buffer = clean
            if len(sent) >= 8: self.task_q.put(sent)
            match = re.search(r'([.!?\n])\s+', clean)

    def finish(self) -> Optional[str]:
        if not self.enable_tts: return ""
        clean = re.sub(r'<think>[\s\S]*?(?:</think>|$)', '', self.buffer, flags=re.IGNORECASE).strip()
        if len(clean) >= 3: self.task_q.put(clean)
        self.task_q.put(None)
        self.worker.join(timeout=15.0)
        return self.audio_urls[0] if self.audio_urls else ""
