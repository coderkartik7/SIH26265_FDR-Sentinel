import React from 'react';
import { AlertTriangle, ShieldCheck, Key } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface SimulatedBadgeProps {
  className?: string;
  size?: 'sm' | 'md';
}

export const SimulatedBadge: React.FC<SimulatedBadgeProps> = ({ className = '', size = 'sm' }) => {
  const { t } = useTranslation();
  const isSmall = size === 'sm';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-bold uppercase rounded-md border border-amber-500/40 bg-amber-500/10 text-amber-400 shadow-sm ${
        isSmall ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1'
      } ${className}`}
      title="Honesty Rule 2: This verification data originates from a local synthetic bank ledger table, not a real external bank API."
    >
      <AlertTriangle className={isSmall ? 'w-3 h-3 text-amber-400' : 'w-3.5 h-3.5 text-amber-400'} />
      <span>{t('app.simulated_badge')}</span>
    </span>
  );
};

export const RealCryptoBadge: React.FC<SimulatedBadgeProps> = ({ className = '', size = 'sm' }) => {
  const { t } = useTranslation();
  const isSmall = size === 'sm';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold uppercase rounded-md border border-emerald-500/40 bg-emerald-500/10 text-emerald-400 shadow-sm ${
        isSmall ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1'
      } ${className}`}
      title="Verified using Ed25519 public key cryptographic signature."
    >
      <Key className={isSmall ? 'w-3 h-3 text-emerald-400' : 'w-3.5 h-3.5 text-emerald-400'} />
      <span>{t('app.real_crypto_badge')}</span>
    </span>
  );
};

export const RealSignatureBadge: React.FC<SimulatedBadgeProps> = ({ className = '', size = 'sm' }) => {
  const { t } = useTranslation();
  const isSmall = size === 'sm';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold uppercase rounded-md border border-cyan-500/40 bg-cyan-500/10 text-cyan-300 shadow-sm ${
        isSmall ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1'
      } ${className}`}
      title="Cryptographically verified using pyHanko PKI against our CA certificates."
    >
      <ShieldCheck className={isSmall ? 'w-3 h-3 text-cyan-400' : 'w-3.5 h-3.5 text-cyan-400'} />
      <span>{t('app.real_sig_badge')}</span>
    </span>
  );
};
