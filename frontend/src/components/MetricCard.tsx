import React from 'react';

type MetricCardProps = {
  label: string;
  value: number;
  description: string;
};

export default function MetricCard({ label, value, description }: MetricCardProps) {
  return (
    <article className="metric-card" aria-label={label}>
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value.toLocaleString()}</p>
      <p className="metric-description">{description}</p>
    </article>
  );
}
