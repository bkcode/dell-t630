# Penpot browser login prefill review

Reviewed scope: VM250 configuration-only login prefill, based on the 2026-11-10 preflight and the implementation design supplied by the root agent. No remote access or secret reads were performed by this reviewer. Implementation was reviewed locally before execution. Live acceptance remains the root agent's responsibility; no live pass is implied by this report.

## Design assessment

No blocking design issue identified, provided the final implementation and verification satisfy the conditions below.

- Reuse the existing owner email/password. Read no worker or MCP identity, reset no account, change no application data or Git source, and build/pull no image.
- Keep the credential JSON on the guest only, with a root-protected parent directory and the frontend UID/GID1001 able to read only the mounted file. Never include its contents or digest in evidence, Git, logs, or command arguments.
- Replace the existing exact `/js/selfhost-login.json` location rather than defining a duplicate. Permit only LAN21/24, WG10.66.66/24, VM250 self19.50 and loopback; deny other peers. Trust X-Real-IP only from loopback, with recursive resolution disabled. Return JSON with Cache-Control no-store even on denied responses.
- Stop dell-penpot.service fully before changing locked files. Change only the private secret source, one frontend read-only nginx bind mount, corresponding expected-mount entries, and hashes of these public configuration files. Preserve all 11 service identities, images, resource limits, other mounts, logging and existing supervision checks.
- The existing fresh-target.py init explicitly forbids browser credentials and must remain unused; this task updates the active supervisor path only.

## Required acceptance evidence

1. Native nginx configuration test succeeds before the main service restarts.
2. Eleven services return healthy with original Git/source/image/resource/data contracts intact.
3. LAN request returns owner-matching JSON without exposing values in evidence, and Cache-Control contains no-store.
4. A request from an existing non-loopback Docker container remains403 with both forged X-Real-IP and X-Forwarded-For. CF19.5 remains outside the allowlist; do not claim a CF live negative test unless it was actually performed. A second negative request through the published host port is useful to check hairpin source-address handling without changing the allowlist.
5. Browser login inputs match the endpoint defaults using boolean comparison only, and an actual login succeeds without showing password values in screenshots or tool results.

## Source-address caveat

Published-port requests originating on VM250 itself may reach nginx with the Docker bridge gateway as peer, depending on Docker networking. Validate the observed peer before asserting self access works. Do not fix a403 by trusting the Docker bridge gateway: that would allow other containers to spoof X-Real-IP. LAN/WG success and Docker-source denial need independent evidence.

## Implementation review

No P1 or blocking issue found in the reviewed worker.py and selfhost-login.conf. Python AST parsing passed. This is approval of the bounded implementation design, not a statement that execution or browser acceptance has passed.

The code enforces three known public input digests before preparation and again before maintenance; YAML semantic comparisons limit compose changes to the secret file source and one read-only frontend mount. It derives the new deployment lock from the old lock, changing only the frontend credential mount source, adding the nginx mount, and updating hashes for those public configuration changes. It does not modify Git, pull/build images, invoke fresh initialization, reset credentials, or change data.

Preparation creates the private candidate/backup transaction and currently unbound public nginx file, then checks the existing frontend's native nginx parser with a temporary configuration. Application stops the managed service before replacing the three locked files, starts via the existing supervisor, waits for11healthy, repeats the supervisor contract check, checks an uncached200 with JSON equality entirely in guest memory, checks one Docker peer with both forged forwarding headers gets403, verifies the existing owner can log in, and checks the identity file remains byte-identical. Exceptions suppress command output and secret details.

The nginx policy uses an exact location, loopback-only real-IP trust, explicit LAN/WG/self/loopback allowlist, deny-all, read-only GET/HEAD serving, and no-store on all responses. The Docker bridge gateway is not trusted.

Two non-blocking robustness observations were sent to the root agent: explicitly gate the existing /etc/penpot directory's root ownership0700/no-symlink property before writing the new file, and wait for old-stack health after the asynchronous rollback restart if rollback is needed. The current exception path makes no false claim that rollback health has been confirmed. Preparation is deliberately one-shot; a preparation failure leaves protected artifacts to inspect rather than allowing blind rerun.

Reviewed public source digests (no credential contents or credential digests):


- infra/penpot/login-prefill/worker.py: 029f897e24d23cec84bda4f85888b4fdb6260a2871028742dd32c48fb866dac5
- infra/penpot/login-prefill/selfhost-login.conf: d88c86636b95a875cee5fd1f5f65df77de4f67be61b94effcdd04dea69510aef
