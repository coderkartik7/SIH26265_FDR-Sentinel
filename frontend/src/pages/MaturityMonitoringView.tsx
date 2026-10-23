import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Clock,
  AlertTriangle,
  Bell,
  CheckCircle2,
  TrendingUp,
  RefreshCw,
  Send,
  ArrowRight,
  ShieldAlert,
  Play
} from 'lucide-react';
import apiClient from '../services/api';
import { Alert, LiabilityForecast } from '../types';

interface MaturityMonitoringViewProps {
  onOpenDemoClock: () => void;
}

export const MaturityMonitoringView: React.FC<MaturityMonitoringViewProps> = ({ onOpenDemoClock }) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [forecast, setForecast] = useState<LiabilityForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [alertsRes, forecastRes] = await Promise.all([
        apiClient.get<Alert[]>('/monitoring/alerts'),
        apiClient.get<LiabilityForecast>('/monitoring/liability-forecast?months=24'),
      ]);
      setAlerts(alertsRes.data);
      setForecast(forecastRes.data);
    } catch (err: any) {
      console.error('Failed to load maturity alerts', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleScanAlerts = async () => {
    setScanning(true);
    setScanMessage(null);
    try {
      const res = await apiClient.post('/monitoring/scan-alerts');
      setScanMessage(`Scan completed: ${res.data.alerts_created} new alert(s) triggered, ${res.data.escalations_triggered} auto-escalation(s).`);
      fetchData();
    } catch (err: any) {
      setScanMessage(err.response?.data?.detail || 'Scan failed.');
    } finally {
      setScanning(false);
    }
  };

  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await apiClient.post(`/monitoring/alerts/${alertId}/acknowledge`);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to acknowledge alert');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">Deposit Maturity & Alert Center</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
              Proactive Monitoring
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Maturity notifications at 90, 60, 30, 15, and 7 days. Automatic escalation to senior officials for unacknowledged alerts &gt;7 days.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleScanAlerts}
            disabled={scanning}
            className="px-4 py-2.5 rounded-xl bg-sentinel-600 hover:bg-sentinel-500 text-white text-xs font-bold flex items-center gap-2 transition-all shadow-md shadow-sentinel-600/30"
          >
            {scanning ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            <span>Trigger Maturity Scan</span>
          </button>
          <button
            onClick={onOpenDemoClock}
            className="px-4 py-2.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-bold flex items-center gap-2 transition-all shadow-md"
          >
            <Clock className="w-4 h-4 animate-pulse-subtle" />
            <span>Time Jump Controller</span>
          </button>
        </div>
      </div>

      {scanMessage && (
        <div className="p-3.5 rounded-xl bg-sentinel-500/10 border border-sentinel-500/30 text-sentinel-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-sentinel-400 flex-shrink-0" />
          <span>{scanMessage}</span>
        </div>
      )}

      {/* Alerts Table */}
      <div className="glass-panel rounded-2xl border border-slate-800 shadow-xl overflow-hidden">
        <div className="p-4 sm:p-6 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-amber-400" />
            <h3 className="font-bold text-slate-100 text-sm">System Alerts & Notifications ({alerts.length})</h3>
          </div>
          <span className="text-xs text-slate-400">WebSocket broadcast + MailHog SMTP dispatched</span>
        </div>

        {alerts.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            No active maturity alerts. Use the Time Jump Controller to advance system time and trigger maturity scans.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-slate-400 uppercase font-mono tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Alert Message</th>
                  <th className="py-3 px-4">Escalation</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {alerts.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          a.severity === 'CRITICAL'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            : a.severity === 'HIGH'
                            ? 'bg-orange-500/20 text-orange-300 border border-orange-500/40'
                            : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        }`}
                      >
                        {a.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold text-slate-300">
                      {a.alert_type}
                    </td>
                    <td className="py-3 px-4 text-slate-200">{a.message}</td>
                    <td className="py-3 px-4">
                      {a.escalation_level > 0 ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                          Level {a.escalation_level} (Senior Official)
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-500">Standard</span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400">
                      {new Date(a.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right flex items-center justify-end gap-2">
                      {!a.is_acknowledged && (
                        <button
                          onClick={() => handleAcknowledgeAlert(a.id)}
                          className="px-2.5 py-1 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 text-[11px] font-semibold transition-all"
                        >
                          Acknowledge
                        </button>
                      )}
                      {a.case_id && (
                        <Link
                          to={`/cases/${a.case_id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-medium text-[11px] border border-slate-700"
                        >
                          <span>Case</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
