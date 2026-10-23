import React, { useState } from 'react';
import { X, Layers, AlertCircle, Eye, EyeOff, ZoomIn } from 'lucide-react';

interface ELAModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
}

export const ELAModal: React.FC<ELAModalProps> = ({ isOpen, onClose, caseId }) => {
  const [activeView, setActiveView] = useState<'split' | 'heatmap' | 'original'>('split');
  const token = localStorage.getItem('sentinel_access_token') || '';

  if (!isOpen) return null;

  const originalUrl = `/api/v1/fdr/cases/${caseId}/preview`;
  const heatmapUrl = `/api/v1/fdr/cases/${caseId}/ela-heatmap`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
      <div className="w-full max-w-5xl max-h-[92vh] glass-panel rounded-2xl border border-rose-500/30 p-6 shadow-2xl flex flex-col relative">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/30">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-slate-100">
                  Forensic Tamper Inspection &bull; Error Level Analysis (ELA)
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/30">
                  95% Compression Differential
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Pillow ELA highlights compression anomalies: bright hyper-intense pixels indicate pasted or edited regions
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* View Toggle Bar */}
        <div className="flex items-center justify-between py-3">
          <div className="flex items-center gap-2 bg-slate-800/80 p-1 rounded-xl border border-slate-700">
            <button
              onClick={() => setActiveView('split')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeView === 'split' ? 'bg-sentinel-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Side-by-Side Comparison
            </button>
            <button
              onClick={() => setActiveView('heatmap')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeView === 'heatmap' ? 'bg-sentinel-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              ELA Heatmap Only
            </button>
            <button
              onClick={() => setActiveView('original')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeView === 'original' ? 'bg-sentinel-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Original Document Only
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-500/10 px-3 py-1 rounded-lg border border-amber-500/20">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Bright white/colored clusters flag high probability of paste manipulation</span>
          </div>
        </div>

        {/* Image Display */}
        <div className="flex-1 overflow-auto bg-slate-950/80 rounded-xl border border-slate-800 p-4 min-h-[420px] flex items-center justify-center">
          {activeView === 'split' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full h-full">
              <div className="flex flex-col items-center">
                <span className="text-xs font-mono font-semibold text-slate-400 mb-2">Original Document Scan</span>
                <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-900 shadow-lg max-h-[500px]">
                  <img
                    src={originalUrl}
                    alt="Original FDR Document"
                    className="max-h-[480px] w-auto object-contain"
                  />
                </div>
              </div>
              <div className="flex flex-col items-center">
                <span className="text-xs font-mono font-semibold text-rose-400 mb-2">
                  Computed ELA Heatmap (Brightness Amplified &times;15)
                </span>
                <div className="border border-rose-500/30 rounded-lg overflow-hidden bg-black shadow-lg max-h-[500px]">
                  <img
                    src={heatmapUrl}
                    alt="ELA Heatmap"
                    className="max-h-[480px] w-auto object-contain"
                  />
                </div>
              </div>
            </div>
          ) : activeView === 'heatmap' ? (
            <div className="flex flex-col items-center">
              <span className="text-xs font-mono font-semibold text-rose-400 mb-2">
                Computed ELA Heatmap (Brightness Amplified &times;15)
              </span>
              <img
                src={heatmapUrl}
                alt="ELA Heatmap"
                className="max-h-[540px] w-auto object-contain rounded-lg border border-rose-500/30"
              />
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <span className="text-xs font-mono font-semibold text-slate-400 mb-2">Original Document Scan</span>
              <img
                src={originalUrl}
                alt="Original FDR Document"
                className="max-h-[540px] w-auto object-contain rounded-lg border border-slate-800"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
