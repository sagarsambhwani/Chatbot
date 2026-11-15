export interface Session {
    id: string;
    title: string;
    created_at: string;
    updated_at: string;
}

export interface Latencies {
    analyzer_seconds?: number;
    search_seconds?: number;
    rag_seconds?: number;
    llm_seconds?: number;
    tokens_per_sec?: number;
    ttft_seconds?: number;
    stt_seconds?: number;
    tts_seconds?: number;
    total_seconds?: number;
}

export interface Message {
    id?: number | string;
    session_id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    intent?: string;
    needs_web_search?: boolean;
    needs_rag?: boolean;
    needs_code?: boolean;
    desired_depth?: string;
    audio_url?: string;
    latencies?: Latencies;
    created_at?: string;
}

export interface ChatRequest {
    message: string;
    session_id?: string;
    use_web?: boolean;
    use_rag?: boolean;
    enable_tts?: boolean;
    stt_seconds?: number;
}

export interface SystemStatus {
    vram: string;
    llm_model: string;
    embed_model: string;
    rag_docs_count: number;
}

export type SSEEvent =
    | { type: 'status'; message: string; session_id?: string }
    | {
        type: 'metadata';
        session_id: string;
        analysis?: {
            intent?: string;
            needs_web_search?: boolean;
            needs_rag?: boolean;
            needs_code?: boolean;
            desired_depth?: string;
        };
        web_sources?: Array<{ title: string; url: string; snippet: string }>;
        doc_sources?: Array<{ filename: string; text: string; score: number }>;
        latencies?: Latencies;
    }
    | { type: 'token'; token: string; session_id?: string }
    | { type: 'done'; session_id: string; answer: string; latencies?: Latencies }
    | { type: 'audio'; session_id: string; audio_url: string; tts_seconds: number }
    | { type: 'error'; error: string; session_id?: string };