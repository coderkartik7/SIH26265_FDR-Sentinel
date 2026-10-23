import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { DemoClockModal } from './components/DemoClockModal';
import { AskSentinelModal } from './components/AskSentinelModal';
import { LoginPage } from './pages/LoginPage';
import { OfficialDashboard } from './pages/OfficialDashboard';
import { InstitutionPortal } from './pages/InstitutionPortal';
import { FDRDetailView } from './pages/FDRDetailView';
import { MaturityMonitoringView } from './pages/MaturityMonitoringView';
import { AuditVerifyView } from './pages/AuditVerifyView';
import { PublicReceiptVerifyView } from './pages/PublicReceiptVerifyView';
import { ErrorBoundary } from './components/ErrorBoundary';

const ProtectedRoute: React.FC<{ children: React.ReactNode; allowedRoles?: string[] }> = ({
  children,
  allowedRoles,
}) => {
  const { isAuthenticated, role } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const normalizedRole = role ? String(role).toUpperCase() : null;
  const normalizedAllowed = allowedRoles?.map((r) => r.toUpperCase());

  if (normalizedAllowed && normalizedRole && !normalizedAllowed.includes(normalizedRole)) {
    return <Navigate to={normalizedRole === 'INSTITUTION' ? '/institution' : '/dashboard'} replace />;
  }

  return <>{children}</>;
};

const RootRedirect: React.FC = () => {
  const { isAuthenticated, role } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  const normalizedRole = role ? String(role).toUpperCase() : null;
  if (normalizedRole === 'INSTITUTION') return <Navigate to="/institution" replace />;
  return <Navigate to="/dashboard" replace />;
};

export const AppContent: React.FC = () => {
  const [isDemoClockOpen, setIsDemoClockOpen] = useState(false);
  const [isAskSentinelOpen, setIsAskSentinelOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col text-slate-100">
      <Navbar
        onOpenDemoClock={() => setIsDemoClockOpen(true)}
        onOpenAskSentinel={() => setIsAskSentinelOpen(true)}
      />

      <main className="flex-1">
        <ErrorBoundary>
          <Routes>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Official / Admin Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute allowedRoles={['OFFICIAL', 'ADMIN']}>
                <OfficialDashboard
                  onOpenDemoClock={() => setIsDemoClockOpen(true)}
                  onOpenAskSentinel={() => setIsAskSentinelOpen(true)}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/monitoring"
            element={
              <ProtectedRoute allowedRoles={['OFFICIAL', 'ADMIN']}>
                <MaturityMonitoringView onOpenDemoClock={() => setIsDemoClockOpen(true)} />
              </ProtectedRoute>
            }
          />
          <Route
            path="/audit-chain"
            element={
              <ProtectedRoute allowedRoles={['OFFICIAL', 'ADMIN']}>
                <AuditVerifyView />
              </ProtectedRoute>
            }
          />

          {/* Institution Route */}
          <Route
            path="/institution"
            element={
              <ProtectedRoute allowedRoles={['INSTITUTION', 'OFFICIAL', 'ADMIN']}>
                <InstitutionPortal />
              </ProtectedRoute>
            }
          />

          {/* Detail Dossier Route */}
          <Route
            path="/cases/:id"
            element={
              <ProtectedRoute>
                <FDRDetailView />
              </ProtectedRoute>
            }
          />

          {/* Public Verification Routes */}
          <Route path="/verify-receipt" element={<PublicReceiptVerifyView />} />
          <Route path="/verify-receipt/:digest" element={<PublicReceiptVerifyView />} />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </ErrorBoundary>
      </main>

      {/* Global Modals */}
      <DemoClockModal
        isOpen={isDemoClockOpen}
        onClose={() => setIsDemoClockOpen(false)}
      />
      <AskSentinelModal
        isOpen={isAskSentinelOpen}
        onClose={() => setIsAskSentinelOpen(false)}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>AICTE Security Deposit Verification Portal &bull; SIH 2026 Problem Statement SIH26265</span>
          <span className="font-mono text-[11px] text-slate-400">
            *Evaluated on synthetic dataset generated with fixed seed=42 &bull; No hardcoded metrics
          </span>
        </div>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  );
};

export default App;
