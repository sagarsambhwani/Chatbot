import React from 'react';
import { Session, SystemStatus } from '../types/chat';

interface SidebarProps {
    sessions: Session[];
    activeSessionId: string | null;
    status: SystemStatus | null;
    onSelectSession: (id: string) => void;
    onNewChat: () => void;
    onDeleteSession: (id: string, e: React.MouseEvent) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
    sessions,
    activeSessionId,
    status,
    onSelectSession,
    onNewChat,
    onDeleteSession,
}) => {
    return (
        <aside className="w-64 bg-zinc-900 border-r border-zinc-800 flex flex-col h-full text-zinc-200">
            <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
                <h2 className="font-semibold text-lg text-white">Local Assistant</h2>
                <button
                    onClick={onNewChat}
                    className="px-2.5 py-1 text-xs bg-indigo-600 hover:bg-indigo-500 rounded font-medium text-white transition"
                >
                    + New Chat
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {sessions.map((s) => (
                    <div
                        key={s.id}
                        onClick={() => onSelectSession(s.id)}
                        className={`group flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-sm transition ${s.id === activeSessionId
                            ? 'bg-zinc-800 text-white font-medium'
                            : 'hover:bg-zinc-800/50 text-zinc-400 hover:text-zinc-200'
                            }`}
                    >
                        <span className="truncate flex-1">{s.title || 'Untitled Chat'}</span>
                        <button
                            onClick={(e) => onDeleteSession(s.id, e)}
                            className="opacity-0 group-hover:opacity-100 hover:text-red-400 ml-2 text-xs p-1"
                            title="Delete session"
                        >
                            ✕
                        </button>
                    </div>
                ))}
            </div>

            {status && (
                <div className="p-3 border-t border-zinc-800 text-xs bg-zinc-950/40 space-y-1 text-zinc-400">
                    <div className="flex justify-between">
                        <span>GPU VRAM:</span>
                        <span className="font-mono text-emerald-400">{status.vram}</span>
                    </div>
                    <div className="flex justify-between">
                        <span>LLM:</span>
                        <span className="text-zinc-300 truncate max-w-[120px]">{status.llm_model.split(' ')[0]}</span>
                    </div>
                    <div className="flex justify-between">
                        <span>Indexed Docs:</span>
                        <span className="text-zinc-300">{status.rag_docs_count}</span>
                    </div>
                </div>
            )}
        </aside>
    );
};