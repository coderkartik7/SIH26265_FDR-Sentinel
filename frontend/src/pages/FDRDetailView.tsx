import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Shield,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Layers,
  Sparkles,
  Download,
  Eye,
  Edit3,
  Check,
  X,
  ArrowLeft,
  Key,
  Database,
  Clock,
  ShieldCheck,
  Fingerprint
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import apiClient from '../services/api';
import { useAuth } from '../context/AuthContext';
import { FDRCase, ExtractedField, ForensicFinding, DuplicateMatch, VerificationResult, RiskScore } from '../types';
import { TrustLadderStepper } from '../components/TrustLadderStepper';
import { RiskMeter } from '../components/RiskMeter';
import { SimulatedBadge, RealCryptoBadge, RealSignatureBadge } from '../components/SimulatedBadge';
import { ELAModal, AuthImage } from '../components/ELAModal';

export const FDRDetailView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { role, user } = useAuth();
  const { t } = useTranslation();

  const [fdrCase, setFdrCase] = useState<FDRCase | null>(null);
  const [duplicateMatches, setDuplicateMatches] = useState<DuplicateMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ELA Heatmap Modal
  const [showELAModal, setShowELAModal] = useState(false);

  // Field Edit State
  const [editingFieldId, setEditingFieldId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState<string>('');
  const [savingField, setSavingField] = useState(false);

  // Action States
  const [verifyingConnectors, setVerifyingConnectors] = useState(false);
  const [sealingCase, setSealingCase] = useState(false);
  const [decisionNotes, setDecisionNotes] = useState('');
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  const normalizedRole = role ? String(role).toUpperCase() : null;
  const isOfficial = normalizedRole === 'OFFICIAL' || normalizedRole === 'ADMIN';

  const fetchCaseDetail = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [caseRes, dupRes] = await Promise.all([
        apiClient.get<FDRCase>(`/fdr/cases/${id}`),
        apiClient.get<DuplicateMatch[]>(`/fdr/cases/${id}/duplicates`),
      ]);
      setFdrCase(caseRes.data);
      setDuplicateMatches(dupRes.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load FDR case details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCaseDetail();
  }, [id]);

  const handleSaveField = async (fieldId: string) => {
    setSavingField(true);
    try {
      await apiClient.put(`/fdr/extracted-fields/${fieldId}`, {
        manual_corrected_value: editingValue,
      });
      setEditingFieldId(null);
      fetchCaseDetail();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update field');
    } finally {
      setSavingField(false);
    }
  };

  const handleRunConnectors = async () => {
    if (!id) return;
    setVerifyingConnectors(true);
    setActionSuccessMsg(null);
    try {
      await apiClient.post(`/trust/cases/${id}/verify-connectors`);
      setActionSuccessMsg('Verification connectors evaluated. Case progressed according to source confirmation.');
      fetchCaseDetail();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Verification connectors failed.');
    } finally {
      setVerifyingConnectors(false);
    }
  };

  const handleSealDecision = async (decision: 'SEAL_APPROVE' | 'REJECT') => {
    if (!id) return;
    setSealingCase(true);
    setActionSuccessMsg(null);
    try {
      const res = await apiClient.post(`/trust/cases/${id}/seal`, {
        decision,
        notes: decisionNotes || (decision === 'SEAL_APPROVE' ? 'Approved after multi-tier review' : 'Rejected due to forensic anomaly'),
      });
      setActionSuccessMsg(
        decision === 'SEAL_APPROVE'
          ? `Case sealed successfully! Receipt Hash: ${res.data.sealed_receipt_digest?.slice(0, 16)}...`
          : 'Case status updated to REJECTED.'
      );
      fetchCaseDetail();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to seal case');
    } finally {
      setSealingCase(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-slate-400">
        <div className="w-8 h-8 border-2 border-sentinel-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        Loading FDR case dossier...
      </div>
    );
  }

  if (error || !fdrCase) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-rose-400">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
        <p>{error || 'Case not found'}</p>
        <Link to="/" className="inline-flex items-center gap-1 mt-4 text-xs font-semibold text-sentinel-400">
          <ArrowLeft className="w-4 h-4" /> Return to Dashboard
        </Link>
      </div>
    );
  }

  const currentVersion = fdrCase.versions?.find((v) => v.id === fdrCase.current_version_id) || fdrCase.versions?.[0];
  const latestRisk = currentVersion?.risk_scores?.[currentVersion.risk_scores.length - 1] || null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Back button & Breadcrumb */}
      <div className="flex items-center">
        <Link
          to={normalizedRole === 'INSTITUTION' ? '/institution' : '/dashboard'}
          className="inline-flex items-center gap-1.5 text-[15px] font-semibold text-muted hover:text-ink"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Overview</span>
        </Link>
      </div>

      {actionSuccessMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      {/* Case Header Card */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 shadow-xl space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-semibold text-ink font-mono truncate" title={fdrCase.case_number}>
                {fdrCase.case_number}
              </h1>
              <span
                className={`px-3 py-1 rounded-lg text-[15px] font-semibold border ${
                  fdrCase.status === 'VERIFIED'
                    ? 'bg-surface border-soft text-ok'
                    : fdrCase.status === 'FLAGGED'
                    ? 'flag-row'
                    : 'bg-surface border-soft text-ink'
                }`}
              >
                {fdrCase.status}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Bank: <span className="font-semibold text-slate-200">{fdrCase.bank_name}</span> &bull; Certificate No:{' '}
              <span className="font-mono text-slate-200">{fdrCase.fdr_number}</span> &bull; Institution:{' '}
              <span className="text-slate-200">{fdrCase.institution?.name || fdrCase.institution_id}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowELAModal(true)}
              className="btn-primary px-3 py-2 text-[15px] flex items-center gap-1.5"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>{t('fdr_detail.view_ela')}</span>
            </button>
            <a
              href={`/api/v1/fdr/cases/${fdrCase.id}/document`}
              target="_blank"
              rel="noreferrer"
              className="btn-ghost px-3 py-2 flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download PDF</span>
            </a>
          </div>
        </div>

        {/* Trust Ladder Stepper */}
        <div className="pt-2 border-t border-slate-800">
          <TrustLadderStepper currentLevel={fdrCase.trust_level} />
        </div>
      </div>

      {/* Main Grid: Document Preview & Extracted Fields */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Document Image Preview & Risk Meter */}
        <div className="lg:col-span-5 space-y-6">
          {/* Document Preview Card */}
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[15px] font-semibold text-ink">
                Document preview
              </span>
              <button
                onClick={() => setShowELAModal(true)}
                className="text-[15px] font-semibold text-accent-text flex items-center gap-1"
              >
                <Layers className="w-4 h-4" /> ELA heatmap
              </button>
            </div>
            <div className="aspect-[3/4] w-full rounded-lg border border-soft bg-surface flex items-center justify-center p-2">
              <AuthImage
                path={`/fdr/cases/${fdrCase.id}/preview`}
                alt="FDR preview"
                className="max-h-full max-w-full object-contain cursor-pointer"
                onClick={() => setShowELAModal(true)}
              />
            </div>
          </div>

          {/* AI Risk Meter (GBDT + SHAP) */}
          {latestRisk && <RiskMeter riskScore={latestRisk} />}

          {/* Duplicate Radar Match (If flagged) */}
          {duplicateMatches.length > 0 && (
            <div className="glass-panel p-5 flag-row space-y-3">
              <div className="flex items-center gap-2 text-rose-400 font-bold text-sm">
                <Fingerprint className="w-5 h-5" />
                <span>Duplicate Radar Detection</span>
              </div>
              <p className="text-xs text-rose-300/80">
                Potential cross-institution reuse or post-release resubmission detected.
              </p>
              <div className="space-y-2">
                {duplicateMatches.map((m) => (
                  <div key={m.id} className="p-3 rounded-xl bg-slate-900/90 border border-rose-500/30 text-xs space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-rose-300">{m.match_type}</span>
                      <span className="font-mono text-[10px] text-slate-400">
                        Score: {(m.similarity_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    {m.phash_distance !== null && (
                      <div className="text-[11px] text-slate-400 font-mono">
                        Perceptual Hash Distance: {m.phash_distance} bits
                      </div>
                    )}
                    <div className="text-[11px] text-slate-400">
                      Matched Case: <span className="font-mono text-sentinel-400">{m.matching_case_id}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: OCR Fields, Forensics, Connectors & Decision */}
        <div className="lg:col-span-7 space-y-6">
          {/* Extracted Fields Table */}
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-sentinel-400" />
                <h3 className="font-bold text-slate-100 text-sm">{t('fdr_detail.extracted_fields')}</h3>
              </div>
            </div>

            <div className="space-y-2">
              {currentVersion?.extracted_fields?.map((field: any) => {
                const isEditing = editingFieldId === field.id;
                const conf = typeof field.confidence === 'number'
                  ? field.confidence
                  : (typeof field.confidence_score === 'number' ? field.confidence_score : 1.0);
                const isLowConf = conf < 0.85 || field.is_flagged_for_manual_review;
                const fieldName = (field.field_name || 'Field').replace(/_/g, ' ');
                const val = field.manual_corrected_value || field.field_value || field.normalized_value || field.raw_value || field.raw_ocr_text || 'N/A';

                return (
                  <div
                    key={field.id}
                    className={`p-3 rounded-lg grid grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto] gap-3 items-start ${
                      isLowConf ? 'flag-row' : 'border border-soft bg-surface'
                    }`}
                  >
                    <div className="min-w-0">
                      <span className="text-[15px] font-semibold text-ink line-clamp-2" title={fieldName}>
                        {fieldName}
                      </span>
                      <span
                        className={`font-mono ${isLowConf ? 'text-accent-text' : 'text-ok'}`}
                      >
                        {(conf * 100).toFixed(0)}%
                      </span>
                    </div>

                    <div className="min-w-0">
                      {isEditing ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            value={editingValue}
                            onChange={(e) => setEditingValue(e.target.value)}
                            className="flex-1 min-w-0 px-2.5 py-1 text-[15px] rounded bg-bg border border-border-strong text-ink"
                          />
                          <button
                            onClick={() => handleSaveField(field.id)}
                            disabled={savingField}
                            className="btn-primary p-1"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setEditingFieldId(null)}
                            className="btn-ghost p-1"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="text-[15px] text-ink line-clamp-2" title={String(val)}>
                          {val}
                        </div>
                      )}
                    </div>

                    {!isEditing && (
                      <button
                        onClick={() => {
                          setEditingFieldId(field.id);
                          setEditingValue(val === 'N/A' ? '' : val);
                        }}
                        className="btn-ghost p-1.5"
                        title="Correct value"
                      >
                        <Edit3 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Forensic Inspection Findings */}
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-sentinel-400" />
                <h3 className="font-bold text-slate-100 text-sm">{t('fdr_detail.forensics_tab')}</h3>
              </div>
            </div>

            <div className="space-y-2">
              {currentVersion?.forensic_findings?.map((finding: any) => {
                const isFlagged = finding.status === 'ANOMALY_FLAGGED';
                const checkTitle = (finding.check_name || finding.check_type || finding.title || 'FORENSIC CHECK').replace(/_/g, ' ');
                const category = finding.category || finding.severity || 'INSPECTION';
                const desc = finding.description || finding.details?.description || (finding.evidence_json ? JSON.stringify(finding.evidence_json) : 'Passed forensic verification check.');

                return (
                  <div
                    key={finding.id}
                    className={`p-3.5 rounded-lg text-[15px] space-y-1.5 ${
                      isFlagged ? 'flag-row' : 'bg-surface border border-soft'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-200">
                          {checkTitle}
                        </span>
                        <span className="text-[10px] uppercase font-mono text-slate-500">
                          [{category}]
                        </span>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          isFlagged
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                        }`}
                      >
                        {isFlagged ? 'ANOMALY FOR REVIEW' : 'PASS'}
                      </span>
                    </div>

                    <p className="text-slate-400 text-[11px]">
                      {desc}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Verification Connectors Panel (Honesty Rule 2: Simulated Issuer Badge) */}
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-cyan-400" />
                <h3 className="font-bold text-slate-100 text-sm">Source Verification Connectors</h3>
              </div>
              <button
                onClick={handleRunConnectors}
                disabled={verifyingConnectors || fdrCase.trust_level === 'L4_SEALED'}
                className="btn-primary px-3 py-1.5 disabled:opacity-50 flex items-center gap-1.5"
              >
                {verifyingConnectors ? (
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Key className="w-3.5 h-3.5" />
                )}
                <span>Run Connectors</span>
              </button>
            </div>

            <div className="space-y-2">
              {currentVersion?.verification_results && currentVersion.verification_results.length > 0 ? (
                currentVersion.verification_results.map((res: any) => {
                  const connectorName = res.connector_type || res.adapter_name || 'CONNECTOR';
                  const isSimulated = res.is_simulated ?? true;
                  const isConfirmed = res.status === 'CONFIRMED' || res.is_verified === true;
                  const message = res.raw_response?.message || res.raw_response_json?.message || (isConfirmed ? 'Source confirmed verification.' : 'Verification pending or discrepancy noted.');

                  return (
                    <div
                      key={res.id}
                      className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 text-xs flex items-center justify-between gap-3"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-200">{connectorName}</span>
                          {isSimulated ? (
                            <SimulatedBadge />
                          ) : connectorName.includes('QR') ? (
                            <RealCryptoBadge />
                          ) : (
                            <RealSignatureBadge />
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          {message}
                        </p>
                      </div>

                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          isConfirmed
                            ? 'bg-emerald-500/20 text-emerald-300'
                            : 'bg-rose-500/20 text-rose-300'
                        }`}
                      >
                        {isConfirmed ? 'CONFIRMED' : 'DISCREPANCY'}
                      </span>
                    </div>
                  );
                })
              ) : (
                <div className="text-center p-4 text-xs text-slate-500">
                  Connectors not yet executed for this version. Click "Run Connectors" to verify via QR, PKI signature, and synthetic bank ledger.
                </div>
              )}
            </div>
          </div>

          {/* Official Human Approval Actions (Honesty Rule 5) */}
          {isOfficial && fdrCase.trust_level !== 'L4_SEALED' && (
            <div className="glass-panel p-5 rounded-2xl border border-amber-500/30 bg-amber-500/5 space-y-4">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-amber-400" />
                <h3 className="font-bold text-white text-sm">
                  {t('fdr_detail.official_actions')}
                </h3>
              </div>
              <p className="text-xs text-slate-400">
                Honesty Rule 5: A human official makes the final decision on every flagged or verified FDR. Sealing locks the record and generates a tamper-proof QR receipt digest.
              </p>

              <div>
                <input
                  type="text"
                  value={decisionNotes}
                  onChange={(e) => setDecisionNotes(e.target.value)}
                  placeholder="Official approval / rejection justification notes..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => handleSealDecision('SEAL_APPROVE')}
                  disabled={sealingCase}
                  className="btn-primary flex-1 py-2.5 flex items-center justify-center gap-1.5"
                >
                  <Lock className="w-3.5 h-3.5" />
                  <span>{t('fdr_detail.approve_seal')}</span>
                </button>
                <button
                  onClick={() => handleSealDecision('REJECT')}
                  disabled={sealingCase}
                  className="flag-row px-4 py-2.5 text-[15px] font-semibold flex items-center gap-1.5"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>{t('fdr_detail.reject')}</span>
                </button>
              </div>
            </div>
          )}

          {/* Sealed Receipt Badge (If L4 Sealed) */}
          {fdrCase.trust_level === 'L4_SEALED' && (
            <div className="glass-panel p-5 rounded-2xl border border-cyan-500/40 bg-cyan-500/5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-cyan-300 font-bold text-sm">
                  <Lock className="w-4 h-4 text-cyan-400" />
                  <span>AICTE Sealed Receipt Digest (L4)</span>
                </div>
                <span className="text-[10px] font-mono uppercase bg-cyan-500/20 text-cyan-300 px-2 py-0.5 rounded border border-cyan-500/30">
                  Locked Record
                </span>
              </div>
              <p className="text-xs text-slate-300">
                This FDR record is cryptographically sealed and immutable. Anyone with the receipt digest can verify authenticity on the public verification portal.
              </p>
              <Link
                to="/verify-receipt"
                className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-semibold"
              >
                <span>Check on Public Verification Portal</span>
                <CheckCircle2 className="w-3.5 h-3.5" />
              </Link>
            </div>
          )}

          {/* Audit Chain Timeline for this Case */}
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-sentinel-400" />
              <h3 className="font-bold text-slate-100 text-sm">Trust Ladder Audit Timeline</h3>
            </div>
            <div className="space-y-2">
              {(fdrCase.trust_events || []).map((ev: any) => (
                <div
                  key={ev.id}
                  className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs flex items-center justify-between"
                >
                  <div>
                    <span className="font-semibold text-sentinel-300">
                      {ev.from_level ? `${ev.from_level} → ${ev.to_level}` : `Initial: ${ev.to_level}`}
                    </span>
                    <p className="text-[11px] text-slate-400">{ev.reason || ev.notes || ev.trigger_type || 'Trust transition recorded'}</p>
                  </div>
                  <span className="font-mono text-muted shrink-0" title={ev.created_at || ''}>
                    {ev.created_at ? new Date(ev.created_at).toLocaleString() : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ELA Heatmap Modal */}
      <ELAModal
        isOpen={showELAModal}
        onClose={() => setShowELAModal(false)}
        caseId={fdrCase.id}
      />
    </div>
  );
};
