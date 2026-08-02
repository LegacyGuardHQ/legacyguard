import React from 'react';

export type SummaryItem = {
  key: string;
  label: string;
  value: number;
  description?: string;
};

type SummaryListProps = {
  title: string;
  items: SummaryItem[];
};

export default function SummaryList({ title, items }: SummaryListProps) {
  const headingId = `summary-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;

  return (
    <section className="summary-card" aria-labelledby={headingId}>
      <h2 id={headingId}>{title}</h2>
      <dl className="summary-list">
        {items.map((item) => (
          <div className="summary-row" key={item.key}>
            <dt>
              <span>{item.label}</span>
              {item.description && <small>{item.description}</small>}
            </dt>
            <dd>{item.value.toLocaleString()}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
