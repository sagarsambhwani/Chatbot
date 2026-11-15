import React from 'react';
import { Session, SystemStatus } from '../types/chat';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  status: SystemStatus | null;
  isOpen: boolean;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string, e: React.MouseEvent) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  status,
  isOpen,
  onSelectSession,
  onNewChat,
  onDeleteSession,
}) => {
  if (!isOpen) return null;

  return (
    <aside className="w-64 bg-linen-surface border-r border-linen-border/70 flex flex-col h-full text-linen-text z-20 flex-shrink-0 select-none shadow-sm transition-all duration-200">
      <div className="p-3.5 border-b border-linen-border/70 flex items-center justify-between">
        <span className="font-medium text-xs text-linen-muted uppercase tracking-wider">Saved Threads</span>
        <button
          onClick={onNewChat}
          className="px-2.5 py-1 text-xs bg-[#2b2622] hover:bg-[#423b35] rounded-lg font-medium text-white transition shadow-sm"
        >
          + New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sessions.length === 0 ? (
          <div className="text-xs text-linen-muted p-3 italic">No saved chats yet.</div>
        ) : (
          sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelectSession(s.id)}
              className={`group flex items-center justify-between px-3 py-2 rounded-xl cursor-pointer text-xs transition ${
                s.id === activeSessionId
                  ? 'bg-linen-userBubble border border-linen-border text-linen-text font-medium shadow-xs'
                  : 'hover:bg-linen-surfaceAlt/70 text-linen-muted hover:text-linen-text border border-transparent'
              }`}
            >
              <span className="truncate flex-1">{s.title || 'Untitled Chat'}</span>
              <button
                onClick={(e) => onDeleteSession(s.id, e)}
                className="opacity-0 group-hover:opacity-100 hover:text-red-500 ml-1.5 p-1 text-linen-muted transition"
                title="Delete session"
              >
                <i className="fa-solid fa-trash text-[10px]"></i>
              </button>
            </div>
          ))
        )}
      </div>

      {status && (
        <div className="p-3 border-t border-linen-border/70 text-[11px] bg-linen-surfaceAlt/40 space-y-1 text-linen-muted">
          <div className="flex justify-between">
            <span>Model:</span>
            <span className="text-linen-text font-medium truncate max-w-[120px]">{status.llm_model.split(' ')[0]}</span>
          </div>
          <div className="flex justify-between">
            <span>VRAM:</span>
            <span className="font-mono text-emerald-700">{status.vram}</span>
          </div>
        </div>
      )}
    </aside>
  );
};
