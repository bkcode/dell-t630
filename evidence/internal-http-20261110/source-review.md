# FileBrowser HTTP source review

Review date: 2026-11-10, Asia/Shanghai. Scope: read-only local review of the fixed VM280 HTTPS-to-HTTP migration and renderer/install source. No remote operation, credential/key read, Git operation, socket test, or shared-resource mutation was performed by this reviewer.

## Decision before execution

**PASS for the fixed migration source reviewed below.** Both reported blocking issues are corrected: anonymous 401 and operator settings 403 acceptance run inside the transaction try/rollback block, while pre-write CAS checks run immediately before that try block and refuse drift without stopping or overwriting the existing service. Reviewed NEW SHA256 values are pinned. HTTP health metrics are read back, and rollback checks restored HTTPS health and both original account metadata.

Frozen migration source: `infra/resources/filebrowser/switch-http.py`, SHA256 `282acdf8f7a87a4e09716fca538bd996875b566e6f90d443261c6a8c775ee28a`. Final AST/source check confirms CAS-before-transaction and auth-acceptance-inside-rollback-scope. No remaining execution blocker was found within this review scope.

Both findings and their corrections were reviewed before any migration execution. This is source approval, not a claim that live migration or recovery has already passed.

## Confirmed source properties

- Renderer removes FileBrowser HTTP `tlsCert`/`tlsKey`; authentication remains password-enabled with `noauth: false`. The fixed JWT credential, marker-based bootstrap behavior, state/database/cache paths, UID2000/GID2980, UMask0002, named UID2000 credential ACL validation, resource mount dependencies, and firewall remain present.
- Application unit no longer loads the TLS private key. The launcher permits only JWT/bootstrap-password credentials and retains the initialized-marker branch that avoids injecting the bootstrap password.
- Migration preflights the fixed root/hostname, resource UUID, initial marker, three known OLD public hashes plus prepared manifest, and old HTTPS health configuration. It authenticates both existing accounts before stopping the application and compares username/login method/permissions/scopes after fresh login with the same stored passwords.
- Backup is guest-local under the manager directory, requested mode700; files are mode600. Public runtime, prepared manifest, health configuration, and login-URL metadata have old-byte rollback paths. Database, JWT, marker, old TLS files, NFS exports and firewall are not written by the script.
- Only the application is explicitly stopped/restarted; six protected service identity frames are compared. The migration updates the existing health check and restarts the health collector.

## Verification

`python3 -B -m unittest discover -s infra/resources/filebrowser -p 'test_*.py'`: **40 tests PASS**, offline, no socket operation. The migration script also compiles successfully. These tests cover renderer/install behavior; they are not a migration failure-injection suite or live acceptance.

Independently rendered NEW public SHA256:

| File | SHA256 |
| --- | --- |
| config.yaml | 7fe50a00dd568632abdc29286812af49322a25958b67c38f4cff625c5a52f5db |
| dell-filebrowser.service | 94aec8ba0232171b65b1671b12c4dfa8cc4891c3926a1745cd19d4eb25974ca7 |
| launch.py | e1c3732ca61545747e70a1b23459902796646f872d4147fe2680813834297d4c |

## Execution evidence boundary

The source now locks the three independently rendered NEW hashes and compares all three OLD public file bytes plus prepared/health/login bytes immediately before the transaction. Collector success includes a readback of the HTTP health metric. Any failed live execution must retain the actual error/recovery outcome; source review does not replace the migration receipt, service metrics or final live postcheck. State database, secrets and shared resource data are deliberately excluded from rollback writes.
