import React, { useState, useRef } from 'react';
import { transcribeAudio } from '../services/api';

interface ChatInputProps {
    onSend: (text: string, useWeb: boolean, useRag: boolean, sttTime: number) => void;
    disabled: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled }) => {
    const [text, setText] = useState('');
    const [useWeb, setUseWeb] = useState(true);
    const [useRag, setUseRag] = useState(true);
    const [isRecording, setIsRecording] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);

    const handleSend = () => {
        if (!text.trim() || disabled) return;
        onSend(text.trim(), useWeb, useRag, 0);
        setText('');
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const toggleRecording = async () => {
        if (isRecording) {
            mediaRecorderRef.current?.stop();
            setIsRecording(false);
        } else {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                const recorder = new MediaRecorder(stream);
                audioChunksRef.current = [];

                recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
                recorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
                    try {
                        const { text: transcribed, stt_seconds } = await transcribeAudio(audioBlob);
                        if (transcribed.trim()) {
                            onSend(transcribed.trim(), useWeb, useRag, stt_seconds);
                        }
                    } catch (err) {
                        console.error('STT Error:', err);
                    }
                };

                recorder.start();
                mediaRecorderRef.current = recorder;
                setIsRecording(true);
            } catch (err) {
                console.error('Mic access denied:', err);
            }
        }
    };

    return (
        <div className="p-4 border-t border-zinc-800 bg-zinc-900/60">
            <div className="flex items-center gap-2 mb-2">
                <button
                    type="button"
                    onClick={() => setUseWeb(!useWeb)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition ${useWeb
                        ? 'bg-blue-950/60 border-blue-500/50 text-blue-300'
                        : 'bg-zinc-800/40 border-zinc-700 text-zinc-500'
                        }`}
                >
                    🌐 Web Search
                </button>
                <button
                    type="button"
                    onClick={() => setUseRag(!useRag)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition ${useRag
                        ? 'bg-purple-950/60 border-purple-500/50 text-purple-300'
                        : 'bg-zinc-800/40 border-zinc-700 text-zinc-500'
                        }`}
                >
                    📄 Document RAG
                </button>
            </div>

            <div className="relative flex items-center bg-zinc-800 rounded-xl border border-zinc-700 focus-within:border-indigo-500 transition">
                <textarea
                    rows={1}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask a question or request code..."
                    disabled={disabled}
                    className="w-full bg-transparent resize-none px-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none"
                />

                <div className="flex items-center gap-1.5 pr-2">
                    <button
                        type="button"
                        onClick={toggleRecording}
                        className={`p-2 rounded-lg text-sm transition ${isRecording
                            ? 'bg-red-600 text-white animate-pulse'
                            : 'text-zinc-400 hover:text-white hover:bg-zinc-700'
                            }`}
                        title={isRecording ? 'Stop recording' : 'Voice input (Whisper)'}
                    >
                        🎤
                    </button>
                    <button
                        type="button"
                        onClick={handleSend}
                        disabled={!text.trim() || disabled}
                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 rounded-lg text-sm text-white font-medium transition"
                    >
                        Send
                    </button>
                </div>
            </div>
        </div>
    );
};