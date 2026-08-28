# History Privacy Rewrite Plan

This plan records the public-launch history work identified against the
canonical repository on 2026-08-27. It is preparation only. Do not run the
rewrite, delete old clones, or force-push any ref without explicit owner
approval and a coordinated maintenance window.

## Exposure inventory

Commit `0614df18bf9ce7755466c7e3830e9fbd4fef37c0` contains a user-machine
Windows/OneDrive path in `docs/PROJECT_STATE.md`. Its child removed the path
from the current tree, but the original blob remains reachable from:

- branches: `master`, `security/remediate-sealed-findings`,
  `public-launch/blocker-remediation`
- tags: `v1.0.0`, `v1.0.0-rc1`, `v1.0.1`, `v1.1.0-rc.1`

The reachable history also contains three non-noreply email identities. Full
addresses are intentionally omitted here.

| Identity | Roles and commit counts | Affected refs | Account evidence | Owner decision |
| --- | --- | --- | --- | --- |
| A (`outlook.com`) | 83 author, 83 committer | All three branches and all seven tags | Representative GitHub commits had no linked account; commit verification was absent | Confirm replacement with an approved noreply identity |
| B (`gmail.com`) | 26 author, 21 committer | All three branches and `v1.1.0-rc.1` | Representative commits linked to `jh505tt-create`; commit verification was absent | Confirm whether the address itself may remain public |
| C (`fielding.edu`) | 38 author, 7 committer | All three branches and every tag except `discovery-v1-phase1` | Representative author commits linked to `jh505tt-create`; GitHub web-flow committer records were verified | Confirm whether the address itself may remain public |

The seven inventoried tags are `discovery-v1-phase1`, `v0.3.0`,
`v0.4.0-document-discovery`, `v1.0.0`, `v1.0.0-rc1`, `v1.0.1`, and
`v1.1.0-rc.1`. Association with an account is not evidence of consent to
publish an email address. A `.mailmap` could improve displayed attribution but
would not remove raw addresses or the path from existing commits.

Refresh this inventory immediately before the rewrite. If the remediation PR
has been merged and its source branch deleted, the deleted branch does not need
to be recreated or force-pushed.

## Owner approvals required

Before rewriting, the owner must:

1. approve the neutral replacement for the historical machine path
2. approve retain-or-replace treatment for identities A, B, and C
3. provide the exact approved noreply identity for every replacement
4. confirm whether annotated tags must be re-created and signed
5. approve the maintenance window and force-push of every affected branch and tag
6. notify anyone with an existing clone that old history must not be pushed back

## Isolated rewrite procedure

1. Freeze merges and tag creation. Refresh the branch/tag inventory from the
   remote and record each ref and object ID. Export repository settings and
   create a read-only mirror backup or bundle with checksums.
2. Create a new temporary directory and a fresh `git clone --mirror`. Never run
   the rewrite in a working repository or an existing contributor clone.
3. Install a pinned, reviewed `git-filter-repo` release in an isolated tool
   environment. Record its version and package checksum.
4. Outside the repository, create a private exact-literal replacement file for
   the machine path and an owner-approved mailmap for only the email identities
   that must change. Do not place either file in Git or command output.
5. In a single `git filter-repo --force` invocation, apply `--replace-text` and
   `--mailmap` to all inventoried `refs/heads/*` and `refs/tags/*`. Keeping the
   operations in one pass ensures path and identity changes produce one
   consistent object graph. Commit IDs necessarily change; commit messages,
   timestamps, ordinary file content, ref names, and topology should otherwise
   remain stable. Commit and signed-tag signatures cannot survive rewritten
   object IDs, so required tags must be re-created and re-signed afterward.
6. Compare pre/post ref inventories and trees. Confirm that only the approved
   literal path and identity metadata changed. Run `git fsck --full`, repository
   tests, privacy/secret scans over every rewritten ref, and explicit negative
   searches for the original path and each replaced address without printing
   those values.
7. Make a separate anonymous local clone from the rewritten mirror. Check out
   every branch and tag, run the normal validation suites, and confirm that the
   intended release and documentation content is reachable.
8. During the approved maintenance window, preserve branch protections and
   repository settings, force-push only the rewritten branches and tags, then
   re-enable protections. Verify an anonymous clone from GitHub and request
   cache cleanup/support assistance if removed objects remain publicly served.
9. Archive old clones as read-only evidence or replace them with fresh clones.
   Contributors must rebase or cherry-pick work onto new commit IDs and must
   never merge or push a pre-rewrite branch back into the canonical repository.

## Completion evidence

History cleanup is complete only when the owner decisions are recorded, the
rewritten mirror passes object/privacy/test validation, every affected remote
ref points to the approved rewritten graph, and a fresh anonymous clone cannot
reach the removed path or replaced addresses.
