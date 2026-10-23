import React from 'react';
import { CheckCircle2, Lock, Cpu, Globe, FileCheck } from 'lucide-react';
import { TrustLevel } from '../types';

interface TrustLadderStepperProps {
  currentLevel: TrustLevel;
  className?: string;
}

const levels: Array<{ key: TrustLevel; label: string; desc: string; icon: React.ComponentType<{ className?: string }> }> = [
  { key: 'L1_DECLARED', label: 'L1: Declared', desc: 'Ingested & Encrypted', icon: FileCheck },
  { key: 'L2_MACHINE_CHECKED', label: 'L2: Machine-Checked', desc: 'Forensics & Math Verified', icon: Cpu },
  { key: 'L3_SOURCE_VERIFIED', label: 'L3: Source-Verified', desc: 'Connector Confirmed', icon: Globe },
  { key: 'L4_SEALED', label: 'L4: Sealed', desc: 'Official Approval & Receipt', icon: Lock },
];

const levelIndexMap: Record<TrustLevel, number> = {
  L1_DECLARED: 0,
  L2_MACHINE_CHECKED: 1,
  L3_SOURCE_VERIFIED: 2,
  L4_SEALED: 3,
};

export const TrustLadderStepper: React.FC<TrustLadderStepperProps> = ({ currentLevel, className = '' }) => {
  const activeIdx = levelIndexMap[currentLevel] ?? 0;

  return (
    <div className={`w-full py-3 ${className}`}>
      <div className="flex items-center justify-between relative">
        {/* Track Line */}
        <div className="absolute top-1/2 left-6 right-6 -translate-y-1/2 h-1 bg-slate-800 rounded z-0">
          <div
            className="h-full bg-gradient-to-r from-sentinel-500 via-cyan-400 to-emerald-400 rounded transition-all duration-500"
            style={{ width: `${(activeIdx / (levels.length - 1)) * 100}%` }}
          />
        </div>

        {levels.map((lvl, index) => {
          const isPassed = index < activeIdx;
          const isCurrent = index === activeIdx;
          const isUpcoming = index > activeIdx;
          const IconComponent = lvl.icon;

          return (
            <div key={lvl.key} className="flex flex-col items-center relative z-10">
              <div
                className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold transition-all duration-300 shadow-lg ${
                  isCurrent
                    ? 'bg-sentinel-500 text-white ring-4 ring-sentinel-500/30 scale-110 shadow-sentinel-500/50'
                    : isPassed
                    ? 'bg-emerald-600 text-white ring-2 ring-emerald-500/40'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}
              >
                {isPassed ? <CheckCircle2 className="w-5 h-5 text-white" /> : <IconComponent className="w-5 h-5" />}
              </div>
              <span
                className={`mt-2 text-xs font-semibold text-center whitespace-nowrap ${
                  isCurrent ? 'text-sentinel-400' : isPassed ? 'text-emerald-300' : 'text-slate-500'
                }`}
              >
                {lvl.label}
              </span>
              <span className="text-[10px] text-slate-400 hidden sm:block text-center">{lvl.desc}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
