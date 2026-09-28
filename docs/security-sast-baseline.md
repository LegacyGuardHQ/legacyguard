# LegacyGuard SAST Review Baseline

This document records manually reviewed findings from the initial independent
Semgrep and Bandit security baseline.

A listed item is not a blanket suppression of the underlying rule. New
occurrences must be reviewed independently.

## Reviewed findings

### Alembic dialect-specific numeric predicate

File:

`backend/alembic/versions/20260711_asset_beneficiary_link_model_preparation.py`

Bandit may report B608 because the migration constructs an SQL statement with
an interpolated predicate.

The interpolated value is selected exclusively from two fixed SQL literals
according to the SQLAlchemy database dialect (`sqlite` versus the alternative
dialect). It does not originate from user-controlled input.

Classification: reviewed false positive.

### Encrypted-field migration SELECT

File:

`backend/alembic/versions/20260826_encrypt_legacy_sensitive_fields.py`

Semgrep and Bandit may flag construction of the migration SELECT statement.

The dynamic column fragments are selected from fixed schema-dependent choices
based on column presence and are not derived from user-controlled input.

Classification: reviewed false positive.

## Bandit B101 assertions

Production schema modules contain assertions used to keep controlled Literal
values and model/schema contracts synchronized.

These assertions are developer invariants rather than authentication,
authorization, encryption, or untrusted-input security boundaries.

Because Python can remove assertions when optimization is enabled, these are
tracked as a hardening opportunity. They should eventually be moved into tests
or replaced with explicit runtime checks where runtime enforcement is actually
required.

Classification: hardening opportunity.

## Intentional constant strings

Initial Bandit review also identified fixed strings used for:

- the dummy bcrypt hash used to avoid an unknown-user login timing shortcut
- the OAuth/JWT token type `bearer`
- the JWT application token type `access`
- the privacy replacement value `[REDACTED]`

These values are intentional constants rather than deployable credentials.

Classification: reviewed false positives.

## Scope

This baseline records the disposition of specific findings reviewed during the
initial independent SAST evaluation. It is not a security certification and
does not establish that LegacyGuard is production-ready or free of
vulnerabilities.

## Local gate behavior

The local gate runs pinned Semgrep Community Edition, Bandit, and
`detect-secrets` versions in a disposable environment under the operating
system temporary directory. Scanner reports are also written there and are not
part of the repository.

The gate parses scanner JSON itself. Only the exact reviewed file, rule, and
line locations above are accepted; a new occurrence of a reviewed rule outside
those locations remains a gate failure. Exactly 19 listed `B101` locations are
currently recognized, preserving detection for other assertions elsewhere.

Secret scanning is local and offline with `detect-secrets`; it has no cloud
upload or SaaS dependency. `docs/security-secrets-baseline.json` is the
machine-generated candidate inventory by filename, detector, fingerprint, and
line. It does not authorize findings. `docs/security-secrets-reviewed.json`
contains the separate explicit human-reviewed non-secret dispositions used by
the gate for exact authorization.

Presence in the machine baseline does not by itself mean that a finding has
been manually reviewed or approved. New findings, changed lines, or changed
fingerprints must be reviewed rather than automatically added to either file.
