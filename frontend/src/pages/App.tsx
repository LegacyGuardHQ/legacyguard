import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import AppShell from '../components/AppShell';
import ProtectedRoute from '../components/ProtectedRoute';
import { useAuth } from '../context/AuthContext';
import DiscoveryOverviewPage from './DiscoveryOverviewPage';
import FindingDetailPage from './FindingDetailPage';
import LoginPage from './LoginPage';
import ReviewQueuePage from './ReviewQueuePage';
import ScanDetailPage from './ScanDetailPage';
import ScanHistoryPage from './ScanHistoryPage';

function HomeRedirect() {
  const { isAuthenticated, isInitializing } = useAuth();

  if (isInitializing) {
    return (
      <main className="centered-page">
        <div className="loading-card" role="status">Restoring your secure session…</div>
      </main>
    );
  }

  return <Navigate to={isAuthenticated ? '/discovery' : '/login'} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/discovery" element={<DiscoveryOverviewPage />} />
          <Route path="/discovery/scans" element={<ScanHistoryPage />} />
          <Route path="/discovery/scans/:scanId" element={<ScanDetailPage />} />
          <Route path="/discovery/review" element={<ReviewQueuePage />} />
          <Route path="/discovery/findings/:findingId" element={<FindingDetailPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
