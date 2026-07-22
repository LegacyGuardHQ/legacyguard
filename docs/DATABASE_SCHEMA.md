# LegacyGuard Database Schema Plan

## Overview
This document outlines the proposed relational schema for LegacyGuard. The database is designed to support secure, user-owned legacy planning records with auditability and future expansion.

## Proposed Tables

### 1. users
Purpose: Represents the primary account owner.

Fields:
- id: UUID, primary key
- email: VARCHAR(255), unique, not null
- password_hash: VARCHAR(255), nullable for OAuth-based accounts
- full_name: VARCHAR(255), not null
- phone: VARCHAR(50), nullable
- status: VARCHAR(50), default 'active'
- created_at: TIMESTAMP, not null
- updated_at: TIMESTAMP, not null
- deleted_at: TIMESTAMP, nullable

Relationships:
- One user has many assets, beneficiaries, documents, tasks, reports, and audit logs

Security considerations:
- Store only password hashes, never plaintext
- Enforce encryption for sensitive personal fields
- Restrict access to the owner’s own user record

### 2. assets
Purpose: Stores financial, physical, digital, and personal assets.

Fields:
- id: UUID, primary key
- user_id: UUID, foreign key to users.id
- name: VARCHAR(255), not null
- type: VARCHAR(100), not null
- description: TEXT, nullable
- value_estimate: DECIMAL(12,2), nullable
- location: TEXT, nullable
- account_details: TEXT, nullable
- access_notes: TEXT, nullable
- status: VARCHAR(50), default 'active'
- created_at: TIMESTAMP, not null
- updated_at: TIMESTAMP, not null
- deleted_at: TIMESTAMP, nullable

Relationships:
- Many assets belong to one user
- Can optionally relate to beneficiaries through a join table in future phases

Security considerations:
- Protect account details and location data as sensitive content
- Restrict access to the owner and authorized trusted contacts

### 3. beneficiaries
Purpose: Stores named beneficiaries and their relationship to the user.

Fields:
- id: UUID, primary key
- user_id: UUID, foreign key to users.id
- full_name: VARCHAR(255), not null
- relationship: VARCHAR(100), nullable
- contact_info: TEXT, nullable
- share_percentage: DECIMAL(5,2), nullable
- notes: TEXT, nullable
- status: VARCHAR(50), default 'active'
- created_at: TIMESTAMP, not null
- updated_at: TIMESTAMP, not null
- deleted_at: TIMESTAMP, nullable

Relationships:
- Many beneficiaries belong to one user

Security considerations:
- Store contact details carefully and apply least-privilege access
- Avoid exposing personal contact data unnecessarily

### 4. documents
Purpose: Stores metadata for important documents and files.

Fields:
- id: UUID, primary key
- user_id: UUID, foreign key to users.id
- title: VARCHAR(255), not null
- category: VARCHAR(100), nullable
- document_type: VARCHAR(100), nullable
- file_path: TEXT, nullable
- checksum: VARCHAR(255), nullable
- storage_uri: TEXT, nullable
- notes: TEXT, nullable
- is_encrypted: BOOLEAN, default true
- status: VARCHAR(50), default 'active'
- created_at: TIMESTAMP, not null
- updated_at: TIMESTAMP, not null
- deleted_at: TIMESTAMP, nullable

Relationships:
- Many documents belong to one user
- May later link to assets or beneficiaries

Security considerations:
- Store encrypted file references and hashes
- Restrict file access based on ownership and authorization

### 5. tasks
Purpose: Tracks follow-up actions, checklist items, and continuity instructions.

Fields:
- id: UUID, primary key
- user_id: UUID, foreign key to users.id
- title: VARCHAR(255), not null
- description: TEXT, nullable
- task_type: VARCHAR(100), nullable
- priority: VARCHAR(50), default 'medium'
- status: VARCHAR(50), default 'pending'
- due_date: TIMESTAMP, nullable
- completed_at: TIMESTAMP, nullable
- created_at: TIMESTAMP, not null
- updated_at: TIMESTAMP, not null
- deleted_at: TIMESTAMP, nullable

Relationships:
- Many tasks belong to one user

Security considerations:
- Protect instructions or sensitive follow-up details
- Audit changes to completion or reassignment status

### 6. reports
Purpose: Stores generated summaries, continuity reports, and scoring outputs.

Fields:
- id: UUID, primary key
- user_id: UUID, foreign key to users.id
- report_type: VARCHAR(100), not null
- title: VARCHAR(255), not null
- summary: TEXT, nullable
- score: DECIMAL(5,2), nullable
- generated_at: TIMESTAMP, not null
- created_at: TIMESTAMP, not null
- updated_at: TIMESTAMP, not null

Relationships:
- Many reports belong to one user

Security considerations:
- Reports may include sensitive summaries and should be access-controlled
- Avoid storing unencrypted full content if not needed

### 7. audit_logs
Purpose: Records security-sensitive or administrative actions.

Fields:
- id: UUID, primary key
- user_id: UUID, foreign key to users.id, nullable
- actor_id: UUID, nullable
- action: VARCHAR(255), not null
- entity_type: VARCHAR(100), nullable
- entity_id: UUID, nullable
- details: TEXT, nullable
- ip_address: VARCHAR(100), nullable
- user_agent: TEXT, nullable
- created_at: TIMESTAMP, not null

Relationships:
- Many audit logs belong to one user or actor

Security considerations:
- Treat this table as append-only and tamper-evident
- Store enough context for incident investigation and compliance

### 8. settings
Purpose: Stores user preferences and security settings.

Fields:
- id: UUID, primary key
- user_id: UUID, foreign key to users.id
- theme: VARCHAR(50), default 'dark'
- notifications_enabled: BOOLEAN, default true
- mfa_enabled: BOOLEAN, default false
- emergency_access_enabled: BOOLEAN, default false
- privacy_level: VARCHAR(50), default 'standard'
- created_at: TIMESTAMP, not null
- updated_at: TIMESTAMP, not null

Relationships:
- One settings row belongs to one user

Security considerations:
- Store security-sensitive preferences carefully
- Ensure settings changes are auditable

## General Design Notes
- Use UUIDs for public-safe identifiers
- Use soft delete for user-owned entities where appropriate
- Enforce row-level security or application-level ownership checks
- Keep audit logs immutable and separate from operational data
