import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import apiClient from '../services/api';

interface ELAModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
}

export const AuthImage: React.FC<{
  path: string;
  alt: string;
  className?: string;
  onClick?: () => void;
}> = ({ path, alt, className, onClick }) => {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    setFailed(false);
    setSrc(null);

    apiClient
      .get(path, { responseType: 'blob' })
      .then((res) => {
        if (cancelled) return;
        const type = String(res.headers['content-type'] || res.data?.type || '');
        if (type && !type.includes('image') && !type.includes('octet-stream')) {
          setFailed(true);
          return;
        }
        objectUrl = URL.createObjectURL(res.data);
        setSrc(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  if (failed) {
    return <span className="text-muted text-[15px]">Preview unavailable</span>;
  }
  if (!src) {
    return <span className="text-muted text-[15px]">Loading…</span>;
  }
  return (
    <img
      src={src}
      alt={alt}
      className={className}
      onClick={onClick}
      onError={() => setFailed(true)}
    />
  );
};

export const ELAModal: React.FC<ELAModalProps> = ({ isOpen, onClose, caseId }) => {
  const [activeView, setActiveView] = useState<'split' | 'heatmap' | 'original'>('split');

  if (!isOpen) return null;

  const originalPath = `/fdr/cases/${caseId}/preview`;
  const heatmapPath = `/fdr/cases/${caseId}/ela`;
  const imgClass = 'max-h-[70vh] w-full object-contain';
  const tab = (id: typeof activeView, label: string) => (
    <button
      onClick={() => setActiveView(id)}
      className={`px-3 py-1.5 rounded-lg text-[15px] font-semibold ${
        activeView === id ? 'btn-primary' : 'text-muted hover:text-ink'
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/70">
      <div className="w-full max-w-5xl max-h-[80vh] bg-surface border border-soft rounded-lg p-6 flex flex-col relative overflow-hidden">
        <div className="flex items-center justify-between pb-3 border-b border-soft shrink-0">
          <h3 className="text-[15px] font-semibold text-ink">Error level analysis</h3>
          <button onClick={onClose} className="text-muted hover:text-ink p-1 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-2 py-3 shrink-0">
          {tab('split', 'Side-by-side')}
          {tab('heatmap', 'Heatmap')}
          {tab('original', 'Original')}
        </div>

        <div className="flex-1 overflow-auto min-h-0 min-w-0 bg-bg border border-soft rounded-lg p-4">
          {activeView === 'split' ? (
            <div className="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-4 w-full">
              <div className="flex flex-col items-start min-w-0">
                <span className="text-[15px] text-muted mb-2">Original</span>
                <AuthImage path={originalPath} alt="Original FDR document" className={imgClass} />
              </div>
              <div className="flex flex-col items-start min-w-0">
                <span className="text-[15px] text-muted mb-2">Heatmap</span>
                <AuthImage path={heatmapPath} alt="ELA heatmap" className={imgClass} />
              </div>
            </div>
          ) : activeView === 'heatmap' ? (
            <AuthImage path={heatmapPath} alt="ELA heatmap" className={imgClass} />
          ) : (
            <AuthImage path={originalPath} alt="Original FDR document" className={imgClass} />
          )}
        </div>
      </div>
    </div>
  );
};
