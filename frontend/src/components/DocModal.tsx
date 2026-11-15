import React, { useState, useEffect } from 'react';
import { uploadDocument } from '../services/api';

interface DocModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDocsChanged?: () => void;
}

export const DocModal: React.FC<DocModalProps> = ({ isOpen, onClose, onDocsChanged }) => {
  const [docs, setDocs] = useState<string[]>([]);
  const [chunks, setChunks] = useState<number>(0);
  const [uploading, setUploading] = useState<boolean>(false);
  const [reindexing, setReindexing] = useState<boolean>(false);

  useEffect(() => {
    if (isOpen) {
      loadDocs();
    }
  }, [isOpen]);

  const loadDocs = async () => {
    try {
      const res = await fetch('/api/documents');
      const data = await res.json();
      setDocs(data.documents || []);
      setChunks(data.indexed_chunks || 0);
    } catch (e) {
      console.error(e);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setUploading(true);
    try {
      await uploadDocument(file);
      await loadDocs();
      onDocsChanged?.();
    } catch (err) {
      alert('Upload failed: ' + err);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleReindex = async () => {
    setReindexing(true);
    try {
      const res = await fetch('/api/documents/reindex', { method: 'POST' });
      await res.json();
      await loadDocs();
      onDocsChanged?.();
    } catch (err) {
      alert('Re-index error: ' + err);
    } finally {
      setReindexing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-linen-surface border border-linen-border rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-xl text-linen-text">
        <div className="flex items-center justify-between border-b border-linen-border pb-3">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <i className="fa-regular fa-folder-open text-amber-600"></i> Local Knowledge Base
          </h3>
          <button onClick={onClose} className="text-linen-muted hover:text-linen-text p-1">
            <i className="fa-solid fa-xmark text-sm"></i>
          </button>
        </div>

        <p className="text-xs text-linen-muted">
          Upload reference files (.txt, .md, .pdf). They are chunked and embedded directly into your GPU VRAM with{' '}
          <code className="text-linen-codeText bg-linen-codeBg px-1 py-0.5 rounded">nomic-embed-text</code>.
        </p>

        <label className="border-2 border-dashed border-linen-border hover:border-linen-text rounded-xl p-6 text-center transition cursor-pointer bg-linen-surfaceAlt/60 group block">
          <input
            type="file"
            className="hidden"
            accept=".txt,.md,.pdf"
            onChange={handleFileUpload}
            disabled={uploading}
          />
          <i className="fa-solid fa-cloud-arrow-up text-linen-muted group-hover:text-linen-text text-xl mb-1.5 transition block"></i>
          <p className="text-xs font-medium">
            {uploading ? 'Embedding on GPU...' : 'Click to upload document (.pdf, .txt, .md)'}
          </p>
          <p className="text-[11px] text-linen-muted mt-0.5">Automatic semantic chunking & GPU vector embedding</p>
        </label>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-linen-muted font-medium">
            <span>Indexed Files:</span>
            <span className="text-[11px] font-mono text-emerald-700">{chunks} chunks in VRAM</span>
          </div>
          <div className="max-h-36 overflow-y-auto space-y-1 pr-1 text-xs">
            {docs.length === 0 ? (
              <div className="text-linen-muted italic">No documents uploaded yet.</div>
            ) : (
              docs.map((d, i) => (
                <div key={i} className="flex items-center justify-between bg-linen-surfaceAlt/70 px-2.5 py-1.5 rounded-lg">
                  <span className="truncate flex items-center gap-2">
                    <i className="fa-regular fa-file-lines text-linen-codeText text-[11px]"></i>
                    {d}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="pt-3 flex justify-between items-center border-t border-linen-border text-xs">
          <button
            onClick={handleReindex}
            disabled={reindexing}
            className="px-3 py-1.5 rounded-lg bg-linen-surfaceAlt hover:bg-[#eae1d5] text-linen-text border border-linen-border transition flex items-center gap-1.5 disabled:opacity-50"
          >
            <i className={`fa-solid fa-arrows-rotate text-xs ${reindexing ? 'fa-spin' : ''}`}></i>
            {reindexing ? 'Re-indexing...' : 'Re-index All'}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-[#2b2622] hover:bg-[#423b35] text-white font-medium transition"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
