import { Link } from 'react-router-dom';
import MetricCard from '../components/MetricCard';
import { SectionLoadingState } from '../components/DashboardStates';
import { useDiscoveryDashboard } from '../hooks/useDiscoveryDashboard';
import { usePageTitle } from '../hooks/usePageTitle';

const workspaceAreas = [
  {
    to: '/documents',
    title: 'Document Vault',
    description: 'Upload and organize supported records in your private workspace.',
    action: 'Open Document Vault',
  },
  {
    to: '/discovery',
    title: 'Discovery',
    description: 'Review privacy-safe signals found during document processing.',
    action: 'View discovery activity',
  },
  {
    to: '/assets',
    title: 'Assets',
    description: 'Keep a structured record of the assets you have confirmed.',
    action: 'Manage assets',
  },
  {
    to: '/beneficiaries',
    title: 'Beneficiaries',
    description: 'Maintain the people and organizations relevant to your continuity plan.',
    action: 'Manage beneficiaries',
  },
] as const;

const workflowSteps = [
  ['Document Vault', 'Add the records you want to organize and review.'],
  ['Discovery', 'Inspect privacy-safe signals produced from supported documents.'],
  ['Review queue', 'Confirm or dismiss each signal before relying on it.'],
  ['Assets', 'Record information you have reviewed and chosen to preserve.'],
  ['Beneficiaries', 'Maintain the people and organizations in your plan.'],
] as const;

export default function WorkspaceDashboardPage() {
  usePageTitle('Workspace home');
  const dashboardQuery = useDiscoveryDashboard();

  return (
    <div className="workspace-home">
      <header className="overview-header">
        <p className="eyebrow">Private continuity workspace</p>
        <h1>Workspace home</h1>
        <p>
          Organize records, review discovery signals, and maintain the information that matters to your plan.
          You remain in control of every confirmation and decision.
        </p>
      </header>

      <section aria-labelledby="workspace-areas-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Your workspace</p>
            <h2 id="workspace-areas-title">Continue where you need to</h2>
          </div>
        </div>
        <div className="workspace-area-grid">
          {workspaceAreas.map((area) => (
            <article className="workspace-area-card" key={area.to}>
              <h3>{area.title}</h3>
              <p>{area.description}</p>
              <Link className="action-link" to={area.to}>{area.action} <span aria-hidden="true">→</span></Link>
            </article>
          ))}
        </div>
      </section>

      <section className="workspace-activity" aria-labelledby="workspace-activity-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Discovery activity</p>
            <h2 id="workspace-activity-title">Items that may need attention</h2>
          </div>
          <Link className="secondary-button action-link" to="/discovery/review">Open review queue</Link>
        </div>
        {dashboardQuery.isPending && <SectionLoadingState label="discovery activity" />}
        {dashboardQuery.isError && (
          <div className="workspace-activity-error" role="alert">
            <p>Discovery activity could not be loaded. Your saved information has not been changed.</p>
            <button
              className="secondary-button"
              type="button"
              disabled={dashboardQuery.isFetching}
              onClick={() => { void dashboardQuery.refetch(); }}
            >
              {dashboardQuery.isFetching ? 'Retrying…' : 'Try again'}
            </button>
          </div>
        )}
        {dashboardQuery.data && (
          <div className="workspace-metric-grid">
            <MetricCard
              label="Needs review"
              value={dashboardQuery.data.pending_reviews}
              description="Signals waiting for your review—not verified assets."
            />
            <MetricCard
              label="Discovery scans"
              value={dashboardQuery.data.total_scans}
              description="Scans recorded for your private workspace."
            />
            <MetricCard
              label="Recent scans"
              value={dashboardQuery.data.recent_scans.length}
              description="Recent activity available from the discovery overview."
            />
          </div>
        )}
      </section>

      <section className="workspace-workflow" aria-labelledby="workspace-workflow-title">
        <p className="eyebrow">How the workspace fits together</p>
        <h2 id="workspace-workflow-title">A review-first continuity workflow</h2>
        <ol className="workspace-workflow-list">
          {workflowSteps.map(([title, description]) => (
            <li key={title}>
              <div>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
