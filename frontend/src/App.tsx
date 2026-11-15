import React, { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { MessageItem } from './components/MessageItem';
import { ChatInput } from './components/ChatInput';
import { Session, Message, SystemStatus } from './types/chat';
import {
    fetchSessions,
    fetchSessionHistory,
    createSession,
    deleteSession,
    fetchSystemStatus,
} from './services/api';
import { streamChat } from './services/sse';

export const App: React.FC = () => {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [status, setStatus] = useState<SystemStatus | null>(null);
    const [isStreaming, setIsStreaming] = useState(false);
    const [streamStatus, setStreamStatus] = useState<string>('');
    const scrollRef = useRef<HTMLDivElement>(null);

    // Poll system health
    useEffect(() => {
        fetchSystemStatus().then(setStatus).catch(console.error);
        const interval = setInterval(() => {
            fetchSystemStatus().then(setStatus).catch(console.error);
        }, 4000);
        return () => clearInterval(interval);
    }, []);

    // Load session list on start
    useEffect(() => {
        loadSessions();
    }, []);

    const loadSessions = async () => {
        try {
            const data = await fetchSessions();
            setSessions(data);
            if (data.length > 0 && !activeSessionId) {
                selectSession(data[0].id);
            }
        } catch (err) {
            console.error(err);
        }
    };

    const selectSession = async (id: string) => {
        setActiveSessionId(id);
        try {
            const { messages } = await fetchSessionHistory(id);
            setMessages(messages);
        } catch (err) {
            console.error(err);
        }
    };

    const handleNewChat = async () => {
        try {
            const newSession = await createSession();
            setSessions([newSession, ...sessions]);
            setActiveSessionId(newSession.id);
            setMessages([]);
        } catch (err) {
            console.error(err);
        }
    };

    const handleDeleteSession = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await deleteSession(id);
            const remaining = sessions.filter((s) => s.id !== id);
            setSessions(remaining);
            if (activeSessionId === id) {
                if (remaining.length > 0) selectSession(remaining[0].id);
                else {
                    setActiveSessionId(null);
                    setMessages([]);
                }
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleSend = async (
        text: string,
        useWeb: boolean,
        useRag: boolean,
        sttSeconds: number
    ) => {
        const userMsg: Message = {
            session_id: activeSessionId || '',
            role: 'user',
            content: text,
        };

        setMessages((prev) => [...prev, userMsg]);
        setIsStreaming(true);
        setStreamStatus('');

        // Prepare assistant placeholder
        const assistantIndex = messages.length + 1;
        let accumulatedText = '';

        try {
            await streamChat(
                {
                    message: text,
                    session_id: activeSessionId || undefined,
                    use_web: useWeb,
                    use_rag: useRag,
                    enable_tts: true,
                    stt_seconds: sttSeconds,
                },
                (event) => {
                    if (event.type === 'status') {
                        setStreamStatus(event.message);
                    } else if (event.type === 'metadata') {
                        // Update activeSessionId if backend created a new one
                        if (!activeSessionId && event.session_id) {
                            setActiveSessionId(event.session_id);
                            loadSessions();
                        }
                        // Attach telemetry to the user's message
                        setMessages((prev) =>
                            prev.map((m, idx) =>
                                idx === prev.length - 1 && m.role === 'user'
                                    ? {
                                        ...m,
                                        intent: event.analysis?.intent,
                                        needs_code: event.analysis?.needs_code,
                                        needs_web_search: event.analysis?.needs_web_search,
                                        needs_rag: event.analysis?.needs_rag,
                                    }
                                    : m
                            )
                        );
                    } else if (event.type === 'token') {
                        accumulatedText += event.token;
                        setStreamStatus('');
                        setMessages((prev) => {
                            const updated = [...prev];
                            updated[assistantIndex] = {
                                session_id: activeSessionId || '',
                                role: 'assistant',
                                content: accumulatedText,
                            };
                            return updated;
                        });
                    } else if (event.type === 'done') {
                        setMessages((prev) => {
                            const updated = [...prev];
                            if (updated[assistantIndex]) {
                                updated[assistantIndex].latencies = event.latencies;
                            }
                            return updated;
                        });
                    } else if (event.type === 'audio') {
                        setMessages((prev) => {
                            const updated = [...prev];
                            if (updated[assistantIndex]) {
                                updated[assistantIndex].audio_url = event.audio_url;
                            }
                            return updated;
                        });
                        // Autoplay synthetic speech
                        const audio = new Audio(event.audio_url);
                        audio.play().catch((e) => console.log('Audio autoplay prevented:', e));
                    }
                }
            );
        } catch (err) {
            console.error(err);
        } finally {
            setIsStreaming(false);
            setStreamStatus('');
        }
    };

    useEffect(() => {
        scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, streamStatus]);

    return (
        <div className="flex h-screen bg-zinc-950 text-zinc-100 font-sans">
            <Sidebar
                sessions={sessions}
                activeSessionId={activeSessionId}
                status={status}
                onSelectSession={selectSession}
                onNewChat={handleNewChat}
                onDeleteSession={handleDeleteSession}
            />

            <main className="flex-1 flex flex-col h-full overflow-hidden">
                <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                    {messages.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-zinc-500">
                            <h3 className="text-xl font-medium text-zinc-300 mb-2">Local AI Assistant</h3>
                            <p className="text-sm">FastAPI + Ollama GPU + Piper Voice + SQLite Persistence</p>
                        </div>
                    ) : (
                        messages.map((msg, i) => <MessageItem key={i} message={msg} />)
                    )}

                    {streamStatus && (
                        <div className="text-xs text-indigo-400 italic flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
                            {streamStatus}
                        </div>
                    )}
                    <div ref={scrollRef} />
                </div>

                <ChatInput onSend={handleSend} disabled={isStreaming} />
            </main>
        </div>
    );
};

export default App;