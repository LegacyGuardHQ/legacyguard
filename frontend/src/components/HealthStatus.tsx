import React, { useEffect, useState } from 'react';
import { fetchHealth } from '../api/health';

type Status = 'checking' | 'online' | 'offline';

export default function HealthStatus() {
  const [status, setStatus] = useState<Status>('checking');

  useEffect(() => {
    let active = true;
    fetchHealth()
      .then(() => active && setStatus('online'))
      .catch(() => active && setStatus('offline'));
    return () => {
      active = false;
    };
  }, []);

  const label = status === 'checking' ? 'Checking backend' : status === 'online' ? 'Backend connected' : 'Backend unavailable';

  return (
    <div className={`health-status health-${status}`} role="status">
      <span className="status-dot" aria-hidden="true" />
      {label}
    </div>
  );
}
