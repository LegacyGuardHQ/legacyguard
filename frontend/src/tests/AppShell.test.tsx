import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import AppShell from '../components/AppShell';

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ logout: vi.fn() }),
}));

vi.mock('../components/HealthStatus', () => ({
  default: () => <span>Service available</span>,
}));

describe('AppShell navigation', () => {
  it('provides consistent workspace navigation and identifies the active page', () => {
    render(
      <MemoryRouter initialEntries={['/assets']}>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route path="assets" element={<h1>Assets</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole('navigation', { name: 'Workspace navigation' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/workspace');
    expect(screen.getByRole('link', { name: 'Beneficiaries' })).toHaveAttribute('href', '/beneficiaries');
    expect(screen.getByRole('link', { name: 'Document Vault' })).toHaveAttribute('href', '/documents');
    expect(screen.getByRole('link', { name: 'Discovery' })).toHaveAttribute('href', '/discovery');
    expect(screen.getByRole('link', { name: 'Scans' })).toHaveAttribute('href', '/discovery/scans');
    expect(screen.getByRole('link', { name: 'Review queue' })).toHaveAttribute('href', '/discovery/review');
    expect(screen.getByRole('link', { name: 'Assets' })).toHaveAttribute('aria-current', 'page');
  });
});
