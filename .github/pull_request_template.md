## Summary

<!-- What changed, and what user or engineering outcome does it deliver? -->

## Scope

<!-- Name the milestone, issue, or narrowly defined problem addressed by this PR. -->

## Files changed

<!-- Group the important files by backend, frontend, tests, docs, migrations, or CI and explain why each group changed. -->

## API, schema, and migration impact

- API contract changed: No
- Request/response schema changed: No
- Database model or migration changed: No

<!-- If any answer is Yes, describe the exact fields, routes, statuses, ordering, compatibility impact, migration, and rollback considerations. Do not write "No" unless verified. -->

## Privacy and authorization impact

<!-- Describe owner-scoping, authentication, sensitive-data handling, audit behavior, and privacy-safe response/rendering implications. State "No impact" only after checking. -->

## Validation results

| Validation | Result | Details |
| --- | --- | --- |
| Backend tests (`python -m pytest`) | Not run | |
| Frontend tests (`npm test`) | Not run | |
| Frontend production build (`npm run build`) | Not run | |
| Whitespace check (`git diff --check`) | Not run | |
| Manual verification | Not run | |

<!-- Replace every "Not run" with Pass, Fail, or Not applicable and include commands, counts, environments, and reasons where useful. -->

## Screenshots or recordings

<!-- Required for visible UI changes. Include relevant desktop/mobile and loading, populated, empty, or error states. Otherwise write "Not applicable — no visible UI change." -->

## Known risks

<!-- Include security, privacy, authorization, data, compatibility, performance, accessibility, and operational risks plus mitigations. Write "None identified" only after review. -->

## Out of scope

<!-- List intentionally excluded work and follow-ups so the milestone boundary is explicit. -->

## Pre-merge checklist

- [ ] The PR addresses one milestone or focused change only.
- [ ] I reviewed the full diff and removed unrelated changes, debug output, and temporary files.
- [ ] I verified owner scoping, authentication, authorization, and enumeration-safe behavior where applicable.
- [ ] I verified that responses, UI, logs, errors, URLs, and tests do not expose sensitive data or raw discovery evidence.
- [ ] Findings remain human-reviewed; this change does not create assets automatically or overstate confidence as proof.
- [ ] API/schema behavior is unchanged, or every approved contract change is documented and tested.
- [ ] Database changes include a reviewed Alembic migration and rollback considerations, or no database change is present.
- [ ] No dependency or lockfile change is present unless explicitly approved and explained above.
- [ ] Backend tests pass, or their omission/failure is documented above.
- [ ] Frontend tests pass, or their omission/failure is documented above.
- [ ] The frontend production build passes, or it is not applicable and documented above.
- [ ] `git diff --check` passes.
- [ ] New or changed behavior has focused tests for relevant success, loading, empty, error, auth, privacy, and interaction states.
- [ ] Visible UI changes include relevant screenshots or recordings and were checked for accessibility and responsive behavior.
- [ ] Documentation and roadmap/project-state references are accurate for this milestone, or no update is required.
- [ ] Known risks, assumptions, and out-of-scope items are stated explicitly.
