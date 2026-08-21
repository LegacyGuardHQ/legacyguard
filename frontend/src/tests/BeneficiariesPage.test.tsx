import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import BeneficiariesPage from '../pages/BeneficiariesPage';
import type { Beneficiary } from '../types/beneficiaries';

const { fetchBeneficiariesMock, createBeneficiaryMock } = vi.hoisted(() => ({
  fetchBeneficiariesMock: vi.fn(),
  createBeneficiaryMock: vi.fn(),
}));

vi.mock('../api/beneficiaries', () => ({
  fetchBeneficiaries: fetchBeneficiariesMock,
  createBeneficiary: createBeneficiaryMock,
}));

const beneficiary: Beneficiary = {
  id: 'beneficiary-1',
  name: 'Jordan Example',
  relationship_type: 'Sibling',
  status: 'Active',
  verification_status: 'NEEDS_REVIEW',
  verified_at: null,
  review_due_at: '2030-01-15T00:00:00Z',
  is_deceased: false,
  deceased_at: null,
  archived_at: null,
  created_at: '2026-08-20T12:00:00Z',
  updated_at: '2026-08-20T12:00:00Z',
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter><BeneficiariesPage /></MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('BeneficiariesPage', () => {
  beforeEach(() => {
    fetchBeneficiariesMock.mockReset();
    createBeneficiaryMock.mockReset();
  });

  it('announces its loading state', () => {
    fetchBeneficiariesMock.mockReturnValue(new Promise(() => undefined));
    renderPage();

    expect(screen.getByRole('status')).toHaveTextContent('Loading your beneficiaries');
  });

  it('renders privacy-safe beneficiary summaries and verification state', async () => {
    fetchBeneficiariesMock.mockResolvedValue([{ ...beneficiary, contact_information: 'private@example.com', notes: 'Private note' }]);
    renderPage();

    expect(await screen.findByRole('heading', { name: 'Jordan Example' })).toBeInTheDocument();
    expect(screen.getByText('Sibling')).toBeInTheDocument();
    expect(screen.getByText('Needs review')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText(/Jan 15, 2030/)).toBeInTheDocument();
    expect(screen.queryByText('private@example.com')).not.toBeInTheDocument();
    expect(screen.queryByText('Private note')).not.toBeInTheDocument();
  });

  it('offers an empty state that opens the labeled create form', async () => {
    const user = userEvent.setup();
    fetchBeneficiariesMock.mockResolvedValue([]);
    renderPage();

    expect(await screen.findByRole('heading', { name: 'No beneficiaries recorded yet' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Add your first beneficiary' }));
    expect(screen.getByRole('heading', { name: 'Add a beneficiary' })).toBeInTheDocument();
    expect(screen.getByLabelText(/Beneficiary name/)).toBeRequired();
    expect(screen.getByLabelText(/Relationship/)).toBeInTheDocument();
  });

  it('validates the required name without making a request', async () => {
    const user = userEvent.setup();
    fetchBeneficiariesMock.mockResolvedValue([]);
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Add beneficiary' }));
    await user.click(screen.getByRole('button', { name: 'Save beneficiary' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Beneficiary name is required.');
    expect(createBeneficiaryMock).not.toHaveBeenCalled();
  });

  it('creates an owner-compatible payload, refreshes the list, and announces success', async () => {
    const user = userEvent.setup();
    fetchBeneficiariesMock.mockResolvedValueOnce([]).mockResolvedValueOnce([beneficiary]);
    createBeneficiaryMock.mockResolvedValue(beneficiary);
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Add beneficiary' }));
    await user.type(screen.getByLabelText(/Beneficiary name/), '  Jordan Example  ');
    await user.type(screen.getByLabelText(/Relationship/), '  Sibling  ');
    await user.click(screen.getByRole('button', { name: 'Save beneficiary' }));

    await waitFor(() => expect(createBeneficiaryMock).toHaveBeenCalled());
    expect(createBeneficiaryMock.mock.calls[0][0]).toEqual({ name: 'Jordan Example', relationship_type: 'Sibling' });
    expect(createBeneficiaryMock.mock.calls[0][0]).not.toHaveProperty('user_id');
    expect(await screen.findByRole('status')).toHaveTextContent('Jordan Example was added as a beneficiary.');
    expect(await screen.findByRole('heading', { name: 'Jordan Example' })).toBeInTheDocument();
  });

  it('sanitizes create failures instead of exposing backend details', async () => {
    const user = userEvent.setup();
    fetchBeneficiariesMock.mockResolvedValue([]);
    createBeneficiaryMock.mockRejectedValue(new ApiError('C:\\private\\beneficiary-secret.txt', 500));
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Add beneficiary' }));
    await user.type(screen.getByLabelText(/Beneficiary name/), 'Jordan Example');
    await user.click(screen.getByRole('button', { name: 'Save beneficiary' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to add this beneficiary. Your information has not been changed.');
    expect(screen.queryByText(/beneficiary-secret/i)).not.toBeInTheDocument();
  });

  it('shows a privacy-safe load failure and retries', async () => {
    const user = userEvent.setup();
    fetchBeneficiariesMock.mockRejectedValueOnce(new ApiError('C:\\private\\list-secret.txt', 500)).mockResolvedValueOnce([beneficiary]);
    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('We couldn’t load your beneficiaries.');
    expect(screen.queryByText(/list-secret/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('heading', { name: 'Jordan Example' })).toBeInTheDocument();
  });
});
