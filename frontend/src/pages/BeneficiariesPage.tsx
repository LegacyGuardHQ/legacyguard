import React, { useState } from 'react';
import { EmptyState, ErrorState, LoadingState } from '../components/DashboardStates';
import { useBeneficiaries, useCreateBeneficiary } from '../hooks/useBeneficiaries';
import { usePageTitle } from '../hooks/usePageTitle';
import type { BeneficiaryCreate } from '../types/beneficiaries';

const emptyForm: BeneficiaryCreate = {
  name: '',
  relationship_type: '',
};

function displayStatus(value: string): string {
  return value.replace(/_/g, ' ').toLowerCase().replace(/^./, (character) => character.toUpperCase());
}

function displayReviewDate(value: string | null): string {
  if (!value) return 'Not scheduled';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(value));
}

export default function BeneficiariesPage() {
  usePageTitle('Beneficiaries');
  const beneficiaries = useBeneficiaries();
  const create = useCreateBeneficiary();
  const [form, setForm] = useState<BeneficiaryCreate>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  function setFormVisible(visible: boolean) {
    setShowForm(visible);
    setFormError(null);
    if (visible) setSuccessMessage(null);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setSuccessMessage(null);

    const name = form.name.trim();
    if (!name) {
      setFormError('Beneficiary name is required.');
      return;
    }

    const relationship = form.relationship_type?.trim();
    const payload: BeneficiaryCreate = {
      name,
      ...(relationship ? { relationship_type: relationship } : {}),
    };

    try {
      await create.mutateAsync(payload);
      setForm(emptyForm);
      setShowForm(false);
      setSuccessMessage(`${name} was added as a beneficiary.`);
    } catch {
      setFormError('Unable to add this beneficiary. Your information has not been changed.');
    }
  }

  if (beneficiaries.isLoading) {
    return <LoadingState message="Loading your beneficiaries" description="We’re retrieving your private beneficiary summaries." />;
  }

  if (beneficiaries.isError) {
    return (
      <ErrorState
        title="We couldn’t load your beneficiaries."
        message="Check your connection and try again. Your saved information has not been changed."
        onRetry={() => void beneficiaries.refetch()}
        isRetrying={beneficiaries.isFetching}
      />
    );
  }

  return (
    <section className="page-panel beneficiaries-page" aria-labelledby="beneficiaries-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Continuity planning</p>
          <h1 id="beneficiaries-title">Beneficiaries</h1>
          <p>Keep a clear record of the people and organizations named in your continuity plans.</p>
        </div>
        <button className="primary-button" type="button" onClick={() => setFormVisible(!showForm)}>
          {showForm ? 'Cancel' : 'Add beneficiary'}
        </button>
      </div>

      {successMessage && <div className="beneficiary-success" role="status" aria-live="polite">{successMessage}</div>}

      {showForm && (
        <form className="beneficiary-form" onSubmit={handleSubmit} noValidate>
          <h2>Add a beneficiary</h2>
          <p className="muted-text">Add only the minimum information needed to identify this beneficiary.</p>
          <div className="beneficiary-form-grid">
            <label>
              Beneficiary name <span aria-hidden="true">(required)</span>
              <input value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} required aria-required="true" />
            </label>
            <label>
              Relationship <span>(optional)</span>
              <input value={form.relationship_type} onChange={(event) => setForm((current) => ({ ...current, relationship_type: event.target.value }))} />
            </label>
          </div>
          {formError && <div className="error-message" role="alert">{formError}</div>}
          <button className="primary-button" type="submit" disabled={create.isPending}>
            {create.isPending ? 'Adding beneficiary…' : 'Save beneficiary'}
          </button>
        </form>
      )}

      {beneficiaries.data?.length === 0 ? (
        <EmptyState
          title="No beneficiaries recorded yet"
          description="Add your first beneficiary to begin a private continuity record. Asset allocations and document links remain separate."
          action={{ label: 'Add your first beneficiary', onClick: () => setFormVisible(true) }}
        />
      ) : (
        <ul className="beneficiary-list" aria-label="Current beneficiaries">
          {beneficiaries.data?.map((beneficiary) => (
            <li className="beneficiary-card" key={beneficiary.id}>
              <div className="beneficiary-card-heading">
                <div>
                  <span className="category-badge">{beneficiary.relationship_type || 'Relationship not provided'}</span>
                  <h2>{beneficiary.name}</h2>
                </div>
                <span className={`beneficiary-verification verification-${beneficiary.verification_status.toLowerCase()}`}>
                  {displayStatus(beneficiary.verification_status)}
                </span>
              </div>
              <dl className="beneficiary-summary">
                <div><dt>Status</dt><dd>{beneficiary.status}</dd></div>
                <div><dt>Review due</dt><dd>{displayReviewDate(beneficiary.review_due_at)}</dd></div>
              </dl>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
