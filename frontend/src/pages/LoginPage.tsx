import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
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
  const [logoOk, setLogoOk] = useState(true);

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
        setErrorMessage('Two-factor authentication is enabled. Enter your 6-digit code.');
      } else {
        setErrorMessage(err.response?.data?.detail || 'Sign in failed. Please check credentials.');
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

  const inputClass =
    'w-full px-3 py-2 rounded-lg bg-surface border border-border-strong text-ink text-[15px] focus:outline-none';

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 px-4 bg-bg">
      <div className="mx-auto w-full max-w-md">
        <div className="glass-panel py-8 px-6 text-left">
          <div className="flex items-center gap-2 mb-6">
            {logoOk ? (
              <img
                src="/logo.png"
                alt="FDR-Sentinel"
                className="app-logo h-8 w-auto object-contain"
                onError={() => setLogoOk(false)}
              />
            ) : (
              <span className="font-semibold text-ink">FDR-Sentinel</span>
            )}
          </div>

          <h1 className="text-xl font-semibold text-ink mb-4">Sign in</h1>

          {errorMessage && (
            <div className="flag-row mb-4 p-3 text-[15px] flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleLogin}>
            <div>
              <label className="block text-[15px] font-semibold text-ink mb-1.5">
                {t('auth.email')}
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="official@aicte.gov.in"
                className={inputClass}
              />
            </div>

            <div>
              <label className="block text-[15px] font-semibold text-ink mb-1.5">
                {t('auth.password')}
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputClass}
              />
            </div>

            {totpRequired && (
              <div>
                <label className="block text-[15px] font-semibold text-ink mb-1.5">
                  {t('auth.totp_code')}
                </label>
                <input
                  type="text"
                  maxLength={6}
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value)}
                  placeholder="123456"
                  className={`${inputClass} font-mono text-center`}
                />
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 px-4">
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-soft">
            <span className="block text-[15px] text-muted mb-2">Demo accounts</span>
            <div className="flex flex-col items-start gap-1">
              <button
                type="button"
                onClick={() => handleQuickFill('official@aicte.gov.in', 'OfficialSecret2026!')}
                className="text-[15px] text-accent-text"
              >
                Official
              </button>
              <button
                type="button"
                onClick={() => handleQuickFill('admin@aicte.gov.in', 'AdminSecret2026!')}
                className="text-[15px] text-accent-text"
              >
                Administrator
              </button>
              <button
                type="button"
                onClick={() => handleQuickFill('institution1@aicte.gov.in', 'InstSecret2026!')}
                className="text-[15px] text-accent-text"
              >
                Institution
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
