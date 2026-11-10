# Browser-local login memory review

Reviewed on 2026-11-10 (Asia/Shanghai). Scope: `infra/penpot/browser-remember-login/browser-login.js`, `browser-login.test.mjs`, `selfhost-login.conf`, and `worker.py`. Read `dell/AGENTS.md` first. No SSH, secrets, Git mutation, live deployment, or live browser interaction was performed by this reviewer.

## Code result

PASS: no open P1 or P2 issue found in the reviewed candidate. The candidate contains public helper code, with no embedded account defaults or credentials fetch. New browser storage starts unchecked. The visible warning accurately describes plaintext site-localStorage, same-site script access, personal-device use, and the intended 30-day retention. Saving requires a checked control, a captured form submission with email and password, and a successful exact same-origin POST login response. Forget/uncheck and input changes invalidate pending saves. The fetch wrapper preserves the call arguments, receiver, and response without consuming its body or replaying a request. The helper appends its own subtree and leaves the application's existing form children in place.

The server configuration returns 404 for the former defaults JSON path. The deployment worker uses two read-only frontend mounts, preserves existing image references and the server secret source, checks the current public contract, performs native nginx syntax validation, and provides rollback for failures after the service stop succeeds. The declined shared server-password proposal is not approved by this review; its activation or a replacement shared credentials endpoint remains outside the reviewed candidate.

### TTL finding resolved

The previously reported P2 is closed. `browser-login.js:91–97` now validates the in-memory record at the start of each scan, before any automatic fill. Expiry invalidates pending saves, clears the in-memory record and checked controls, and removes only the helper's own storage key. Existing input values are preserved. The successful save path at lines 152–154 now retains the complete record, including its deadline. The clock-controlled regression at `browser-login.test.mjs:97–115` exercises expiry in an already-installed tab and verifies that a replacement SPA form remains empty and unchecked while unrelated storage survives.

## Verification performed

- `node infra/penpot/browser-remember-login/browser-login.test.mjs`: all assertions passed.
- `node --check infra/penpot/browser-remember-login/browser-login.js`: passed.
- Python AST parse of `worker.py`: passed; syntax only.
- Local JS and nginx SHA256 values match `prepared.json` (captured 2026-11-10T15:41:32+08:00); this receipt reports native parser preparation passed and current services unchanged. The reviewer did not independently execute the remote preparation.
- Static inspection of the four files listed above: completed.

## Live QA status

Pending. This code review does not certify that the actual Penpot form's submit/fetch sequence, controlled input handling, nginx injection, successful save/reload/forget behavior, browser isolation, or runtime health have been observed on the deployed service. Those results must be recorded independently by the deploying agent. The supplied test fixture is a small synthetic DOM and cannot establish actual React or network integration.
