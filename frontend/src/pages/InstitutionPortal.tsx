import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  UploadCloud,
  FileCheck,
  ShieldCheck,
  AlertCircle,
  Clock,
  ArrowRight,
  Layers,
  CheckCircle2,
  Lock,
  RefreshCw,
  Send
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import apiClient from '../services/api';
import { useAuth } from '../context/AuthContext';
import { FDRCaseListItem, ReleaseRequest } from '../types';

export const InstitutionPortal: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();

  const [cases, setCases] = useState<FDRCaseListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Release Request Modal State
  const [releaseModalOpen, setReleaseModalOpen] = useState(false);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('');
  const [releaseLoading, setReleaseLoading] = useState(false);
  const [releaseMsg, setReleaseMsg] = useState<string | null>(null);

  const fetchMyCases = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get<FDRCaseListItem[]>('/fdr/cases');
      setCases(res.data);
    } catch (err: any) {
      console.error('Failed to load institution deposits', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMyCases();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('change_reason', 'INITIAL_SUBMISSION');

    try {
      const res = await apiClient.post('/fdr/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUploadSuccess(`FDR Certificate ${res.data.case_number} uploaded, AES-256-GCM encrypted, and verified through AICTE forensic pipeline!`);
      fetchMyCases();
    } catch (err: any) {
      setUploadError(err.response?.data?.detail || 'Failed to upload and process FDR document.');
    } finally {
      setUploading(false);
    }
  };

  const handleRequestRelease = async (caseId: string) => {
    setReleaseLoading(true);
    setReleaseMsg(null);
    try {
      const res = await apiClient.post<ReleaseRequest>('/monitoring/release/request', {
        case_id: caseId,
      });
      setReleaseMsg(`Release request #${res.data.id.slice(0, 8)} submitted for AICTE official review.`);
      fetchMyCases();
    } catch (err: any) {
      setReleaseMsg(err.response?.data?.detail || 'Failed to submit release request.');
    } finally {
      setReleaseLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Welcome Header */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">Institution Deposit Portal</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
              {user?.institution_id || 'AICTE Affiliated'}
            </span>
          </div>
        </div>

        <button
          onClick={fetchMyCases}
          className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all self-start md:self-auto"
          title="Refresh Deposits"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-sentinel-400' : ''}`} />
        </button>
      </div>

      {/* Upload FDR Section */}
      <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-slate-800 shadow-xl space-y-4">
        <div className="flex items-center gap-3">
          <div className="text-sentinel-400">
            <UploadCloud className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">{t('institution.upload_title')}</h2>
          </div>
        </div>

        {uploadSuccess && (
          <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{uploadSuccess}</span>
          </div>
        )}

        {uploadError && (
          <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}

        {/* Drag and Drop Zone */}
        <label className="relative border-2 border-dashed border-slate-700 hover:border-sentinel-500/80 rounded-2xl p-8 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-900/40 hover:bg-slate-900/80 group">
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={handleFileUpload}
            disabled={uploading}
            className="hidden"
          />
          <div className="text-slate-400 group-hover:text-sentinel-300 transition-colors mb-3">
            <UploadCloud className="w-8 h-8" />
          </div>
          <span className="text-sm font-semibold text-slate-200">
            {uploading ? t('institution.uploading') : t('institution.select_file')}
          </span>
          <span className="text-xs text-slate-500 mt-1">
            Max 25 MB &bull; Magic byte verified &bull; Client AES-256-GCM encrypted
          </span>
        </label>
      </div>

      {/* My FDR Deposits List */}
      <div className="glass-panel rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
        <div className="p-4 sm:p-6 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-sentinel-400" />
            <h3 className="font-bold text-slate-100 text-sm">{t('institution.my_deposits')} ({cases.length})</h3>
          </div>
        </div>

        {cases.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            {loading ? 'Loading deposits...' : 'No security deposits uploaded yet. Submit your first FDR above.'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-slate-400 uppercase font-mono tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Case #</th>
                  <th className="py-3 px-4">Bank</th>
                  <th className="py-3 px-4">FDR Number</th>
                  <th className="py-3 px-4">Principal Amount</th>
                  <th className="py-3 px-4">Maturity Date</th>
                  <th className="py-3 px-4">Trust Level</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {cases.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-sentinel-400">
                      {c.case_number}
                    </td>
                    <td className="py-3 px-4 text-slate-200 font-medium">{c.bank_name}</td>
                    <td className="py-3 px-4 font-mono text-slate-300">{c.fdr_number}</td>
                    <td className="py-3 px-4 font-mono-nums font-bold text-slate-100">
                      ₹{(c.principal_amount).toLocaleString('en-IN')}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400">
                      {new Date(c.maturity_date).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-semibold text-slate-300">
                        T{c.trust_level[1]}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          c.status === 'VERIFIED'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : c.status === 'RELEASED'
                            ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                            : c.status === 'RELEASE_REQUESTED'
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            : c.status === 'FLAGGED'
                            ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            : 'bg-slate-700/50 text-slate-300'
                        }`}
                      >
                        {c.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right flex items-center justify-end gap-2">
                      {c.status === 'VERIFIED' && (
                        <button
                          onClick={() => {
                            setSelectedCaseId(c.id);
                            setReleaseModalOpen(true);
                          }}
                          className="px-2.5 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-[11px] font-semibold transition-all"
                        >
                          {t('institution.request_release')}
                        </button>
                      )}
                      <Link
                        to={`/cases/${c.id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-medium text-[11px] border border-slate-700"
                      >
                        <span>View</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Release Request Confirmation Modal */}
      {releaseModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-md glass-panel rounded-2xl border border-amber-500/30 p-6 shadow-2xl relative space-y-4">
            <h3 className="text-base font-bold text-white">Request Security Deposit Release</h3>
            <p className="text-xs text-slate-400">
              Submit formal request for AICTE approval and closure report generation. Prerequisites (maturity period, no lien, KYC) will be evaluated automatically.
            </p>

            {releaseMsg && (
              <div className="p-3 rounded-xl bg-sentinel-500/10 border border-sentinel-500/30 text-sentinel-300 text-xs">
                {releaseMsg}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => {
                  setReleaseModalOpen(false);
                  setReleaseMsg(null);
                }}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700"
              >
                Close
              </button>
              <button
                onClick={() => handleRequestRelease(selectedCaseId)}
                disabled={releaseLoading}
                className="px-4 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold flex items-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Confirm Request</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
