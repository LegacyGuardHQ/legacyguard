import React, { useState } from 'react';
import { EmptyState, ErrorState, LoadingState } from '../components/DashboardStates';
import { useAssets, useCreateAsset } from '../hooks/useAssets';
import { usePageTitle } from '../hooks/usePageTitle';
import type { AssetCreate } from '../types/assets';

const emptyForm: AssetCreate = {
  asset_name: '',
  asset_category: '',
  institution: '',
  description: '',
  estimated_value: '',
  ownership_type: '',
};

function displayValue(value: string | null): string {
  if (!value) return 'Not provided';
  const amount = Number(value);
  return Number.isFinite(amount)
    ? new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(amount)
    : 'Not provided';
}

export default function AssetsPage() {
  usePageTitle('Assets');
  const assets = useAssets();
  const create = useCreateAsset();
  const [form, setForm] = useState<AssetCreate>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  function updateField(field: keyof AssetCreate, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    if (!form.asset_name.trim() || !form.asset_category.trim()) {
      setFormError('Asset name and category are required.');
      return;
    }
    if (form.estimated_value && Number(form.estimated_value) < 0) {
      setFormError('Estimated value cannot be negative.');
      return;
    }

    const payload = Object.fromEntries(
      Object.entries(form).filter(([, value]) => value.trim() !== ''),
    ) as unknown as AssetCreate;

    try {
      await create.mutateAsync(payload);
      setForm(emptyForm);
      setShowForm(false);
    } catch {
      setFormError('Unable to add this asset. Your information has not been changed.');
    }
  }

  if (assets.isLoading) {
    return <LoadingState message="Loading your assets" description="We’re retrieving your private asset summaries." />;
  }

  if (assets.isError) {
    return (
      <ErrorState
        title="We couldn’t load your assets."
        message="Check your connection and try again. Your saved information has not been changed."
        onRetry={() => void assets.refetch()}
        isRetrying={assets.isFetching}
      />
    );
  }

  return (
    <section className="page-panel assets-page" aria-labelledby="assets-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Continuity inventory</p>
          <h1 id="assets-title">Assets</h1>
          <p>Keep a deliberate record of accounts, policies, property, and other resources your family may need to locate.</p>
        </div>
        <button className="primary-button" type="button" onClick={() => setShowForm((current) => !current)}>
          {showForm ? 'Cancel' : 'Add asset'}
        </button>
      </div>

      {showForm && (
        <form className="asset-form" onSubmit={handleSubmit} noValidate>
          <h2>Add an asset</h2>
          <p className="muted-text">Add only what is useful for continuity. You can leave optional fields blank.</p>
          <div className="asset-form-grid">
            <label>Asset name<input value={form.asset_name} onChange={(event) => updateField('asset_name', event.target.value)} required /></label>
            <label>Category<input value={form.asset_category} onChange={(event) => updateField('asset_category', event.target.value)} required /></label>
            <label>Institution <span>(optional)</span><input value={form.institution} onChange={(event) => updateField('institution', event.target.value)} /></label>
            <label>Ownership type <span>(optional)</span><input value={form.ownership_type} onChange={(event) => updateField('ownership_type', event.target.value)} /></label>
            <label>Estimated value <span>(optional)</span><input type="number" min="0" step="0.01" inputMode="decimal" value={form.estimated_value} onChange={(event) => updateField('estimated_value', event.target.value)} /></label>
            <label className="asset-form-wide">Description <span>(optional)</span><textarea rows={3} value={form.description} onChange={(event) => updateField('description', event.target.value)} /></label>
          </div>
          {formError && <div className="error-message" role="alert">{formError}</div>}
          <button className="primary-button" type="submit" disabled={create.isPending}>{create.isPending ? 'Adding asset…' : 'Save asset'}</button>
        </form>
      )}

      {assets.data?.length === 0 ? (
        <EmptyState title="No assets recorded yet" description="Add your first asset to begin a private continuity inventory. Discovery findings remain separate until you deliberately convert them." action={{ label: 'Add your first asset', onClick: () => setShowForm(true) }} />
      ) : (
        <ul className="asset-list" aria-label="Active assets">
          {assets.data?.map((asset) => (
            <li className="asset-card" key={asset.id}>
              <div className="asset-card-heading">
                <div><span className="category-badge">{asset.asset_category}</span><h2>{asset.asset_name}</h2></div>
                <span className={`asset-verification verification-${asset.verification_status.toLowerCase()}`}>{asset.verification_status.replace('_', ' ')}</span>
              </div>
              <dl className="asset-summary">
                <div><dt>Institution</dt><dd>{asset.institution || 'Not provided'}</dd></div>
                <div><dt>Ownership</dt><dd>{asset.ownership_type || 'Not provided'}</dd></div>
                <div><dt>Estimated value</dt><dd>{displayValue(asset.estimated_value)}</dd></div>
              </dl>
              {asset.description && <p>{asset.description}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
