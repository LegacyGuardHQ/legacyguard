import React, { useState } from 'react';
import HealthStatus from '../components/HealthStatus';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../services/api';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  async function handleLogout() {
    setLogoutError(null);
    setIsLoggingOut(true);
    try {
      await logout();
    } catch (error) {
      setLogoutError(error instanceof ApiError ? error.message : 'Logout could not be completed.');
      setIsLoggingOut(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <div className="app-title">LegacyGuard</div>
          <div className="app-subtitle">Private asset continuity workspace</div>
        </div>
        <div className="header-actions">
          <HealthStatus />
          <button className="secondary-button" onClick={handleLogout} disabled={isLoggingOut}>
            {isLoggingOut ? 'Signing out…' : 'Sign out'}
          </button>
        </div>
      </header>

      <main className="dashboard">
        <section className="welcome-panel">
          <p className="eyebrow">Authenticated workspace</p>
          <h1>Welcome, {user?.email}</h1>
          <p>
            Your protected application shell is ready. Asset, beneficiary, document, and discovery screens will be added in later milestones.
          </p>
          {logoutError && <div className="error-message" role="alert">{logoutError}</div>}
        </section>

        <section className="dashboard-grid" aria-label="LegacyGuard modules">
          {[
            ['Assets', 'Inventory and verify assets you already know about.'],
            ['Beneficiaries', 'Record intended beneficiaries and allocation details.'],
            ['Document vault', 'Store and analyze supporting records securely.'],
            ['Discovery', 'Review potential asset clues without claiming ownership.'],
          ].map(([title, description]) => (
            <article className="module-card" key={title}>
              <h2>{title}</h2>
              <p>{description}</p>
              <span className="coming-soon">Coming in a later milestone</span>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}
