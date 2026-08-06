# LegacyGuard Development Roadmap

## Current state (2026-08-06)
- Repository is stable on master at `d815bdc318e6cc0ccc4154626ef1df9e44ba1fce`.
- Phase 5.1 and Phase 5.2 are complete and merged.
- The next milestone should focus on discovery reliability observability and operational clarity rather than introducing new product features.

## Phase 1: Project Foundation
- Create repository structure and documentation
- Define product requirements and architecture
- Set up development environment and tooling
- Establish coding standards and contribution workflow

## Phase 2: Authentication/Security
- Implement user registration and login
- Add password recovery and session control
- Introduce MFA and security best practices
- Build access control and audit logging foundation

## Phase 3: Asset Inventory
- Create asset entry and editing workflows
- Support categories such as financial, physical, digital, and personal
- Add valuation and location tracking
- Implement asset search and organization views

## Phase 4: Beneficiary Tracking
- Add beneficiary profiles and relationship management
- Support distribution instructions and notes
- Create review workflows for beneficiary updates
- Prepare for future inheritance logic or reporting

## Phase 5: Document Management
- Support document uploads and metadata entry
- Organize documents by category and type
- Add encryption-aware storage handling
- Enable document search and retrieval workflows

## Phase 6: AI Assistant
- Add AI-supported summaries and guidance
- Implement document classification and planning assistance
- Provide reviewable AI-generated suggestions
- Keep AI features optional and user-controlled

## Phase 7: Reports/Scoring
- Generate continuity summaries and readiness reports
- Add scoring logic for completeness and preparedness
- Surface gaps and missing information to users
- Produce exportable planning reports

## Phase 5.3: Discovery Lifecycle Telemetry and Safe Status Visibility
- Add privacy-safe lifecycle visibility for discovery scans and documents
- Surface recovery and failure states without exposing sensitive evidence
- Improve operator understanding of pending, running, recovered, and completed scans

## Phase 5.4: Background Job Monitoring and Failure Surfacing
- Improve visibility into background discovery execution and upload-driven scans
- Surface queue, retry, and failure states in a consistent way
- Reduce silent failures during background processing

## Phase 5.5: API Contract Hardening
- Standardize discovery and document API validation, pagination, and error behavior
- Reduce contract drift between backend and frontend consumers
- Keep responses privacy-safe and deterministic

## Phase 5.6: Extraction Reliability
- Improve behavior for unsupported and low-quality document formats
- Make extraction outcomes more predictable and easier to reason about
- Preserve clear warning semantics for skipped or failed documents

## Phase 5.7: Authentication and Session Resilience
- Harden token and session validation edge cases
- Improve handling of expired, revoked, and invalid sessions
- Preserve privacy-safe error responses

## Phase 5.8: Regression Coverage Expansion
- Add regression tests for recovery, background-job, ownership, and upload edge cases
- Keep the suite focused and maintainable
- Reduce risk when evolving the discovery pipeline

## Phase 5.9: Discovery UX Improvements
- Improve loading, empty, and error states in discovery views
- Make scan lifecycle states easier to understand for end users
- Preserve the current privacy-safe contract

## Phase 6.0: Documentation and Architecture Refresh
- Refresh project-state and architecture documents to match the current codebase
- Clarify the operational model for discovery and document workflows
- Preserve the existing privacy-first engineering principles

## Phase 8: Testing/Security Audit
- Add automated tests for core workflows
- Perform penetration and security review
- Validate backup, recovery, and data retention procedures
- Prepare for production deployment and compliance review
