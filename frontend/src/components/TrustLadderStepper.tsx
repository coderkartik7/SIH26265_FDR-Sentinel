import React from 'react';
import { TrustLevel } from '../types';

interface TrustLadderStepperProps {
  currentLevel: TrustLevel;
  className?: string;
}

const levels: Array<{ key: TrustLevel; label: string }> = [
  { key: 'L1_DECLARED', label: 'Declared' },
  { key: 'L2_MACHINE_CHECKED', label: 'Machine-checked' },
  { key: 'L3_SOURCE_VERIFIED', label: 'Source-verified' },
  { key: 'L4_SEALED', label: 'Sealed' },
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
    <div className={`w-full py-2 overflow-x-auto ${className}`}>
      <div className="flex items-center gap-2 min-w-0">
        {levels.map((lvl, index) => {
          const isPassed = index < activeIdx;
          const isCurrent = index === activeIdx;
          return (
            <React.Fragment key={lvl.key}>
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className={`h-2 w-2 rounded-full ${
                    isCurrent ? 'bg-accent' : isPassed ? 'bg-ok' : 'bg-soft'
                  }`}
                />
                <span
                  className={`text-[15px] whitespace-nowrap ${
                    isCurrent ? 'font-semibold text-accent-text' : isPassed ? 'text-ok' : 'text-muted'
                  }`}
                >
                  {lvl.label}
                </span>
              </div>
              {index < levels.length - 1 && <span className="h-px w-8 bg-soft shrink-0" />}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
