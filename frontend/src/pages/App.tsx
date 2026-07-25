import React, { useState } from 'react';
import AuthForm from '../components/AuthForm';
import { AuthProvider, useAuth } from '../context/AuthContext';
import Dashboard from './Dashboard';

function AppContent() {
  const { isAuthenticated, isInitializing, login, register } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');

  if (isInitializing) {
    return (
      <main className="centered-page">
        <div className="loading-card" role="status">Restoring your secure session…</div>
      </main>
    );
  }

  if (isAuthenticated) {
    return <Dashboard />;
  }

  return (
    <main className="auth-page">
      <div className="auth-intro">
        <p className="eyebrow">Privacy-first continuity planning</p>
        <h2>Organize what exists, what may exist, and what must happen next.</h2>
        <p>
          LegacyGuard separates verified assets from unconfirmed discovery findings and keeps every decision under your control.
        </p>
      </div>
      <AuthForm
        mode={mode}
        onSubmit={mode === 'login' ? login : register}
        onSwitchMode={() => setMode((current) => (current === 'login' ? 'register' : 'login'))}
      />
    </main>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
