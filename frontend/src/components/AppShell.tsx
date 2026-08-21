import React, { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { ApiError } from '../api/client';
import { useAuth } from '../context/AuthContext';
import HealthStatus from './HealthStatus';

const navigation = [
  ['/workspace', 'Home'],
  ['/assets', 'Assets'],
  ['/beneficiaries', 'Beneficiaries'],
  ['/documents', 'Document Vault'],
  ['/discovery', 'Discovery'],
  ['/discovery/scans', 'Scans'],
  ['/discovery/review', 'Review queue'],
] as const;

export default function AppShell() {
  const { logout } = useAuth();
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

      <nav className="app-nav" aria-label="Workspace navigation">
        {navigation.map(([to, label]) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/workspace' || to === '/discovery'}
            className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`}
          >
            {label}
          </NavLink>
        ))}
      </nav>

      {logoutError && <div className="shell-error error-message" role="alert">{logoutError}</div>}
      <main className="dashboard">
        <Outlet />
      </main>
    </div>
  );
}
