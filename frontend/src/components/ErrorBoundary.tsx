import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, ArrowLeft } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="max-w-2xl mx-auto my-16 p-8 glass-panel rounded-2xl border border-rose-500/30 text-center space-y-4 shadow-2xl">
          <div className="w-12 h-12 rounded-2xl bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-100">Something went wrong while displaying this view</h2>
          <p className="text-xs text-rose-300 font-mono bg-rose-950/40 p-3 rounded-xl border border-rose-900/50 break-words">
            {this.state.error?.message || 'Unknown render error'}
          </p>
          <div className="flex items-center justify-center gap-3 pt-2">
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center gap-2 transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Reload Page
            </button>
            <a
              href="/dashboard"
              className="px-4 py-2 rounded-xl bg-sentinel-600 hover:bg-sentinel-500 text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-md shadow-sentinel-600/30"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Return to Dashboard
            </a>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
