import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import AssetsPage from '../pages/AssetsPage';
import type { Asset } from '../types/assets';

const { fetchAssetsMock, createAssetMock } = vi.hoisted(() => ({
  fetchAssetsMock: vi.fn(),
  createAssetMock: vi.fn(),
}));

vi.mock('../api/assets', () => ({
  fetchAssets: fetchAssetsMock,
  createAsset: createAssetMock,
}));

const asset: Asset = {
  id: 'asset-1',
  asset_category: 'Bank account',
  asset_name: 'Household checking',
  institution: 'Example Bank',
  description: 'Primary household account',
  estimated_value: '2500.00',
  ownership_type: 'Joint',
  status: 'Active',
  is_verified: false,
  verification_status: 'NEEDS_REVIEW',
  verified_at: null,
  archived_at: null,
  created_at: '2026-08-20T12:00:00Z',
  updated_at: '2026-08-20T12:00:00Z',
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter><AssetsPage /></MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AssetsPage', () => {
  beforeEach(() => {
    fetchAssetsMock.mockReset();
    createAssetMock.mockReset();
  });

  it('renders privacy-safe active asset summaries', async () => {
    fetchAssetsMock.mockResolvedValue([asset]);
    renderPage();

    expect(await screen.findByRole('heading', { name: 'Household checking' })).toBeInTheDocument();
    expect(screen.getByText('Example Bank')).toBeInTheDocument();
    expect(screen.getByText('Joint')).toBeInTheDocument();
    expect(screen.getByText('$2,500.00')).toBeInTheDocument();
    expect(screen.getByText('NEEDS REVIEW')).toBeInTheDocument();
  });

  it('offers a useful empty state that opens the create form', async () => {
    const user = userEvent.setup();
    fetchAssetsMock.mockResolvedValue([]);
    renderPage();

    expect(await screen.findByRole('heading', { name: 'No assets recorded yet' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Add your first asset' }));
    expect(screen.getByRole('heading', { name: 'Add an asset' })).toBeInTheDocument();
  });

  it('validates required fields without making a request', async () => {
    const user = userEvent.setup();
    fetchAssetsMock.mockResolvedValue([]);
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Add asset' }));
    await user.click(screen.getByRole('button', { name: 'Save asset' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Asset name and category are required.');
    expect(createAssetMock).not.toHaveBeenCalled();
  });

  it('creates an asset and refreshes the list', async () => {
    const user = userEvent.setup();
    fetchAssetsMock.mockResolvedValueOnce([]).mockResolvedValueOnce([asset]);
    createAssetMock.mockResolvedValue(asset);
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Add asset' }));
    await user.type(screen.getByLabelText('Asset name'), 'Household checking');
    await user.type(screen.getByLabelText('Category'), 'Bank account');
    await user.type(screen.getByLabelText(/Institution/), 'Example Bank');
    await user.click(screen.getByRole('button', { name: 'Save asset' }));

    await waitFor(() => expect(createAssetMock).toHaveBeenCalled());
    expect(createAssetMock.mock.calls[0][0]).toEqual({
      asset_name: 'Household checking',
      asset_category: 'Bank account',
      institution: 'Example Bank',
    });
    expect(await screen.findByRole('heading', { name: 'Household checking' })).toBeInTheDocument();
  });

  it('sanitizes create failures instead of exposing backend details', async () => {
    const user = userEvent.setup();
    fetchAssetsMock.mockResolvedValue([]);
    createAssetMock.mockRejectedValue(new ApiError('C:\\private\\asset-secret.txt', 500));
    renderPage();

    await user.click(await screen.findByRole('button', { name: 'Add asset' }));
    await user.type(screen.getByLabelText('Asset name'), 'Household checking');
    await user.type(screen.getByLabelText('Category'), 'Bank account');
    await user.click(screen.getByRole('button', { name: 'Save asset' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to add this asset. Your information has not been changed.');
    expect(screen.queryByText(/asset-secret/i)).not.toBeInTheDocument();
  });

  it('shows a privacy-safe load failure and retries', async () => {
    const user = userEvent.setup();
    fetchAssetsMock.mockRejectedValueOnce(new ApiError('C:\\private\\list-secret.txt', 500)).mockResolvedValueOnce([asset]);
    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('We couldn’t load your assets.');
    expect(screen.queryByText(/list-secret/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('heading', { name: 'Household checking' })).toBeInTheDocument();
  });
});
