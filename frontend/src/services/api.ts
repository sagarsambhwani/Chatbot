import { Session, Message, SystemStatus } from "../types/chat";

export async function fetchSystemStatus(): Promise<SystemStatus> {
    const res = await fetch('/api/system_status');
    if (!res.ok) throw new Error('Failed to fetch system status');
    return res.json();
}

export async function fetchSessions(): Promise<Session[]> {
    const res = await fetch('/api/sessions');
    if (!res.ok) throw new Error('Failed to fetch sessions');
    return res.json();
}

export async function createSession(title = 'New Chat'): Promise<Session> {
    const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
    })
    return res.json();
}

export async function fetchSessionHistory(sessionId: string): Promise<{ session: Session; messages: Message[] }> {
    const res = await fetch(`/api/sessions/${sessionId}`);
    if (!res.ok) throw new Error('Failed to fetch session history');
    return res.json();
}

export async function updateSessionTitle(sessionId: string, title: string): Promise<Session> {
    const res = await fetch(`/api/sessions/${sessionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
    });
    if (!res.ok) throw new Error('Failed to update session');
    return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
    const res = await fetch(`/api/sessions/${sessionId}`, {
        method: 'DELETE'
    });
    if (!res.ok) throw new Error('Failed to delete session');
}

export async function transcribeAudio(audioBlob: Blob): Promise<{ text: string; stt_seconds: number }> {
    const formData = new FormData(); formData.append('audio', audioBlob, 'recording.wav');
    const res = await fetch('/api/transcribe', {
        method: 'POST',
        body: formData,
    });
    if (!res.ok) throw new Error('Transcription failed');
    return res.json();
}

export async function uploadDocument(file: File): Promise<{ message: string; total_chunks: number }> {
    const formData = new FormData(); formData.append('file', file);
    const res = await fetch('/api/documents', {
        method: 'POST',
        body: formData,
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
}
