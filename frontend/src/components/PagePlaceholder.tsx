import React from 'react';

type PagePlaceholderProps = {
  eyebrow: string;
  title: string;
  description: string;
  resourceId?: string;
};

export default function PagePlaceholder({ eyebrow, title, description, resourceId }: PagePlaceholderProps) {
  return (
    <section className="page-panel" aria-labelledby="page-title">
      <p className="eyebrow">{eyebrow}</p>
      <h1 id="page-title">{title}</h1>
      <p>{description}</p>
      {resourceId && <p className="resource-id">Resource ID: {resourceId}</p>}
      <span className="foundation-badge">Routing foundation ready</span>
    </section>
  );
}
