import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Search,
  Clock,
  Languages,
  User as UserIcon,
  LogOut,
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
  const [logoOk, setLogoOk] = useState(true);

  const toggleLanguage = () => {
    const nextLang = i18n.language === 'en' ? 'hi' : 'en';
    i18n.changeLanguage(nextLang);
  };

  const normalizedRole = role ? String(role).toUpperCase() : null;
  const isOfficial = normalizedRole === 'OFFICIAL' || normalizedRole === 'ADMIN';

  const navItems = [
    ...(isOfficial
      ? [
          { to: '/dashboard', label: 'Dashboard' },
          { to: '/monitoring', label: 'Alerts' },
          { to: '/audit-chain', label: 'Audit' },
        ]
      : [
          { to: '/institution', label: t('nav.institution_portal') },
        ]),
    { to: '/verify-receipt', label: 'Verify receipt' },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-soft bg-surface">
      <div className="app-shell app-header px-4">
      <div className="flex items-center gap-6 min-h-16 w-full min-w-0">
        <Link to="/" className="flex items-center gap-2 shrink-0 whitespace-nowrap">
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
        </Link>

        <nav className="app-header-nav flex flex-1 items-center gap-6 whitespace-nowrap">
          {navItems.map((item) => {
            const isActive = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`text-[15px] whitespace-nowrap pb-0.5 ${
                  isActive
                    ? 'text-accent-text font-semibold border-b-2 border-accent'
                    : 'text-muted hover:text-ink'
                }`}
                style={{ transition: 'color 150ms' }}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3 shrink-0 whitespace-nowrap">
          <button
            onClick={onOpenAskSentinel}
            className="btn-primary flex items-center gap-1.5 px-3 py-1.5"
            title="Ask-Sentinel"
          >
            <Search className="w-4 h-4" />
            <span className="hidden sm:inline">Ask-Sentinel</span>
          </button>

          <button
            onClick={toggleLanguage}
            className="btn-ghost flex items-center gap-1 px-2.5 py-1.5"
            title="Switch language"
          >
            <Languages className="w-4 h-4" />
            <span className="hidden sm:inline">{i18n.language === 'hi' ? 'Hi' : 'En'}</span>
          </button>

          {isOfficial && (
            <button
              onClick={onOpenDemoClock}
              className="btn-ghost flex items-center gap-1.5 px-2.5 py-1.5"
              title="Demo clock"
            >
              <Clock className="w-4 h-4" />
              <span className="hidden xl:inline">Demo clock</span>
            </button>
          )}

          {user ? (
            <div className="flex items-center gap-2 pl-2 border-l border-soft">
              <div className="hidden xl:flex flex-col min-w-0">
                <span className="text-[15px] font-semibold text-ink truncate max-w-[140px]" title={user.full_name || user.email}>
                  {user.full_name || user.email}
                </span>
                <span className="font-mono text-muted" title={user.role}>
                  {user.role}
                </span>
              </div>
              <button
                onClick={logout}
                className="p-1.5 rounded-lg text-muted hover:text-accent-text"
                title={t('nav.logout')}
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="btn-primary flex items-center gap-1.5 px-3 py-1.5"
            >
              <UserIcon className="w-4 h-4" />
              <span>Sign in</span>
            </Link>
          )}
        </div>
      </div>
      </div>
    </header>
  );
};
