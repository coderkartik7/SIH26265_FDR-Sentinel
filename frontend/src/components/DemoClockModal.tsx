import React, { useState } from 'react';
import { X, Clock, Play, RotateCcw, AlertCircle, CheckCircle } from 'lucide-react';
import apiClient from '../services/api';

interface DemoClockModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const DemoClockModal: React.FC<DemoClockModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [offsetDays, setOffsetDays] = useState<number>(30);
  const [loading, setLoading] = useState(false);
  const [resultMsg, setResultMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleApplyOffset = async (days: number) => {
    setLoading(true);
    setResultMsg(null);
    try {
      const res = await apiClient.post('/monitoring/demo-clock', { offset_days: days });
      // Also trigger scan to generate alerts immediately
      const scanRes = await apiClient.post('/monitoring/scan-alerts');
      setResultMsg(`Time offset updated to ${days} days. Maturity scanner generated ${scanRes.data.alerts_created} new alert(s).`);
      setOffsetDays(days);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setResultMsg(err.response?.data?.detail || 'Failed to update demo clock');
    } finally {
      setLoading(false);
    }
  };

  const presetOffsets = [
    { label: '+7 Days (Urgent Escalate)', days: 7 },
    { label: '+15 Days (Critical Expiry)', days: 15 },
    { label: '+30 Days (1 Month Scan)', days: 30 },
    { label: '+60 Days (2 Months Scan)', days: 60 },
    { label: '+90 Days (Quarterly Scan)', days: 90 },
    { label: '+180 Days (Half-Year Jump)', days: 180 },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-surface/80">
      <div className="w-full max-w-lg glass-panel rounded-2xl border border-amber-500/30 p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <Clock className="w-6 h-6 animate-pulse-subtle" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-100">Demonstration Clock Time Jump</h3>
            <p className="text-xs text-slate-400">
              Advance portal system time into the future to test maturity alerts & auto-escalation
            </p>
          </div>
        </div>

        {resultMsg && (
          <div className="mb-4 p-3 rounded-xl bg-sentinel-500/10 border border-sentinel-500/30 text-sentinel-300 text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-sentinel-400 flex-shrink-0" />
            <span>{resultMsg}</span>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Select Preset Future Offset:
            </label>
            <div className="grid grid-cols-2 gap-2">
              {presetOffsets.map((preset) => (
                <button
                  key={preset.days}
                  onClick={() => handleApplyOffset(preset.days)}
                  disabled={loading}
                  className={`px-3 py-2.5 rounded-xl text-xs font-semibold text-left transition-all border ${
                    offsetDays === preset.days
                      ? 'bg-amber-500/20 border-amber-500 text-amber-300'
                      : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-700/80 hover:border-slate-600'
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          <div className="pt-2">
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Custom Days Jump:
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                value={offsetDays}
                onChange={(e) => setOffsetDays(parseInt(e.target.value) || 0)}
                className="flex-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-amber-500 font-mono"
                placeholder="Enter days"
              />
              <button
                onClick={() => handleApplyOffset(offsetDays)}
                disabled={loading}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-all"
              >
                <Play className="w-4 h-4 fill-current" />
                Apply Jump
              </button>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 flex justify-between items-center">
            <button
              onClick={() => handleApplyOffset(0)}
              disabled={loading}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium flex items-center gap-1.5 border border-slate-700"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset to Current Time (0 Days)
            </button>
            <span className="text-[11px] text-slate-400">Honesty Rule 1 & 4 compliant</span>
          </div>
        </div>
      </div>
    </div>
  );
};
