import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { AuthProvider } from '../context/AuthContext';
import App from '../pages/App';

function renderApp(path: string) {
  const testQueryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={testQueryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('routing foundation', () => {
  it('renders the existing authentication experience at /login', async () => {
    renderApp('/login');

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('protects discovery routes with the existing authentication gate', async () => {
    renderApp('/discovery');

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
  });

  it('protects the workspace home with the existing authentication gate', async () => {
    renderApp('/workspace');

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
  });

  it('protects the asset-management route with the existing authentication gate', async () => {
    renderApp('/assets');

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
  });

  it('protects the beneficiary-management route with the existing authentication gate', async () => {
    renderApp('/beneficiaries');

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
  });

  it('protects the document-vault route with the existing authentication gate', async () => {
    renderApp('/documents');

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
  });

  it('shows the generic registration result without automatically attempting login', async () => {
    const user = userEvent.setup();
    const message = 'If registration is available for this address, you can sign in with the submitted credentials.';
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ message }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    renderApp('/login');

    await user.click(await screen.findByRole('button', { name: 'Need an account? Register' }));
    await user.type(screen.getByLabelText('Email'), 'new@example.com');
    await user.type(screen.getByLabelText('Password'), 'StrongPass123!');
    await user.type(screen.getByLabelText('Confirm password'), 'StrongPass123!');
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByRole('status')).toHaveTextContent(message);
    expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain('/auth/register');
    expect(fetchMock.mock.calls.some(([request]) => String(request).includes('/auth/login'))).toBe(false);

    fetchMock.mockRestore();
  });
});
