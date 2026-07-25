import React, { useState } from 'react';
import { ApiError } from '../services/api';

type AuthFormProps = {
  mode: 'login' | 'register';
  onSubmit: (email: string, password: string) => Promise<void>;
  onSwitchMode: () => void;
};

function validatePassword(password: string): string | null {
  if (password.length < 12) return 'Use at least 12 characters.';
  if (!/[A-Z]/.test(password)) return 'Include at least one uppercase letter.';
  if (!/[a-z]/.test(password)) return 'Include at least one lowercase letter.';
  if (!/[0-9]/.test(password)) return 'Include at least one number.';
  if (!/[!@#$%^&*()\-_=+\[\]{};:'",.<>/?]/.test(password)) return 'Include at least one special character.';
  return null;
}

export default function AuthForm({ mode, onSubmit, onSwitchMode }: AuthFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isRegister = mode === 'register';

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!email.trim()) {
      setError('Enter your email address.');
      return;
    }

    if (isRegister) {
      const passwordError = validatePassword(password);
      if (passwordError) {
        setError(passwordError);
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match.');
        return;
      }
    }

    setIsSubmitting(true);
    try {
      await onSubmit(email.trim(), password);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to complete the request.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="auth-card" aria-labelledby="auth-title">
      <div className="brand-mark" aria-hidden="true">LG</div>
      <h1 id="auth-title">{isRegister ? 'Create your LegacyGuard account' : 'Welcome back'}</h1>
      <p className="muted">
        {isRegister
          ? 'Create a private account for your asset-continuity records.'
          : 'Sign in to your private LegacyGuard workspace.'}
      </p>

      <form onSubmit={handleSubmit} noValidate>
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={isSubmitting}
          required
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          type="password"
          autoComplete={isRegister ? 'new-password' : 'current-password'}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={isSubmitting}
          required
        />

        {isRegister && (
          <>
            <p className="password-help">
              Use 12+ characters with uppercase, lowercase, a number, and a special character.
            </p>
            <label htmlFor="confirm-password">Confirm password</label>
            <input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              disabled={isSubmitting}
              required
            />
          </>
        )}

        {error && <div className="error-message" role="alert">{error}</div>}

        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in'}
        </button>
      </form>

      <button className="link-button" type="button" onClick={onSwitchMode} disabled={isSubmitting}>
        {isRegister ? 'Already have an account? Sign in' : 'Need an account? Register'}
      </button>
    </section>
  );
}
