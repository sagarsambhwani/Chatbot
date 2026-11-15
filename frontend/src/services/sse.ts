import { ChatRequest, SSEEvent } from '../types/chat';

export async function streamChat(
    req: ChatRequest,
    onEvent: (event: SSEEvent) => void,
    signal?: AbortSignal
): Promise<void> {
    const response = await fetch('/api/chat_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
        signal,
    });

    if (!response.ok || !response.body) {
        throw new Error(`Stream error: ${response.status} ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep trailing partial chunk

        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('data: ')) {
                try {
                    const payload = JSON.parse(trimmed.slice(6)) as SSEEvent;
                    onEvent(payload);
                } catch (err) {
                    console.warn('Failed to parse SSE event chunk:', trimmed, err);
                }
            }
        }
    }
}