import React, { useState } from 'react';
import { X, Search, Sparkles, Send, Database, ArrowRight, ShieldCheck, CornerDownRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import apiClient from '../services/api';
import { AskSentinelResult, FDRCaseListItem } from '../types';

interface AskSentinelModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const suggestedPrompts = [
  "Show all flagged FDRs from ACT bank",
  "Find deposits above 25 lakhs",
  "Which deposits are in North region?",
  "Show FDRs requiring immediate attention",
  "List all L4 sealed certificates",
  "Show active FDRs from BNB bank",
];

export const AskSentinelModal: React.FC<AskSentinelModalProps> = ({ isOpen, onClose }) => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskSentinelResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAsk = async (queryText: string) => {
    if (!queryText.trim()) return;
    setLoading(true);
    setErrorMsg(null);
    setQuestion(queryText);
    try {
      const res = await apiClient.post<AskSentinelResult>('/ask-sentinel', {
        question: queryText.trim(),
        limit: 20,
      });
      setResult(res.data);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to process natural language query');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md">
      <div className="w-full max-w-4xl max-h-[90vh] glass-panel rounded-2xl border border-sentinel-500/40 p-6 shadow-2xl flex flex-col relative overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-sentinel-600 to-indigo-600 text-white shadow-lg">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-slate-100">Ask-Sentinel Natural Language Query</h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sentinel-500/20 text-sentinel-300 border border-sentinel-500/30">
                  SQL-Parameterized Engine
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Ask in plain English. Guaranteed no raw SQL hallucination &bull; Hash-chained audit logged
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Input Bar */}
        <div className="pt-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAsk(question);
            }}
            className="flex gap-2"
          >
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask e.g. 'Show all flagged FDRs from ACT bank' or 'Deposits over 20 lakhs'..."
                className="w-full pl-10 pr-4 py-3 rounded-xl bg-slate-800/90 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-sentinel-500 placeholder-slate-500 shadow-inner"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="px-5 py-3 rounded-xl bg-sentinel-600 hover:bg-sentinel-500 disabled:opacity-50 text-white font-bold text-sm flex items-center gap-2 transition-all shadow-md shadow-sentinel-600/30"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              <span>Query</span>
            </button>
          </form>

          {/* Preset Suggestion Chips */}
          <div className="flex flex-wrap gap-1.5 mt-3">
            {suggestedPrompts.map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => handleAsk(prompt)}
                className="px-2.5 py-1 rounded-lg text-xs bg-slate-800/70 hover:bg-slate-700 border border-slate-700/80 text-slate-300 hover:text-white transition-colors"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        {/* Body / Results */}
        <div className="flex-1 overflow-y-auto mt-4 pr-1 space-y-4">
          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              {errorMsg}
            </div>
          )}

          {result && (
            <div className="space-y-4">
              {/* Query Interpretation Plan */}
              <div className="p-3.5 rounded-xl bg-slate-800/70 border border-slate-700/60 flex flex-col gap-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-sentinel-400" />
                    Interpreted Safe Query Plan:
                  </span>
                  <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
                    <span>Audit Log #{result.audit_entry_id}</span>
                    <span>&bull;</span>
                    <span>{result.latency_ms.toFixed(1)} ms</span>
                  </div>
                </div>
                <div className="bg-slate-900/90 rounded-lg p-2.5 font-mono text-xs text-sentinel-300 overflow-x-auto border border-slate-800">
                  {JSON.stringify(result.interpreted_query, null, 2)}
                </div>
              </div>

              {/* Results Count */}
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-semibold text-slate-300">
                  Matching FDR Cases ({result.total_matching}):
                </span>
              </div>

              {/* Results Table */}
              {result.results.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-sm glass-card rounded-xl">
                  No FDR records matched this criteria.
                </div>
              ) : (
                <div className="glass-card rounded-xl overflow-hidden border border-slate-800">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-800/80 text-slate-400 border-b border-slate-700/80 uppercase font-mono tracking-wider">
                        <tr>
                          <th className="py-2.5 px-3">Case ID</th>
                          <th className="py-2.5 px-3">Bank</th>
                          <th className="py-2.5 px-3">FDR Number</th>
                          <th className="py-2.5 px-3">Principal</th>
                          <th className="py-2.5 px-3">Trust Level</th>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        {result.results.map((c) => (
                          <tr key={c.id} className="hover:bg-slate-800/50 transition-colors">
                            <td className="py-2 px-3 font-mono text-sentinel-300 font-semibold">
                              {c.case_number}
                            </td>
                            <td className="py-2 px-3 text-slate-200">{c.bank_name}</td>
                            <td className="py-2 px-3 font-mono text-slate-300">{c.fdr_number}</td>
                            <td className="py-2 px-3 font-mono-nums font-semibold text-slate-100">
                              ₹{(c.principal_amount).toLocaleString('en-IN')}
                            </td>
                            <td className="py-2 px-3">
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sentinel-500/10 text-sentinel-400 border border-sentinel-500/20">
                                {c.trust_level}
                              </span>
                            </td>
                            <td className="py-2 px-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  c.status === 'VERIFIED'
                                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                    : c.status === 'FLAGGED'
                                    ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                    : 'bg-slate-700/50 text-slate-300'
                                }`}
                              >
                                {c.status}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-right">
                              <Link
                                to={`/cases/${c.id}`}
                                onClick={onClose}
                                className="inline-flex items-center gap-1 text-xs text-sentinel-400 hover:text-sentinel-300 font-semibold"
                              >
                                <span>Inspect</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
