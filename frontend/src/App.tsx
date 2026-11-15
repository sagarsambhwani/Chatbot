import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { MessageItem } from './components/MessageItem';
import { ChatInput } from './components/ChatInput';
import { DocModal } from './components/DocModal';
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
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isDocModalOpen, setIsDocModalOpen] = useState(false);
  const [userHasScrolledUp, setUserHasScrolledUp] = useState(false);
  const [quickInput, setQuickInput] = useState('');

  const chatContainerRef = useRef<HTMLDivElement>(null);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  // Poll system health
  useEffect(() => {
    fetchSystemStatus().then(setStatus).catch(console.error);
    const interval = setInterval(() => {
      fetchSystemStatus().then(setStatus).catch(console.error);
    }, 5000);
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
      scrollToBottom(true);
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
      scrollToBottom(true);
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

  const scrollToBottom = (force = false) => {
    if (!chatContainerRef.current) return;
    if (force || !userHasScrolledUp) {
      if (force) {
        chatContainerRef.current.scrollTo({
          top: chatContainerRef.current.scrollHeight,
          behavior: 'smooth',
        });
      } else {
        chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
      }
    }
  };

  const handleScroll = () => {
    if (!chatContainerRef.current) return;
    const { scrollHeight, scrollTop, clientHeight } = chatContainerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    setUserHasScrolledUp(distanceFromBottom > 100);
  };

  const handleSend = async (
    text: string,
    useWeb: boolean,
    useRag: boolean,
    enableTts: boolean,
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
    setUserHasScrolledUp(false);
    scrollToBottom(true);

    const assistantIndex = messages.length + 1;
    let accumulatedText = '';

    try {
      await streamChat(
        {
          message: text,
          session_id: activeSessionId || undefined,
          use_web: useWeb,
          use_rag: useRag,
          enable_tts: enableTts,
          stt_seconds: sttSeconds,
        },
        (event) => {
          if (event.type === 'status') {
            setStreamStatus(event.message);
          } else if (event.type === 'metadata') {
            if (!activeSessionId && event.session_id) {
              setActiveSessionId(event.session_id);
              loadSessions();
            }
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
            scrollToBottom(false);
          } else if (event.type === 'done') {
            setMessages((prev) => {
              const updated = [...prev];
              if (updated[assistantIndex]) {
                updated[assistantIndex].latencies = event.latencies;
              }
              return updated;
            });
            scrollToBottom(false);
          } else if (event.type === 'audio') {
            setMessages((prev) => {
              const updated = [...prev];
              if (updated[assistantIndex]) {
                updated[assistantIndex].audio_url = event.audio_url;
              }
              return updated;
            });
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
      scrollToBottom(false);
    }
  };

  const handleUseQuickPrompt = (promptText: string) => {
    setQuickInput(promptText);
    handleSend(promptText, true, true, true, 0);
    setQuickInput('');
  };

  return (
    <div className="flex h-screen h-[100dvh] w-screen overflow-hidden bg-linen-canvas text-linen-text font-sans antialiased selection:bg-[#ebdcc8]">
      {/* Sidebar Drawer */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        status={status}
        isOpen={isSidebarOpen}
        onSelectSession={selectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
      />

      <div className="flex-1 min-h-0 flex flex-col relative overflow-hidden bg-linen-canvas">
        {/* Top Breadcrumb Header */}
        <Header
          status={status}
          onOpenDocs={() => setIsDocModalOpen(true)}
          onNewChat={handleNewChat}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          isSidebarOpen={isSidebarOpen}
        />

        {/* Messages Canvas */}
        <main
          ref={chatContainerRef}
          onScroll={handleScroll}
          className="flex-1 min-h-0 overflow-y-auto px-4 md:px-6 py-6 scroll-smooth relative"
        >
          <div className="max-w-3xl mx-auto w-full space-y-7 pb-6">
            {messages.length === 0 ? (
              <div className="text-center pt-16 pb-8 space-y-5">
                <div className="w-12 h-12 mx-auto rounded-2xl bg-linen-surfaceAlt border border-linen-border flex items-center justify-center shadow-sm">
                  <i className="fa-solid fa-sparkles text-linen-text text-xl"></i>
                </div>
                <div className="space-y-1">
                  <h2 className="text-xl font-medium text-linen-text">Local Ollama Voice Assistant</h2>
                  <p className="text-xs text-linen-muted">
                    Running 100% locally on your machine • Qwen2.5 on NVIDIA GTX 1650
                  </p>
                </div>

                <div className="flex flex-wrap justify-center gap-2 pt-2 max-w-xl mx-auto text-xs">
                  <button
                    onClick={() => handleUseQuickPrompt('What are the latest discoveries from the James Webb Telescope?')}
                    className="px-3.5 py-2 rounded-xl bg-linen-surface hover:bg-linen-surfaceAlt border border-linen-border text-linen-text transition shadow-sm text-left"
                  >
                    🔭 Latest Space News
                  </button>
                  <button
                    onClick={() => handleUseQuickPrompt('Summarize the system specs and architecture from my local docs.')}
                    className="px-3.5 py-2 rounded-xl bg-linen-surface hover:bg-linen-surfaceAlt border border-linen-border text-linen-text transition shadow-sm text-left"
                  >
                    📄 Query Local Docs
                  </button>
                  <button
                    onClick={() => handleUseQuickPrompt('Tell me a short funny joke.')}
                    className="px-3.5 py-2 rounded-xl bg-linen-surface hover:bg-linen-surfaceAlt border border-linen-border text-linen-text transition shadow-sm text-left"
                  >
                    ✨ Instant Chitchat
                  </button>
                </div>
              </div>
            ) : (
              messages.map((msg, i) => (
                <MessageItem
                  key={msg.id || i}
                  message={msg}
                  isStreaming={isStreaming && i === messages.length - 1 && msg.role === 'assistant'}
                />
              ))
            )}

            {streamStatus && (
              <div className="text-xs text-linen-muted flex items-center gap-2 italic">
                <i className="fa-solid fa-compass fa-spin text-[10px]"></i>
                {streamStatus}
              </div>
            )}
            <div ref={scrollAnchorRef} className="h-4" />
          </div>
        </main>

        {/* Scroll To Bottom Floating Button */}
        {userHasScrolledUp && (
          <button
            onClick={() => scrollToBottom(true)}
            className="absolute bottom-28 left-1/2 -translate-x-1/2 w-8 h-8 rounded-full bg-white border border-linen-border shadow-md hover:shadow-lg text-linen-muted hover:text-linen-text flex items-center justify-center transition-all duration-200 z-30"
            title="Scroll to bottom"
          >
            <i className="fa-solid fa-arrow-down text-xs"></i>
          </button>
        )}

        {/* Floating Omnibar Input Capsule */}
        <ChatInput
          onSend={handleSend}
          disabled={isStreaming}
          onOpenDocs={() => setIsDocModalOpen(true)}
          initialValue={quickInput}
        />
      </div>

      {/* Knowledge Base Modal */}
      <DocModal
        isOpen={isDocModalOpen}
        onClose={() => setIsDocModalOpen(false)}
        onDocsChanged={() => fetchSystemStatus().then(setStatus).catch(console.error)}
      />
    </div>
  );
};

export default App;
