import React from 'react';
import { Message } from '../types/chat';

interface MessageItemProps {
    message: Message;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
    const isUser = message.role === 'user';

    return (
        <div className={`flex flex-col mb-4 ${isUser ? 'items-end' : 'items-start'}`}>
            <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 leading-relaxed text-sm ${isUser
                    ? 'bg-indigo-600 text-white rounded-br-none'
                    : 'bg-zinc-800/80 border border-zinc-700/50 text-zinc-100 rounded-bl-none shadow-sm'
                    }`}
            >
                <div className="whitespace-pre-wrap font-sans">{message.content}</div>

                {/* Telemetry & Routing Badges for User Query */}
                {isUser && message.intent && (
                    <div className="mt-2 flex flex-wrap gap-1.5 pt-1.5 border-t border-indigo-500/40 text-[11px]">
                        <span className="bg-indigo-700/80 px-2 py-0.5 rounded font-mono">
                            intent: {message.intent}
                        </span>
                        {message.needs_code && (
                            <span className="bg-amber-600/60 px-1.5 py-0.5 rounded">code</span>
                        )}
                        {message.needs_web_search && (
                            <span className="bg-blue-600/60 px-1.5 py-0.5 rounded">web</span>
                        )}
                        {message.needs_rag && (
                            <span className="bg-purple-600/60 px-1.5 py-0.5 rounded">rag</span>
                        )}
                    </div>
                )}

                {/* Performance Latency Bar & Audio Player for Assistant */}
                {!isUser && (
                    <div className="mt-2.5 pt-2 border-t border-zinc-700/40 flex flex-wrap items-center gap-3 text-[11px] text-zinc-400">
                        {message.latencies?.tokens_per_sec && (
                            <span className="text-emerald-400 font-mono">
                                ⚡ {message.latencies.tokens_per_sec} t/s
                            </span>
                        )}
                        {message.latencies?.llm_seconds && (
                            <span>LLM: {message.latencies.llm_seconds}s</span>
                        )}
                        {message.latencies?.tts_seconds && (
                            <span>TTS: {message.latencies.tts_seconds}s</span>
                        )}

                        {message.audio_url && (
                            <audio
                                controls
                                src={message.audio_url}
                                className="h-6 w-48 mt-1 block accent-indigo-500"
                            />
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};