import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Shield,
  Layers,
  Clock,
  Search,
  CheckCircle,
  FileText,
  LogOut,
  Languages,
  User as UserIcon,
  HelpCircle,
  Activity
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';

interface NavbarProps {
  onOpenDemoClock: () => void;
  onOpenAskSentinel: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenDemoClock, onOpenAskSentinel }) => {
  const { user, role, logout } = useAuth();
  const { t, i18n } = useTranslation();
  const location = useLocation();

  const toggleLanguage = () => {
    const nextLang = i18n.language === 'en' ? 'hi' : 'en';
    i18n.changeLanguage(nextLang);
  };

  const normalizedRole = role ? String(role).toUpperCase() : null;
  const isOfficial = normalizedRole === 'OFFICIAL' || normalizedRole === 'ADMIN';

  const navItems = [
    ...(isOfficial
      ? [
          { to: '/dashboard', label: t('nav.dashboard'), icon: Layers },
          { to: '/monitoring', label: t('nav.monitoring'), icon: Clock },
          { to: '/audit-chain', label: t('nav.audit_chain'), icon: Activity },
        ]
      : [
          { to: '/institution', label: t('nav.institution_portal'), icon: FileText },
        ]),
    { to: '/verify-receipt', label: t('nav.verify_receipt'), icon: CheckCircle },
  ];

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-800 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sentinel-700 via-sentinel-500 to-amber-500 p-0.5 shadow-lg group-hover:scale-105 transition-transform">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Shield className="w-5 h-5 text-sentinel-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight text-white">
                FDR<span className="text-sentinel-400">-Sentinel</span>
              </span>
              <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                AICTE SIH'26
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">Security Deposit Fraud Prevention</p>
          </div>
        </Link>

        {/* Navigation Links */}
        <nav className="hidden md:flex items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-sentinel-600/30 text-sentinel-300 border border-sentinel-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Quick Actions & User */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Ask-Sentinel Natural Language Query Button */}
          <button
            onClick={onOpenAskSentinel}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-sentinel-600 to-indigo-600 hover:from-sentinel-500 hover:to-indigo-500 text-white shadow-md shadow-sentinel-500/20 transition-all hover:scale-105"
            title="Ask Sentinel in Natural Language"
          >
            <Search className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Ask-Sentinel</span>
          </button>

          {/* Demo Clock Jump Button (For Official/Admin) */}
          {isOfficial && (
            <button
              onClick={onOpenDemoClock}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-amber-400 border border-amber-500/30 transition-all"
              title="Demonstration Time Jump Controller"
            >
              <Clock className="w-3.5 h-3.5 text-amber-400 animate-pulse-subtle" />
              <span className="hidden lg:inline">Demo Clock</span>
            </button>
          )}

          {/* Language Switcher */}
          <button
            onClick={toggleLanguage}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
            title="Switch Language (English / Hindi)"
          >
            <Languages className="w-3.5 h-3.5 text-sentinel-400" />
            <span className="uppercase">{i18n.language}</span>
          </button>

          {/* User profile / Logout */}
          {user ? (
            <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs font-medium text-slate-200 truncate max-w-[120px]">
                  {user.full_name || user.email}
                </span>
                <span className="text-[10px] text-sentinel-400 font-mono font-semibold">
                  {user.role}
                </span>
              </div>
              <button
                onClick={logout}
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                title={t('nav.logout')}
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-sentinel-600 hover:bg-sentinel-500 text-white transition-all"
            >
              <UserIcon className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};
