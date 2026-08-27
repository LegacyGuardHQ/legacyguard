import React, { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import AuthForm from '../components/AuthForm';
import { useAuth } from '../context/AuthContext';
import { usePageTitle } from '../hooks/usePageTitle';

type LoginLocationState = {
  from?: { pathname?: string };
};

export default function LoginPage() {
  const { isAuthenticated, isInitializing, sessionError, login, register } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [registrationNotice, setRegistrationNotice] = useState<string | null>(null);
  const location = useLocation();
  usePageTitle(mode === 'login' ? 'Sign in' : 'Register');

  if (isInitializing) {
    return (
      <main className="centered-page">
        <div className="loading-card" role="status">Restoring your secure session…</div>
      </main>
    );
  }

  if (isAuthenticated) {
    const state = location.state as LoginLocationState | null;
    return <Navigate to={state?.from?.pathname || '/workspace'} replace />;
  }

  async function handleRegistration(email: string, password: string) {
    const message = await register(email, password);
    setRegistrationNotice(message);
    setMode('login');
  }

  return (
    <main className="auth-page">
      <div className="auth-intro">
        {sessionError && <div className="error-message" role="alert">{sessionError}</div>}
        <p className="eyebrow">Privacy-first continuity planning</p>
        <h2>Organize what exists, what may exist, and what must happen next.</h2>
        <p>
          LegacyGuard separates verified assets from unconfirmed discovery findings and keeps every decision under your control.
        </p>
      </div>
      <AuthForm
        mode={mode}
        onSubmit={mode === 'login' ? login : handleRegistration}
        onSwitchMode={() => {
          setRegistrationNotice(null);
          setMode((current) => (current === 'login' ? 'register' : 'login'));
        }}
      />
      {registrationNotice && <div className="success-message" role="status">{registrationNotice}</div>}
    </main>
  );
}
