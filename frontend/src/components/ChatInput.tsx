import React, { useState, useRef, useEffect } from 'react';
import { transcribeAudio } from '../services/api';

interface ChatInputProps {
  onSend: (text: string, useWeb: boolean, useRag: boolean, enableTts: boolean, sttTime: number) => void;
  disabled: boolean;
  onOpenDocs: () => void;
  initialValue?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled,
  onOpenDocs,
  initialValue = '',
}) => {
  const [text, setText] = useState(initialValue);
  const [useWeb, setUseWeb] = useState(true);
  const [useRag, setUseRag] = useState(true);
  const [useTts, setUseTts] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    if (initialValue) {
      setText(initialValue);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
      }
    }
  }, [initialValue]);

  const handleSend = () => {
    if (!text.trim() || disabled) return;
    onSend(text.trim(), useWeb, useRag, useTts, 0);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
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

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        recorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
          stream.getTracks().forEach((track) => track.stop());
          try {
            const { text: transcribed, stt_seconds } = await transcribeAudio(audioBlob);
            if (transcribed.trim()) {
              setText(transcribed.trim());
              onSend(transcribed.trim(), useWeb, useRag, useTts, stt_seconds || 0.0);
              setText('');
            }
          } catch (err) {
            console.error('STT Error:', err);
          }
        };

        recorder.start();
        mediaRecorderRef.current = recorder;
        setIsRecording(true);
      } catch (err) {
        alert('Microphone error: ' + (err as Error).message);
      }
    }
  };

  return (
    <footer className="flex-shrink-0 px-4 pt-2 pb-4 bg-linen-canvas border-t border-linen-border/40 z-20">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white border border-[#e5ded3] rounded-3xl p-3 shadow-md focus-within:shadow-lg focus-within:border-[#cfc6b8] transition-all duration-200">
          
          {/* Textarea Input Row */}
          <div className="px-2 pt-1">
            <textarea
              ref={textareaRef}
              rows={1}
              value={text}
              onChange={handleTextareaInput}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder="Ask anything, @ to mention, / for actions"
              className="w-full bg-transparent text-linen-text placeholder-[#8e867f] text-sm focus:outline-none resize-none max-h-40 leading-relaxed font-sans"
            />
          </div>

          {/* Bottom Capsule Row: Left Actions + Model Tag, Right Tools + Send */}
          <div className="flex items-center justify-between pt-2 px-1">
            
            {/* Left: '+' Button & Model Tag */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onOpenDocs}
                className="w-6 h-6 rounded-md hover:bg-linen-surfaceAlt text-linen-muted hover:text-linen-text flex items-center justify-center transition"
                title="Add document to knowledge base"
              >
                <i className="fa-solid fa-plus text-xs"></i>
              </button>

              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-xs font-medium text-linen-text select-none cursor-default">
                <span>Qwen 2.5 1.5B (GPU)</span>
                <i className="fa-solid fa-chevron-up text-[9px] text-linen-muted"></i>
              </div>
            </div>

            {/* Right: Feature Toggles + Mic + Dark Circular Send Button */}
            <div className="flex items-center gap-2">
              
              {/* Web Search Toggle Pill */}
              <button
                type="button"
                onClick={() => setUseWeb(!useWeb)}
                className={`px-2 py-0.5 rounded-full border text-[11px] font-medium flex items-center gap-1 transition select-none ${
                  useWeb
                    ? 'border-sky-300 bg-sky-50 text-sky-700 hover:bg-sky-100'
                    : 'border-linen-border bg-linen-surfaceAlt/60 text-linen-muted hover:bg-linen-surfaceAlt opacity-50'
                }`}
              >
                <i className="fa-solid fa-globe text-[10px]"></i>
                <span>Search</span>
              </button>

              {/* Document RAG Toggle Pill */}
              <button
                type="button"
                onClick={() => setUseRag(!useRag)}
                className={`px-2 py-0.5 rounded-full border text-[11px] font-medium flex items-center gap-1 transition select-none ${
                  useRag
                    ? 'border-emerald-300 bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                    : 'border-linen-border bg-linen-surfaceAlt/60 text-linen-muted hover:bg-linen-surfaceAlt opacity-50'
                }`}
              >
                <i className="fa-solid fa-book-bookmark text-[10px]"></i>
                <span>Docs</span>
              </button>

              {/* Spoken Voice Toggle Pill */}
              <button
                type="button"
                onClick={() => setUseTts(!useTts)}
                className={`px-2 py-0.5 rounded-full border text-[11px] font-medium flex items-center gap-1 transition select-none ${
                  useTts
                    ? 'border-violet-300 bg-violet-50 text-violet-700 hover:bg-violet-100'
                    : 'border-linen-border bg-linen-surfaceAlt/60 text-linen-muted hover:bg-linen-surfaceAlt opacity-50'
                }`}
              >
                <i className="fa-solid fa-volume-high text-[10px]"></i>
                <span>Voice</span>
              </button>

              {/* Microphone Icon */}
              <button
                type="button"
                onClick={toggleRecording}
                title="Speak with microphone (Faster-Whisper)"
                className={`w-7 h-7 rounded-full text-linen-muted hover:text-linen-text hover:bg-linen-surfaceAlt flex items-center justify-center transition ${
                  isRecording ? 'recording-active' : ''
                }`}
              >
                <i className={`fa-solid ${isRecording ? 'fa-stop text-white' : 'fa-microphone text-xs'}`}></i>
              </button>

              {/* Dark Circular Action Button */}
              <button
                type="button"
                onClick={handleSend}
                disabled={!text.trim() || disabled}
                title="Send message"
                className="w-7 h-7 rounded-full bg-[#2d2926] text-white hover:bg-[#423b35] flex items-center justify-center transition shadow-sm disabled:opacity-40"
              >
                <i className="fa-solid fa-sparkles text-[11px]"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};
