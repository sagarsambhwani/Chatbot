import React from 'react';
import { SystemStatus } from '../types/chat';

interface HeaderProps {
  status: SystemStatus | null;
  onOpenDocs: () => void;
  onNewChat: () => void;
  onToggleSidebar: () => void;
  isSidebarOpen: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  onOpenDocs,
  onNewChat,
  onToggleSidebar,
  isSidebarOpen,
}) => {
  return (
    <header className="h-12 px-6 flex items-center justify-between border-b border-linen-border/70 bg-linen-canvas/90 backdrop-blur z-20 flex-shrink-0 select-none">
      <div className="flex items-center gap-2 text-xs text-linen-muted">
        <button
          onClick={onToggleSidebar}
          className={`p-1.5 rounded-lg border transition mr-1 flex items-center gap-1.5 ${
            isSidebarOpen
              ? 'bg-linen-surfaceAlt border-linen-border text-linen-text'
              : 'hover:bg-linen-surfaceAlt/60 border-transparent text-linen-muted hover:text-linen-text'
          }`}
          title="Toggle chat history sidebar"
        >
          <i className="fa-solid fa-bars text-xs"></i>
          <span className="text-[11px] font-medium hidden sm:inline">Threads</span>
        </button>
        <span className="font-medium text-linen-text/80">ollama</span>
        <span>/</span>
        <span className="font-normal text-linen-muted">Local Ollama Voice Assistant</span>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-linen-surfaceAlt border border-linen-border text-[11px] text-linen-muted">
          <i className="fa-solid fa-microchip text-emerald-600 text-[10px]"></i>
          <span className="text-linen-text font-medium">GTX 1650</span>
          <span className="text-linen-border">|</span>
          <span className="font-mono text-linen-text">VRAM: {status?.vram || 'checking...'}</span>
        </div>

        <button
          onClick={onOpenDocs}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-linen-surface hover:bg-linen-surfaceAlt border border-linen-border text-xs text-linen-text transition shadow-sm"
          title="Knowledge Base"
        >
          <i className="fa-regular fa-folder-open text-amber-600 text-[11px]"></i>
          <span className="text-[11px] font-medium">Docs</span>
          <span className="ml-0.5 px-1.5 py-0.2 rounded-full bg-linen-codeBg text-linen-codeText text-[10px] font-mono">
            {status?.rag_docs_count ?? 1}
          </span>
        </button>

        <button
          onClick={onNewChat}
          className="p-1.5 rounded-lg text-linen-muted hover:text-linen-text hover:bg-linen-surfaceAlt transition"
          title="New chat"
        >
          <i className="fa-solid fa-rotate-right text-xs"></i>
        </button>
      </div>
    </header>
  );
};

