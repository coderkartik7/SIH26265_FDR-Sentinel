import React from 'react';
import { ShieldAlert, AlertTriangle, ShieldCheck, Sparkles } from 'lucide-react';
import { RiskScore } from '../types';

interface RiskMeterProps {
  riskScore: RiskScore | null;
  className?: string;
}

export const RiskMeter: React.FC<RiskMeterProps> = ({ riskScore, className = '' }) => {
  if (!riskScore) {
    return (
      <div className={`p-4 glass-card rounded-lg text-left text-muted text-[15px] ${className}`}>
        Risk score pending
      </div>
    );
  }

  const rawScore = typeof riskScore.overall_score === 'number'
    ? riskScore.overall_score
    : (typeof (riskScore as any).score === 'number' ? (riskScore as any).score : 0);
  const score = Math.round(rawScore);

  const rawBand = riskScore.risk_band || (riskScore as any).risk_level || 'LOW';
  const band = String(rawBand).toUpperCase();

  // Band color styles
  const getBandStyles = (b: string) => {
    switch (b) {
      case 'CRITICAL':
        return {
          bg: 'bg-rose-500/10 border-rose-500/40 text-rose-400',
          bar: 'bg-rose-500',
          icon: ShieldAlert,
        };
      case 'HIGH':
        return {
          bg: 'bg-orange-500/10 border-orange-500/40 text-orange-400',
          bar: 'bg-orange-500',
          icon: AlertTriangle,
        };
      case 'MEDIUM':
        return {
          bg: 'bg-amber-500/10 border-amber-500/40 text-amber-400',
          bar: 'bg-amber-500',
          icon: AlertTriangle,
        };
      case 'LOW':
      default:
        return {
          bg: 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400',
          bar: 'bg-emerald-500',
          icon: ShieldCheck,
        };
    }
  };

  const style = getBandStyles(band);
  const IconComponent = style.icon;

  const reasons = (riskScore as any).top_reasons_json || riskScore.shap_reasons || [];

  return (
    <div className={`p-5 glass-panel rounded-2xl border border-slate-700/60 shadow-xl ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-sentinel-400" />
          <h3 className="font-semibold text-slate-100 text-[15px]">
            Risk assessment
          </h3>
        </div>
        <span className={`px-2.5 py-1 rounded-full text-xs font-bold border flex items-center gap-1.5 ${style.bg}`}>
          <IconComponent className="w-3.5 h-3.5" />
          {band} RISK
        </span>
      </div>

      {/* Progress Bar & Value */}
      <div className="my-4">
        <div className="flex justify-between items-baseline mb-1">
          <span className="text-3xl font-extrabold font-mono-nums text-slate-100">
            {score}<span className="text-sm font-normal text-slate-400">/100</span>
          </span>
          <span className="text-xs text-slate-400">0: Minimal Risk &bull; 100: Max Anomaly Risk</span>
        </div>
        <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-700/80">
          <div
            className={`h-full rounded-full transition-all duration-700 ${style.bar}`}
            style={{ width: `${Math.min(100, Math.max(2, score))}%` }}
          />
        </div>
      </div>

      {/* SHAP Explainability Chips */}
      {reasons.length > 0 && (
        <div className="mt-4 pt-3 border-t border-slate-800">
          <h4 className="text-[15px] font-semibold text-slate-400 mb-2">
            Key risk factors
          </h4>
          <div className="space-y-2">
            {reasons.map((reason: any, idx: number) => {
              const feat = reason.feature || 'Feature';
              const text = reason.description || reason.reason || 'Risk factor analyzed';
              const impactLabel = reason.contribution || (typeof reason.impact === 'number' ? `${reason.impact > 0 ? '+' : ''}${reason.impact.toFixed(1)} pts` : '+5.0 pts');
              const isHigh = String(impactLabel).startsWith('+');

              return (
                <div
                  key={idx}
                  className="flex items-start gap-2 text-xs p-2 rounded-lg bg-slate-800/60 border border-slate-700/50"
                >
                  <div
                    className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${
                      isHigh ? 'bg-amber-400' : 'bg-emerald-400'
                    }`}
                  />
                  <div className="flex-1">
                    <span className="font-mono text-slate-300 font-medium mr-1.5">[{feat}]:</span>
                    <span className="text-slate-400">{text}</span>
                  </div>
                  <span
                    className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                      isHigh ? 'text-amber-300 bg-amber-500/10' : 'text-emerald-300 bg-emerald-500/10'
                    }`}
                  >
                    {impactLabel}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
