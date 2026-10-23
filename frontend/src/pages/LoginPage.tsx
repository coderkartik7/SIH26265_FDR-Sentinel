import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Lock, Mail, Key, AlertCircle, ArrowRight, CheckCircle2, UserCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import apiClient from '../services/api';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [totpRequired, setTotpRequired] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // TOTP Setup Modal State
  const [showMfaSetup, setShowMfaSetup] = useState(false);
  const [mfaSecret, setMfaSecret] = useState('');
  const [mfaQrBase64, setMfaQrBase64] = useState('');
  const [mfaVerifyCode, setMfaVerifyCode] = useState('');
  const [mfaSuccessMsg, setMfaSuccessMsg] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage(null);

    try {
      const res = await apiClient.post('/auth/login', {
        email,
        password,
        totp_code: totpCode || null,
      });

      const { access_token, refresh_token, role, user_id, full_name, institution_id } = res.data;
      login(access_token, refresh_token, {
        id: user_id,
        email,
        full_name,
        role,
        institution_id,
        totp_enabled: !!totpCode,
      });

      const upperRole = String(role || '').toUpperCase();
      if (upperRole === 'INSTITUTION') {
        navigate('/institution');
      } else {
        navigate('/dashboard');
      }
    } catch (err: any) {
      if (err.response?.data?.detail === 'TOTP_REQUIRED') {
        setTotpRequired(true);
        setErrorMessage('Two-Factor Authentication is enabled on this account. Enter your 6-digit TOTP code.');
      } else {
        setErrorMessage(err.response?.data?.detail || 'Authentication failed. Please check credentials.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (presetEmail: string, presetPass: string) => {
    setEmail(presetEmail);
    setPassword(presetPass);
    setTotpCode('');
    setTotpRequired(false);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-slate-950 relative overflow-hidden">
      {/* Background Glow effects */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-sentinel-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center">
        <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-tr from-sentinel-700 via-sentinel-500 to-amber-500 p-0.5 shadow-2xl flex items-center justify-center mb-4">
          <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center">
            <Shield className="w-8 h-8 text-sentinel-400" />
          </div>
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
          FDR<span className="text-sentinel-400">-Sentinel</span>
        </h2>
        <p className="mt-1 text-xs text-slate-400 max-w-sm mx-auto">
          {t('app.subtitle')}
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10 px-4">
        <div className="glass-panel py-8 px-6 sm:px-8 rounded-2xl shadow-2xl border border-slate-800">
          {errorMessage && (
            <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleLogin}>
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                {t('auth.email')}
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. official@aicte.gov.in"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-sentinel-500 placeholder-slate-600 font-medium"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                {t('auth.password')}
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-sentinel-500 placeholder-slate-600 font-medium"
                />
              </div>
            </div>

            {totpRequired && (
              <div className="p-3 rounded-xl bg-sentinel-500/10 border border-sentinel-500/30">
                <label className="block text-xs font-semibold text-sentinel-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <Key className="w-3.5 h-3.5" />
                  {t('auth.totp_code')}
                </label>
                <input
                  type="text"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value)}
                  placeholder="123456"
                  className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-sentinel-500/50 text-center font-mono text-lg font-bold tracking-widest text-slate-100 focus:outline-none focus:border-sentinel-400"
                />
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-sentinel-600 to-sentinel-500 hover:from-sentinel-500 hover:to-sentinel-400 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-sentinel-600/30 transition-all hover:scale-[1.01]"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <span>{t('auth.login_btn')}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Quick Fill Test Accounts */}
          <div className="mt-6 pt-5 border-t border-slate-800">
            <span className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2.5 text-center">
              Demonstration Quick-Fill Logins:
            </span>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => handleQuickFill('official@aicte.gov.in', 'OfficialSecret2026!')}
                className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-left transition-colors"
              >
                <div className="font-semibold text-sentinel-300 flex items-center gap-1">
                  <UserCheck className="w-3 h-3" />
                  AICTE Official
                </div>
                <div className="text-[10px] text-slate-400 truncate">official@aicte.gov.in</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill('admin@aicte.gov.in', 'AdminSecret2026!')}
                className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-left transition-colors"
              >
                <div className="font-semibold text-amber-300 flex items-center gap-1">
                  <Shield className="w-3 h-3" />
                  Administrator
                </div>
                <div className="text-[10px] text-slate-400 truncate">admin@aicte.gov.in</div>
              </button>

              <button
                type="button"
                onClick={() => handleQuickFill('institution1@aicte.gov.in', 'InstSecret2026!')}
                className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-left transition-colors col-span-2"
              >
                <div className="font-semibold text-slate-300 flex items-center gap-1">
                  <Lock className="w-3 h-3" />
                  Institution Account (Delhi Tech Institute)
                </div>
                <div className="text-[10px] text-slate-400 truncate">institution1@aicte.gov.in</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
