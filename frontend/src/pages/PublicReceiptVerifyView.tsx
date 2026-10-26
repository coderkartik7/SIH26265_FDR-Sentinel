import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ShieldCheck,
  CheckCircle2,
  Lock,
  Search,
  AlertTriangle,
  QrCode,
  ArrowRight,
  ShieldAlert,
  Building,
  Calendar,
  DollarSign
} from 'lucide-react';
import apiClient from '../services/api';

export const PublicReceiptVerifyView: React.FC = () => {
  const { digest: routeDigest } = useParams<{ digest?: string }>();
  const [digestInput, setDigestInput] = useState<string>(routeDigest || '');
  const [loading, setLoading] = useState(false);
  const [receiptData, setReceiptData] = useState<any | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const verifyDigest = async (targetDigest: string) => {
    if (!targetDigest.trim()) return;
    setLoading(true);
    setErrorMsg(null);
    setReceiptData(null);
    try {
      const res = await apiClient.get(`/trust/receipt/${targetDigest.trim()}`);
      setReceiptData(res.data);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'No valid AICTE sealed receipt found matching this digest.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (routeDigest) {
      verifyDigest(routeDigest);
    }
  }, [routeDigest]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    verifyDigest(digestInput);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-8">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="receipt-verify-icon inline-flex p-3 rounded-2xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 mb-2">
          <QrCode className="w-10 h-10" />
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Public Sealed QR Receipt Verification
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 max-w-xl mx-auto">
          Verify the cryptographic authenticity of any AICTE sealed security deposit. The sealed receipt digest guarantees that the deposit was officially approved and has not been altered.
        </p>
      </div>

      {/* Search Bar */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 shadow-2xl">
        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={digestInput}
              onChange={(e) => setDigestInput(e.target.value)}
              placeholder="Paste 64-character SHA-256 sealed receipt digest or scan QR..."
              className="w-full pl-10 pr-4 py-3 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-xs sm:text-sm focus:outline-none focus:border-cyan-500 font-mono shadow-inner"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !digestInput.trim()}
            className="px-6 py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-cyan-600/30"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <ShieldCheck className="w-4 h-4" />
            )}
            <span>Verify Digest</span>
          </button>
        </form>
      </div>

      {/* Error View */}
      {errorMsg && (
        <div className="glass-panel p-6 rounded-2xl border border-rose-500/40 bg-rose-500/5 text-center space-y-2">
          <ShieldAlert className="w-8 h-8 text-rose-400 mx-auto" />
          <h3 className="text-base font-bold text-rose-300">Verification Failed</h3>
          <p className="text-xs text-slate-400">{errorMsg}</p>
        </div>
      )}

      {/* Valid Receipt View */}
      {receiptData && (
        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-cyan-500/40 bg-cyan-500/5 shadow-2xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-cyan-500/20">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                <Lock className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400 font-bold">
                  {receiptData.badge}
                </span>
                <h2 className="text-xl font-extrabold text-white">Cryptographically Verified</h2>
              </div>
            </div>
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 self-start sm:self-auto">
              AUTHENTIC & SEALED
            </span>
          </div>

          {/* Receipt Info Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
              <span className="text-slate-400 flex items-center gap-1.5 uppercase font-semibold text-[10px]">
                <Building className="w-3.5 h-3.5 text-cyan-400" />
                Case & Institution
              </span>
              <div className="font-mono text-sm font-bold text-white">{receiptData.case_number}</div>
              <div className="text-slate-400">{receiptData.institution_id}</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
              <span className="text-slate-400 flex items-center gap-1.5 uppercase font-semibold text-[10px]">
                <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
                Deposit Amount & Bank
              </span>
              <div className="font-mono-nums text-sm font-bold text-white">
                ₹{(receiptData.principal_amount || 0).toLocaleString('en-IN')}
              </div>
              <div className="text-slate-300">{receiptData.bank_name} &bull; #{receiptData.fdr_number}</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
              <span className="text-slate-400 flex items-center gap-1.5 uppercase font-semibold text-[10px]">
                <Calendar className="w-3.5 h-3.5 text-amber-400" />
                Maturity Date
              </span>
              <div className="font-mono text-sm font-bold text-white">
                {receiptData.maturity_date ? new Date(receiptData.maturity_date).toLocaleDateString() : 'N/A'}
              </div>
              <div className="text-slate-400">Lock Status: IMMUTABLE</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
              <span className="text-slate-400 flex items-center gap-1.5 uppercase font-semibold text-[10px]">
                <ShieldCheck className="w-3.5 h-3.5 text-sentinel-400" />
                Sealed By Official
              </span>
              <div className="font-mono text-sm font-bold text-sentinel-300">
                {receiptData.sealed_by || 'AICTE Authorized Official'}
              </div>
              <div className="text-slate-400 font-mono text-[10px]">
                {receiptData.sealed_at ? new Date(receiptData.sealed_at).toLocaleString() : ''}
              </div>
            </div>
          </div>

          {/* Digest Hash */}
          <div className="p-3.5 rounded-xl bg-slate-950 border border-cyan-500/30 text-xs font-mono space-y-1">
            <span className="text-slate-500 block text-[10px] uppercase font-bold">SHA-256 Digest:</span>
            <div className="text-cyan-300 break-all">{receiptData.digest}</div>
          </div>
        </div>
      )}
    </div>
  );
};
