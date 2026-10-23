import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Activity,
  RefreshCw,
  Database,
  Lock,
  AlertTriangle,
  Play,
  Key,
  CheckCircle2,
  FileCode
} from 'lucide-react';
import apiClient from '../services/api';
import { AuditLog, AuditVerifyResult } from '../types';

export const AuditVerifyView: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [verifyResult, setVerifyResult] = useState<AuditVerifyResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [tampering, setTampering] = useState(false);
  const [tamperMsg, setTamperMsg] = useState<string | null>(null);

  const fetchAuditData = async () => {
    setLoading(true);
    setTamperMsg(null);
    try {
      const [logsRes, verifyRes] = await Promise.all([
        apiClient.get<AuditLog[]>('/audit/logs?limit=50'),
        apiClient.get<AuditVerifyResult>('/audit/verify'),
      ]);
      setLogs(logsRes.data);
      setVerifyResult(verifyRes.data);
    } catch (err: any) {
      console.error('Failed to load audit verification', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditData();
  }, []);

  const handleSimulateTamper = async () => {
    if (logs.length === 0) return;
    setTampering(true);
    setTamperMsg(null);
    const targetRecord = logs[Math.floor(logs.length / 2)] || logs[0];

    try {
      await apiClient.post('/audit/tamper-demo', {
        record_id: targetRecord.id,
        forged_action: 'UNAUTHORIZED_ADMIN_TAMPER_SIMULATION',
        forged_details: {
          tampered_by: 'Demo Intruder / Corrupted DB Admin',
          tamper_reason: 'Testing cryptographic hash-chain break detection',
        },
      });

      // Immediately re-verify hash chain
      const verifyRes = await apiClient.get<AuditVerifyResult>('/audit/verify');
      setVerifyResult(verifyRes.data);
      setTamperMsg(`Injected unauthorized DB edit on Audit Row #${targetRecord.id}. Hash chain broken index immediately detected at #${verifyRes.data.broken_index}!`);
      // Refresh logs
      const logsRes = await apiClient.get<AuditLog[]>('/audit/logs?limit=50');
      setLogs(logsRes.data);
    } catch (err: any) {
      setTamperMsg(err.response?.data?.detail || 'Failed to simulate DB tamper');
    } finally {
      setTampering(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              Cryptographic Audit Chain Verification
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-sentinel-500/20 text-sentinel-400 border border-sentinel-500/30 font-mono">
              SHA-256 Chained
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Every portal mutation is sealed in a recursive cryptographic hash chain: <code className="text-sentinel-300 font-mono">H_i = SHA256(H_i-1 + canonical_json(E_i))</code>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchAuditData}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
            title="Re-verify Chain"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-sentinel-400' : ''}`} />
          </button>
          <button
            onClick={handleSimulateTamper}
            disabled={tampering || logs.length === 0}
            className="px-4 py-2.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-xs font-bold flex items-center gap-2 transition-all shadow-md"
            title="Mutate an audit row in the database without updating hash"
          >
            <AlertTriangle className="w-4 h-4 text-rose-400" />
            <span>Simulate DB Row Tamper</span>
          </button>
        </div>
      </div>

      {tamperMsg && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <span>{tamperMsg}</span>
        </div>
      )}

      {/* Verification Status Card */}
      {verifyResult && (
        <div
          className={`glass-panel p-6 rounded-2xl border shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4 ${
            verifyResult.is_valid
              ? 'border-emerald-500/40 bg-emerald-500/5'
              : 'border-rose-500/50 bg-rose-500/10'
          }`}
        >
          <div className="flex items-center gap-4">
            <div
              className={`p-3.5 rounded-2xl ${
                verifyResult.is_valid
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse'
              }`}
            >
              {verifyResult.is_valid ? (
                <ShieldCheck className="w-8 h-8" />
              ) : (
                <ShieldAlert className="w-8 h-8" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white">
                  {verifyResult.is_valid
                    ? 'Cryptographic Audit Log: 100% UNCOMPROMISED'
                    : 'AUDIT CHAIN INTEGRITY BREACH DETECTED'}
                </h2>
                <span
                  className={`px-2.5 py-0.5 rounded text-xs font-mono font-bold ${
                    verifyResult.is_valid
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : 'bg-rose-500/20 text-rose-300'
                  }`}
                >
                  {verifyResult.is_valid ? 'VALID CHAIN' : 'TAMPER PINPOINTED'}
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1">{verifyResult.message}</p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-right">
            <div>
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">
                Chain Height
              </span>
              <span className="text-xl font-bold font-mono text-slate-100">
                {verifyResult.chain_length} Blocks
              </span>
            </div>
            {verifyResult.broken_index !== null && (
              <div className="border-l border-rose-500/30 pl-4">
                <span className="text-[10px] text-rose-400 uppercase tracking-wider block font-semibold">
                  Broken At Block #
                </span>
                <span className="text-xl font-bold font-mono text-rose-400">
                  {verifyResult.broken_index}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Audit Log Blocks */}
      <div className="glass-panel rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
        <div className="p-4 sm:p-6 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-sentinel-400" />
            <h3 className="font-bold text-slate-100 text-sm">Audit Chain Explorer (Latest 50 Entries)</h3>
          </div>
          <span className="text-xs font-mono text-slate-400">Canonical JSON Serialized</span>
        </div>

        <div className="divide-y divide-slate-800/80">
          {logs.map((log) => {
            const isBrokenRow = verifyResult && !verifyResult.is_valid && verifyResult.broken_index === log.id;

            return (
              <div
                key={log.id}
                className={`p-4 transition-colors ${
                  isBrokenRow
                    ? 'bg-rose-500/15 border-l-4 border-rose-500'
                    : 'hover:bg-slate-800/40'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-xs font-bold text-sentinel-400 bg-sentinel-500/10 px-2 py-0.5 rounded border border-sentinel-500/20">
                      Block #{log.id}
                    </span>
                    <span className="font-semibold text-xs text-white uppercase tracking-wider">
                      {log.action}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      [{log.target_type}:{log.target_id?.slice(0, 8)}]
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500">
                    {new Date(log.timestamp).toLocaleString()}
                  </span>
                </div>

                {/* Hashes */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-mono bg-slate-900/70 p-2.5 rounded-lg border border-slate-800/80 mb-2">
                  <div className="truncate">
                    <span className="text-slate-500 mr-1.5">Prev Hash:</span>
                    <span className="text-slate-400">{log.prev_hash}</span>
                  </div>
                  <div className="truncate">
                    <span className="text-slate-500 mr-1.5">Record Hash:</span>
                    <span className={isBrokenRow ? 'text-rose-400 font-bold' : 'text-emerald-400'}>
                      {log.record_hash}
                    </span>
                  </div>
                </div>

                {/* Canonical Event Details */}
                <div className="text-xs text-slate-400 bg-slate-950/60 p-2 rounded border border-slate-900 font-mono overflow-x-auto">
                  {JSON.stringify(log.details_json)}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
