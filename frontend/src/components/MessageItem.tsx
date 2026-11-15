import React, { useState } from 'react';
import { marked } from 'marked';
import { Message } from '../types/chat';

interface MessageItemProps {
  message: Message;
  isStreaming?: boolean;
}

function parseThinking(content: string) {
  const match = content.match(/<think>([\s\S]*?)(?:<\/think>|$)/i);
  if (!match) {
    return { thought: null, answer: content, isThinking: false };
  }
  const thought = match[1].trim();
  const hasClosed = /<\/think>/i.test(content);
  const answer = content.replace(/<think>[\s\S]*?(?:<\/think>|$)/i, '').trim();
  return { thought, answer, isThinking: !hasClosed };
}

export const MessageItem: React.FC<MessageItemProps> = ({ message, isStreaming = false }) => {
  const isUser = message.role === 'user';
  const [showDetails, setShowDetails] = useState(false);
  const [showThought, setShowThought] = useState(false);
  const [copied, setCopied] = useState(false);

  const { thought, answer, isThinking } = parseThinking(message.content || '');

  const handleCopy = () => {
    navigator.clipboard.writeText(answer || message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePlayAudio = () => {
    if (message.audio_url) {
      const audio = new Audio(message.audio_url);
      audio.play().catch((e) => console.log('Audio playback note:', e));
    }
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="bg-linen-userBubble border border-linen-border/60 text-linen-text rounded-2xl px-4 py-2.5 text-sm max-w-[85%] sm:max-w-[75%] leading-relaxed shadow-sm">
          <div className="whitespace-pre-wrap">{message.content}</div>
          {message.intent && (
            <div className="mt-1.5 pt-1.5 border-t border-linen-border/40 flex flex-wrap items-center gap-1.5 text-[10px] text-linen-muted">
              <span className="bg-linen-codeBg text-linen-codeText px-1.5 py-0.5 rounded font-mono">
                {message.intent}
              </span>
              {message.needs_code && <span className="text-amber-700">code</span>}
              {message.needs_web_search && <span className="text-sky-700">web</span>}
              {message.needs_rag && <span className="text-emerald-700">rag</span>}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Assistant Message
  const hasLatencies = message.latencies && Object.keys(message.latencies).length > 0;
  const displayContent = answer || (isThinking ? '' : message.content || '');
  const rawHtml = marked.parse(displayContent) as string;

  return (
    <div className="space-y-3 mb-6">
      {/* Collapsible Step / Status Pill */}
      {hasLatencies && (
        <div>
          <button
            type="button"
            onClick={() => setShowDetails(!showDetails)}
            className="text-xs text-linen-muted hover:text-linen-text cursor-pointer select-none flex items-center gap-1.5 transition"
          >
            <span className="flex items-center gap-1.5">
              <i className="fa-solid fa-sparkles text-[10px] text-amber-600"></i>
              {message.latencies?.llm_seconds
                ? `Generated in ${message.latencies.llm_seconds}s (${message.latencies.tokens_per_sec || 0} t/s)`
                : 'Thinking...'}
            </span>
            <i className={`fa-solid text-[9px] ${showDetails ? 'fa-chevron-down' : 'fa-chevron-right'}`}></i>
          </button>

          {showDetails && (
            <div className="mt-2 text-xs text-linen-muted bg-linen-surfaceAlt/70 border border-linen-border rounded-xl p-3 space-y-1">
              <div className="flex flex-wrap gap-x-4 gap-y-1">
                {message.latencies?.analyzer_seconds && (
                  <span>Router: {message.latencies.analyzer_seconds}s</span>
                )}
                {message.latencies?.search_seconds && message.latencies.search_seconds > 0 && (
                  <span>Web Search: {message.latencies.search_seconds}s</span>
                )}
                {message.latencies?.rag_seconds && message.latencies.rag_seconds > 0 && (
                  <span>RAG Search: {message.latencies.rag_seconds}s</span>
                )}
                {message.latencies?.ttft_seconds && (
                  <span>TTFT: {message.latencies.ttft_seconds}s</span>
                )}
                {message.latencies?.tts_seconds && message.latencies.tts_seconds > 0 && (
                  <span>Kokoro TTS: {message.latencies.tts_seconds}s</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Thought Process Scratchpad Accordion */}
      {thought && (
        <div className="mb-2">
          <button
            type="button"
            onClick={() => setShowThought(!showThought)}
            className="text-[11px] text-linen-muted hover:text-linen-text cursor-pointer select-none flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-linen-surfaceAlt/70 border border-linen-border/70 transition"
          >
            <i className="fa-solid fa-brain text-[10px] text-amber-600"></i>
            <span>Thought Process</span>
            {isThinking && (
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse ml-0.5"></span>
            )}
            <i className={`fa-solid text-[8px] ml-1 ${showThought || isThinking ? 'fa-chevron-down' : 'fa-chevron-right'}`}></i>
          </button>
          {(showThought || isThinking) && (
            <div className="mt-1.5 px-3.5 py-2 text-linen-muted bg-linen-surfaceAlt/40 border border-linen-border/60 rounded-xl font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
              {thought}
              {isThinking && <span className="stream-cursor ml-1"></span>}
            </div>
          )}
        </div>
      )}

      {/* Formatted Markdown Content */}
      <div className="prose-antigravity">
        <div dangerouslySetInnerHTML={{ __html: rawHtml }} />
        {isStreaming && !isThinking && <span className="stream-cursor"></span>}
      </div>

      {/* Action Buttons: Copy, Replay Audio, etc. */}
      {!isStreaming && (
        <div className="flex flex-wrap items-center gap-3 pt-2 text-xs text-linen-muted select-none border-t border-linen-border/40">
          <button
            onClick={handleCopy}
            className="hover:text-linen-text flex items-center gap-1.5 transition"
          >
            <i className={`fa-regular ${copied ? 'fa-check text-emerald-600' : 'fa-copy'}`}></i>
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {message.audio_url && (
            <button
              onClick={handlePlayAudio}
              className="hover:text-linen-text flex items-center gap-1.5 transition"
              title="Replay synthetic voice audio"
            >
              <i className="fa-solid fa-volume-high text-violet-600"></i>
              <span>Replay Audio</span>
            </button>
          )}

          {message.latencies?.tokens_per_sec && (
            <span className="text-emerald-700 font-mono text-[11px] ml-auto">
              ⚡ {message.latencies.tokens_per_sec} t/s
            </span>
          )}
        </div>
      )}
    </div>
  );
};
