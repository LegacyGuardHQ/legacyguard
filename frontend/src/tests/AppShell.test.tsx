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
  it('provides a keyboard-accessible beneficiary navigation link', () => {
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
    expect(screen.getByRole('link', { name: 'Beneficiaries' })).toHaveAttribute('href', '/beneficiaries');
    expect(screen.getByRole('link', { name: 'Document Vault' })).toHaveAttribute('href', '/documents');
  });
});
